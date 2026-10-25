"""Full-scene windowed detection, followed by global filtering on valid bounds."""
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import ColorInterp
from rasterio.windows import Window

from .detect import detect_green
from .heatmap import make_heatmap
from .park_verify import prepare_park_review
from .exclusions import exclude_context


def windows(width, height, size=512):
    """Cover every source pixel exactly once, including partial edge windows."""
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise ValueError('Window size must be a positive integer')
    for row in range(0, height, size):
        for col in range(0, width, size):
            yield Window(col, row, min(size, width-col), min(size, height-row))


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def analyse_scene(tif_path, out_dir, *, scene_id, red_band, nir_band,
                  registry_path=None, context_path=None, exclude_path=None,
                  imagery_date=None, window_size=512, min_area_m2=300,
                  radius_m=50, clean_radius_m=0, progress=None):
    """Process a TIFF once in windows; merge before patch filtering/heatmap.

    Outputs preserve the source CRS and native pixel grid, cropped only to
    exact valid-pixel bounds. Cropping never discards a valid image pixel.
    Global filters use RAM on the cropped mask (maximum 80 million cells).
    Does not manufacture model accuracy, ownership or public-access evidence.
    """
    destination, tif_path = Path(out_dir), Path(tif_path)
    if destination.exists():
        raise FileExistsError('Choose a new output directory; existing results are preserved')
    registry = read_json(registry_path) if registry_path else {'type': 'FeatureCollection', 'features': []}
    context = read_json(context_path) if context_path else None
    # Validate user options before reading a large input or creating output.
    detect_green(np.ones((4, 1, 1)), red_band=red_band, nir_band=nir_band)
    make_heatmap(np.zeros((1, 1), dtype='uint8'), 1, min_area_m2, radius_m, clean_radius_m=clean_radius_m)
    list(windows(1, 1, window_size))
    stamp = (tif_path.stat().st_size, tif_path.stat().st_mtime_ns)
    if progress:
        progress(f'{scene_id}: hashing source')
    source_hash = digest(tif_path)
    exclusion = None
    with rasterio.open(tif_path) as src:
        if src.crs is None or not src.crs.is_projected or not np.isclose(src.crs.linear_units_factor[1], 1):
            raise ValueError('Expected a projected raster in metres')
        if not all(np.isfinite(tuple(src.transform)[:6])) or src.transform.b or src.transform.d or src.transform.a <= 0 or src.transform.e >= 0 or not np.isclose(src.res[0], src.res[1]):
            raise ValueError('Expected north-up square pixels')
        detect_green(np.ones((src.count, 1, 1)), red_band=red_band, nir_band=nir_band)
        if exclude_path:
            exclusion = rasterio.open(exclude_path)
            if exclusion.crs != src.crs or exclusion.transform != src.transform or exclusion.shape != src.shape or exclusion.count != 1:
                exclusion.close()
                raise ValueError('Exclusion must be one band on the exact source grid/CRS')
        destination.mkdir(parents=True)
        write_json(destination / 'status.json', {'status': 'processing', 'scene_id': scene_id})
        profile = dict(driver='GTiff', count=1, width=src.width, height=src.height,
                       crs=src.crs, transform=src.transform, dtype='uint8', nodata=255,
                       tiled=True, blockxsize=256, blockysize=256, compress='deflate', BIGTIFF='IF_SAFER')
        top, left, bottom, right = src.height, src.width, 0, 0
        total = seen = nonempty = 0
        raw = destination / 'raw-mask.tif'
        try:
            with rasterio.open(raw, 'w', SPARSE_OK=True, **profile) as dst:
                for win in windows(src.width, src.height, window_size):
                    total += 1
                    # A missing first band cannot be valid across all bands.
                    if not src.read_masks(1, window=win).any():
                        continue
                    bands = src.read(window=win)
                    extra = None if exclusion is None else (exclusion.read(1, window=win) != 0) & (exclusion.read_masks(1, window=win) != 0)
                    mask = detect_green(bands, red_band=red_band, nir_band=nir_band,
                                        nodata=src.nodata, valid_mask=(src.read_masks(window=win) != 0).all(axis=0), exclude_mask=extra)
                    valid = mask != 255
                    if not valid.any():
                        continue
                    dst.write(mask, 1, window=win)
                    rr, cc = np.where(valid)
                    top, left = min(top, int(win.row_off)+int(rr.min())), min(left, int(win.col_off)+int(cc.min()))
                    bottom, right = max(bottom, int(win.row_off)+int(rr.max())+1), max(right, int(win.col_off)+int(cc.max())+1)
                    seen += int(valid.sum())
                    nonempty += 1
                    if progress and nonempty % 20 == 0:
                        progress(f'{scene_id}: {nonempty} data windows / {seen:,} valid pixels')
        finally:
            if exclusion is not None:
                exclusion.close()
        crop = Window(left, top, right-left, bottom-top) if seen else Window(0, 0, 1, 1)
        if crop.width * crop.height > 80_000_000:
            raise ValueError('Valid extent exceeds 80M-cell global-filter budget; raw-mask.tif is retained')
        transform = src.window_transform(crop)
        with rasterio.open(raw) as source:
            mask = source.read(1, window=crop)
        if int((mask != 255).sum()) != seen:
            raise RuntimeError('Window merging lost or invented valid pixels')
        exclusion_report = None
        if context:
            mask, exclusion_report = exclude_context(mask, context, transform, src.crs)
        if progress:
            progress(f'{scene_id}: global patch filter and distance over {mask.shape}')
        result = make_heatmap(mask, src.res[0], min_area_m2, radius_m, clean_radius_m=clean_radius_m)
        tasks = prepare_park_review(registry, result['mask'], transform, src.crs,
                                    scene_id=scene_id, imagery_date=imagery_date)
        profile.update(width=int(crop.width), height=int(crop.height), transform=transform)
        with rasterio.open(destination / 'candidate-mask.tif', 'w', **profile) as dst:
            dst.write(result['mask'], 1)
        profile.update(count=4, nodata=None)
        with rasterio.open(destination / 'heatmap.tif', 'w', **profile) as dst:
            dst.write(np.moveaxis(result['rgba'], -1, 0))
            dst.colorinterp = (ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.alpha)
        # Compact display artifact; raw radiometry is not modified.
        height = max(1, round(1000 * crop.height / max(crop.width, crop.height)))
        width = max(1, round(1000 * crop.width / max(crop.width, crop.height)))
        rgb = src.read([red_band, 2 if src.count >= 2 else red_band, 1], window=crop, out_shape=(3,height,width)).astype('float32')
        valid_preview = src.read_masks(1, window=crop, out_shape=(height,width)) != 0
        for band in rgb:
            limits = np.percentile(band[valid_preview], [2,98]) if valid_preview.any() else [0,1]
            band[:] = np.clip((band-limits[0])/max(limits[1]-limits[0],1), 0, 1)*255
        rgb = np.moveaxis(rgb.astype('uint8'), 0, -1)
        rgb[~valid_preview] = [236,234,230]
        for name in ('source', 'heatmap'):
            image = rgb
            if name == 'heatmap':
                with rasterio.open(destination / 'heatmap.tif') as layer:
                    rgba = np.moveaxis(layer.read(out_shape=(4,height,width)),0,-1)
                alpha = rgba[:,:,3:4].astype('float32')/255
                image = np.round(rgb*(1-alpha)+rgba[:,:,:3]*alpha).astype('uint8')
            with rasterio.open(destination / f'{name}.png', 'w', driver='PNG', width=width,height=height,count=3,dtype='uint8') as dst:
                dst.write(np.moveaxis(image,-1,0))
        summary = {
            'scene_id':scene_id, 'input_file':tif_path.name,
            'status':'experimental_raw_band_ratio_unvalidated',
            'red_band_assumption':red_band,'nir_band_assumption':nir_band,
            'band_mapping_status':'standard_order_supported_file_identity_unconfirmed',
            'calibration_verified':False, 'real_accuracy':None,
            'imagery_date':imagery_date,'imagery_date_basis':'source filename; product metadata not verified',
            'pixel_m':src.res[0], 'valid_area_m2':seen*src.res[0]**2,
            'source_shape':[src.height,src.width], 'crop_window':[int(crop.col_off),int(crop.row_off),int(crop.width),int(crop.height)],
            'transform':list(transform)[:6], 'crs':src.crs.to_string(),
            'window_size':window_size,'windows_scanned':total,'data_windows':nonempty,
            'clean_radius_m':clean_radius_m, 'minimum_patch_m2':min_area_m2,'halo_radius_m':radius_m,
            'exclusion_supplied':bool(context_path or exclude_path), 'context_exclusions':exclusion_report,
            'stats':result['stats'], 'review_tasks':len(tasks['features']), 'verified_parks':0,
            'provenance':{'source_sha256':source_hash,
                          'registry_sha256':digest(registry_path) if registry_path else None,
                          'context_sha256':digest(context_path) if context_path else None,
                          'exclusion_sha256':digest(exclude_path) if exclude_path else None,
                          'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}},
            'limitations':['No independent reviewed labels; no real accuracy.',
                           'OSM exclusions are incomplete and are not ownership or public-access verification.',
                           'Residential exclusion can remove public vegetation inside broad residential polygons.',
                           'RGB preview band identities and image dates are not file-level verified.'],
        }
    if (tif_path.stat().st_size,tif_path.stat().st_mtime_ns) != stamp:
        raise RuntimeError('Source changed during analysis; output is not publishable')
    write_json(destination / 'park-review.geojson',tasks)
    summary['artifact_sha256'] = {name:digest(destination/name) for name in ('raw-mask.tif','candidate-mask.tif','heatmap.tif','park-review.geojson','source.png','heatmap.png')}
    write_json(destination / 'summary.json',summary)
    write_json(destination / 'status.json',{'status':'complete','scene_id':scene_id})
    return summary
