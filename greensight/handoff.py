"""Small frontend handoff: projected PNG overlays + explicit GeoJSON/JSON."""
from pathlib import Path
import shutil
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import array_bounds, from_bounds
from rasterio.warp import reproject, transform_bounds
from .scene import read_json, write_json, digest


def export_frontend(run_dir, out_dir, *, max_size=1200):
    """Export finished scene results without rerunning detection or altering inputs.

    PNGs are warped to EPSG:3857 for web map image overlays. Bounds use
    [west,south,east,north] degrees; measurements remain native-grid values.
    """
    if type(max_size) is not int or not 16 <= max_size <= 4096:
        raise ValueError('max_size must be an integer from 16 to 4096')
    source, output = Path(run_dir), Path(out_dir)
    if output.exists():
        raise FileExistsError('Choose a new frontend export directory')
    summaries = read_json(source/'summary-all.json')
    records = []
    # Validate source artifacts before creating the export.
    for s in summaries:
        scene = s['scene_id']
        if Path(scene).name != scene or scene in ('.','..') or '/' in scene or '\\' in scene:
            raise ValueError('Invalid scene ID')
        folder = source/scene
        if read_json(folder/'status.json').get('status') != 'complete':
            raise ValueError('Only completed scenes can be exported')
        names=['heatmap.tif','candidate-mask.tif','source.png','park-review.geojson']
        if s.get('pending_review') is not None:names.extend(['pending.tif','pending-mask.tif'])
        for name in names:
            if digest(folder/name) != s['artifact_sha256'][name]:
                raise ValueError('Source artifact hash mismatch: '+name)
    output.mkdir(parents=True)
    for s in summaries:
        scene = s['scene_id']; folder = source/scene; target = output/scene
        target.mkdir()
        with rasterio.open(folder/'heatmap.tif') as src:
            projected = transform_bounds(src.crs,'EPSG:3857',*src.bounds)
            span_x, span_y = projected[2]-projected[0], projected[3]-projected[1]
            width = max(1,round(max_size*span_x/max(span_x,span_y)))
            height = max(1,round(max_size*span_y/max(span_x,span_y)))
            grid = from_bounds(*projected,width,height)
            layers=['source','heatmap']+(['pending'] if s.get('pending_review') is not None else [])
            for name in layers:
                if name == 'source':
                    with rasterio.open(folder/'source.png') as preview:
                        data = preview.read()
                    data = np.concatenate((data,np.full((1,*data.shape[1:]),255,dtype='uint8')))
                    # Source validity comes from the mask, not heatmap proximity alpha.
                    with rasterio.open(folder/'candidate-mask.tif') as mask:
                        data[3] = (mask.read(1,out_shape=data.shape[1:]) != 255)*255
                    native_grid = src.transform * rasterio.Affine.scale(src.width/data.shape[2],src.height/data.shape[1])
                else:
                    with rasterio.open(folder/f'{name}.tif') as layer:
                        if layer.crs!=src.crs or layer.transform!=src.transform or layer.shape!=src.shape:
                            raise ValueError('Overlay grids must match')
                        data = layer.read(out_shape=(4,min(max_size,src.height),min(max_size,src.width)))
                    native_grid = src.transform * rasterio.Affine.scale(src.width/data.shape[2],src.height/data.shape[1])
                warped = np.zeros((4,height,width),dtype='uint8')
                reproject(data,warped,src_transform=native_grid,src_crs=src.crs,dst_transform=grid,dst_crs='EPSG:3857',resampling=Resampling.nearest)
                with rasterio.open(target/f'{name}.png','w',driver='PNG',width=width,height=height,count=4,dtype='uint8') as dst:
                    dst.write(warped)
            bounds = transform_bounds('EPSG:3857','EPSG:4326',*array_bounds(height,width,grid))
        shutil.copyfile(folder/'park-review.geojson',target/'parks.geojson')
        records.append({'id':scene,'bounds_wgs84':list(bounds),'image_crs':'EPSG:3857',
                        'source':f'{scene}/source.png','heatmap':f'{scene}/heatmap.png','parks':f'{scene}/parks.geojson',
                        'candidate_area_m2':s['stats']['retainedCandidateAreaM2'], 'valid_area_m2':s['valid_area_m2'],
                        'park_points':s['review_tasks'],'verified_parks':s['verified_parks'],
                        'status':s['status'],'real_accuracy':s['real_accuracy'],'limitations':s['limitations'],
                        'source_sha256':s['provenance']['source_sha256']})
        if s.get('pending_review') is not None:
            records[-1].update(pending=f'{scene}/pending.png',pending_area_m2=s['pending_review']['pending_candidate_area_m2'],pending_in_main_total=False)
    manifest={'schema_version':1,'scenes':records,'legend':{'green':'candidate vegetation','halo':'straight-line proximity, not temperature or walking distance','park':'registry point awaiting evidence review'},
              'files_sha256':{p.relative_to(output).as_posix():digest(p) for p in sorted(output.rglob('*')) if p.is_file()}}
    write_json(output/'manifest.json',manifest)
    return manifest
