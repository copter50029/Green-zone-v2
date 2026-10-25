"""Exclude mapped structures/private land; this is not a cadastral decision."""
import json
import math

import numpy as np
from rasterio.features import is_valid_geom, rasterize
from rasterio.warp import transform_geom
from scipy.ndimage import binary_dilation


def exclude_context(mask, context, transform, crs, *, building_buffer_m=2):
    """Return mask and disjoint removal areas for buildings/residential/private.

    context: WGS84 GeoJSON polygons with properties.tags or tags_json.
    All mapped residential polygons are excluded, possibly including public
    vegetation inside them. Missing coverage/OSM tags are not proof of safety.
    """
    if not np.isfinite(building_buffer_m) or not 0 <= building_buffer_m <= 20:
        raise ValueError("building_buffer_m must be between 0 and 20 metres")
    groups = {key: [] for key in ('buildings', 'residential', 'private_access')}
    skipped = 0
    for feature in context.get('features', []):
        props = feature.get('properties') or {}
        tags = props.get('tags') or json.loads(props.get('tags_json') or '{}')
        keys = []
        if tags.get('building') not in (None, 'no', 'false', '0'):
            keys.append('buildings')
        if tags.get('landuse') == 'residential':
            keys.append('residential')
        if tags.get('access') in ('private', 'no', 'customers', 'permit'):
            keys.append('private_access')
        if not keys:
            continue
        geometry = feature.get('geometry') or {}
        if geometry.get('type') not in ('Polygon', 'MultiPolygon') or not is_valid_geom(geometry):
            skipped += 1
            continue
        projected = transform_geom('EPSG:4326', crs, geometry)
        for key in keys:
            groups[key].append(projected)
    result, areas = mask.copy(), {}
    pixel_m = transform.a
    for key, shapes in groups.items():
        burned = rasterize(shapes, out_shape=mask.shape, transform=transform, fill=0, default_value=1, dtype='uint8').astype(bool) if shapes else np.zeros(mask.shape, dtype=bool)
        if key == 'buildings' and burned.any() and building_buffer_m:
            radius = math.ceil(building_buffer_m / pixel_m)
            yy, xx = np.ogrid[-radius:radius+1, -radius:radius+1]
            burned = binary_dilation(burned, structure=(xx*xx + yy*yy) * pixel_m**2 <= building_buffer_m**2)
        areas[key] = int(((result == 1) & burned).sum()) * pixel_m**2
        result[burned & (result != 255)] = 0
    coverage = context.get('source', {}).get('coverage_geometry')
    outside = None
    if coverage:
        inside = rasterize([transform_geom('EPSG:4326', crs, coverage)], out_shape=mask.shape, transform=transform, fill=0, default_value=1, dtype='uint8')
        outside = int(((mask != 255) & (inside == 0)).sum()) * pixel_m**2
    return result, {'removed_candidate_m2': areas, 'skipped_non_polygon_or_invalid': skipped,
                    'valid_area_outside_context_coverage_m2': outside,
                    'attribution': context.get('source', {}),
                    'scope': 'outside_mapped_buildings_residential_and_private_areas_not_verified_public_land'}
