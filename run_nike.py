"""Run Nike functions on a manageable raster; grid.py remains independent."""
import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import ColorInterp

from greensight import detect_green, make_heatmap, prepare_park_review


def run_analysis(tif_path, out_dir, *, scene_id, red_band, nir_band,
                 registry_path=None, exclude_path=None, imagery_date=None):
    """Write candidate/heatmap GeoTIFFs, summary and pending park-review GeoJSON.

    This small example accepts up to 25 million pixels. For larger scenes,
    classify in windows, merge all cores, then run patch filtering/heatmap once.
    A tile result has clipped patch boundaries and is not a whole-scene result.
    """
    destination = Path(out_dir)
    if destination.exists():
        raise FileExistsError("Choose a new output directory; existing results are preserved")
    with rasterio.open(tif_path) as src:
        if src.width * src.height > 25_000_000:
            raise ValueError("Example budget: 25 million pixels. Use a tile/crop or windowed scene workflow")
        if src.crs is None or not src.crs.is_projected or not np.isclose(src.crs.linear_units_factor[1], 1):
            raise ValueError("Expected a projected raster in metres")
        if src.transform.b or src.transform.d or src.transform.a <= 0 or src.transform.e >= 0 or not np.isclose(src.res[0], src.res[1]):
            raise ValueError("Expected a north-up raster with square pixels")
        exclusion = None
        if exclude_path:
            with rasterio.open(exclude_path) as extra:
                if extra.crs != src.crs or extra.transform != src.transform or extra.shape != src.shape or extra.count != 1:
                    raise ValueError("Exclusion must be one band on the exact source grid/CRS")
                exclusion = (extra.read(1) != 0) & (extra.read_masks(1) != 0)
        mask = detect_green(src.read(), red_band=red_band, nir_band=nir_band,
                            nodata=src.nodata, valid_mask=(src.read_masks() != 0).all(axis=0),
                            exclude_mask=exclusion)
        result = make_heatmap(mask, pixel_m=src.res[0], min_area_m2=300, radius_m=50)
        registry = {"type": "FeatureCollection", "features": []}
        if registry_path:
            registry = json.loads(Path(registry_path).read_text(encoding="utf-8-sig"))
        tasks = prepare_park_review(registry, result["mask"], src.transform, src.crs,
                                    scene_id=scene_id, imagery_date=imagery_date)
        profile = src.profile.copy()
        profile.update(dtype="uint8", count=1, nodata=255, compress="deflate")
        destination.mkdir(parents=True)
        with rasterio.open(destination / "candidate-mask.tif", "w", **profile) as output:
            output.write(result["mask"], 1)
        profile.update(count=4, nodata=None)
        with rasterio.open(destination / "heatmap.tif", "w", **profile) as output:
            output.write(np.moveaxis(result["rgba"], -1, 0))
            output.colorinterp = (ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.alpha)
        summary = {
            "scene_id": scene_id, "input_file": Path(tif_path).name,
            "status": "experimental_raw_band_ratio_unvalidated",
            "red_band_assumption": red_band, "nir_band_assumption": nir_band,
            "exclusion_supplied": exclusion is not None,
            "pixel_m": src.res[0], "minimum_patch_m2": 300,
            "halo_radius_m": 50, "stats": result["stats"],
            "review_tasks": len(tasks["features"]), "verified_parks": 0,
            "limitations": ["Tile-edge patches are clipped; merge scene cores before final filtering.",
                            "Band identities/calibration and roof rejection are not established.",
                            "Registry points/nearby vegetation do not prove public access."],
        }
    for filename, value in (("park-review.geojson", tasks), ("summary.json", summary)):
        (destination / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tif_path")
    parser.add_argument("out_dir")
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--red-band", required=True, type=int)
    parser.add_argument("--nir-band", required=True, type=int)
    parser.add_argument("--registry", default="data/parks15.geojson")
    parser.add_argument("--exclude")
    parser.add_argument("--imagery-date")
    args = parser.parse_args()
    print(json.dumps(run_analysis(args.tif_path, args.out_dir, scene_id=args.scene_id,
                                 red_band=args.red_band, nir_band=args.nir_band,
                                 registry_path=args.registry, exclude_path=args.exclude,
                                 imagery_date=args.imagery_date), indent=2))
