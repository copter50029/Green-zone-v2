"""Look up Don Mueang park references in each configured image, without UI."""
import argparse
from pathlib import Path
from greensight.park_lookup import find_parks_in_image
from greensight.scene import read_json,write_json


def verify_parks(config_path='data/scenes.json', out_dir='Output/park-lookup', *, district='don-mueang'):
    output=Path(out_dir)
    if output.exists():raise FileExistsError('Choose a new output folder')
    config=read_json(config_path);output.mkdir(parents=True)
    results=[]
    for scene in config['scenes']:
        result=find_parks_in_image(scene['path'],config['registry'],district=district)
        write_json(output/(scene['id']+'-parks.geojson'),result)
        results.append({'scene_id':scene['id'],'registry_points_in_valid_image':len(result['features']),
                        'verified_parks':0,'district_filter':district,'status':result['status']})
    write_json(output/'summary.json',results)
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='data/scenes.json')
    parser.add_argument('--output',default='Output/park-lookup')
    parser.add_argument('--all-districts',action='store_true')
    args=parser.parse_args()
    for row in verify_parks(args.config,args.output,district=None if args.all_districts else 'don-mueang'):
        print(row['scene_id'],row['registry_points_in_valid_image'],row['status'])
