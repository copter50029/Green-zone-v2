"""Run Nike's full-scene analysis without changing the team's grid.py."""
import argparse
import json
from pathlib import Path

from greensight.scene import analyse_scene, read_json
from greensight.report import write_report

# Keep the previous import usable by teammates.
run_analysis = analyse_scene


def run_all(config_path='data/scenes.json', out_dir='Output/nike-scenes'):
    """Analyse all configured images; refuse existing output to preserve runs."""
    output = Path(out_dir)
    if output.exists():
        raise FileExistsError('Choose a new output root')
    settings = read_json(config_path)
    results = []
    for scene in settings['scenes']:
        results.append(analyse_scene(
            scene['path'], output/scene['id'], scene_id=scene['id'],
            red_band=scene['red_band'], nir_band=scene['nir_band'],
            context_path=scene.get('context'), imagery_date=scene.get('imagery_date'),
            registry_path=settings.get('registry'),
            clean_radius_m=scene.get('clean_radius_m',settings.get('clean_radius_m',0)),
            building_buffer_m=settings.get('building_buffer_m',2),house_buffer_m=settings.get('house_buffer_m',0),
            residential_buffer_m=settings.get('residential_buffer_m',0), policy_exclusions=settings.get('policy_exclusions'), progress=lambda message: print(message,flush=True)))
    write_report(output, results)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tif_path', nargs='?')
    parser.add_argument('out_dir', nargs='?')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--output', default='Output/nike-scenes')
    parser.add_argument('--config', default='data/scenes.json')
    parser.add_argument('--scene-id')
    parser.add_argument('--red-band', type=int)
    parser.add_argument('--nir-band', type=int)
    parser.add_argument('--registry', default='data/parks15.geojson')
    parser.add_argument('--policy-exclusions', default='data/labels/area-exclusions.geojson')
    parser.add_argument('--exclude')
    parser.add_argument('--context')
    parser.add_argument('--imagery-date')
    parser.add_argument('--clean-radius-m',type=float,default=3)
    parser.add_argument('--building-buffer-m',type=float,default=8)
    parser.add_argument('--house-buffer-m',type=float,default=20)
    parser.add_argument('--residential-buffer-m',type=float,default=10)
    args = parser.parse_args()
    if args.all:
        results = run_all(args.config,args.output)
        print(json.dumps([{'scene':r['scene_id'],'area_m2':r['stats']['retainedCandidateAreaM2']} for r in results],indent=2))
    else:
        if not all((args.tif_path,args.out_dir,args.scene_id,args.red_band,args.nir_band)):
            parser.error('Supply TIFF/output, --scene-id, --red-band and --nir-band; or use --all')
        result = analyse_scene(args.tif_path,args.out_dir,scene_id=args.scene_id,
                               red_band=args.red_band,nir_band=args.nir_band,
                               registry_path=args.registry,exclude_path=args.exclude,
                               context_path=args.context,imagery_date=args.imagery_date,clean_radius_m=args.clean_radius_m,
                               building_buffer_m=args.building_buffer_m,house_buffer_m=args.house_buffer_m,residential_buffer_m=args.residential_buffer_m,policy_exclusions=args.policy_exclusions,
                               progress=lambda message: print(message,flush=True))
        print(json.dumps(result,indent=2))
