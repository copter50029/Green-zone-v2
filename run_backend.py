"""One command for detection, heatmaps, registry lookup and consistency audits."""
import argparse
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from greensight.audit import audit_scene
from greensight.scene import read_json, write_json
from run_nike import run_all
from verify_parks import verify_parks

ROOT = Path(__file__).resolve().parent


def prepare_config(config_path, *, project_root=ROOT):
    """Resolve input paths against project_root; check before processing."""
    root = Path(project_root).resolve()
    path = Path(config_path)
    config = deepcopy(read_json(path if path.is_absolute() else root / path))
    scenes = config.get('scenes', [])
    ids = [scene['id'] for scene in scenes]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('Configure at least one scene with unique IDs')
    for scene in scenes:
        name = scene['id']
        if not isinstance(name, str) or not name or any(c in name for c in '/\\:') or name in ('.', '..'):
            raise ValueError('Scene IDs must be simple folder names')
        if not scene.get('context'):
            raise ValueError('Each scene needs a context file for the full audit')
    inputs = [(config, 'registry')]
    inputs += [(config, key) for key in ('policy_exclusions', 'pending_areas') if config.get(key)]
    inputs += [(scene, key) for scene in scenes for key in ('path', 'context')]
    for owner, key in inputs:
        path = Path(owner[key])
        path = (path if path.is_absolute() else root / path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f'Missing {key}: {path}')
        owner[key] = str(path)
    return config


def run_backend(config_path='data/scenes.json', out_dir=None, *, district='don-mueang', project_root=ROOT):
    """Run all automatic stages; human reviews remain pending.

    Relative paths use project_root, never the shell working directory.
    Existing results are preserved; failed runs keep status and partial evidence.
    """
    config = prepare_config(config_path, project_root=project_root)
    output = Path(out_dir) if out_dir else Path('Output/runs') / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    if not output.is_absolute():
        output = Path(project_root) / output
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    stage = 'configuration'
    write_json(output / 'status.json', {'status': 'running', 'stage': stage})
    try:
        config_file = output / 'config.json'
        write_json(config_file, config)
        stage = 'analysis'
        write_json(output / 'status.json', {'status': 'running', 'stage': stage})
        print('[1/3] Detecting green areas and making heatmaps', flush=True)
        scenes = run_all(config_file, output / 'analysis')
        stage = 'park_lookup'
        write_json(output / 'status.json', {'status': 'running', 'stage': stage})
        print('[2/3] Finding registered parks in valid image pixels', flush=True)
        parks = verify_parks(config_file, output / 'parks', district=district)
        stage = 'audit'
        write_json(output / 'status.json', {'status': 'running', 'stage': stage})
        print('[3/3] Auditing every source window and retained patch (may take time)', flush=True)
        audits = []
        for scene in config['scenes']:
            print('Auditing ' + scene['id'], flush=True)
            audits.append(audit_scene(
                output / 'analysis' / scene['id'], scene['path'],
                context_path=scene['context'], policy_path=config.get('policy_exclusions'),
                pending_path=config.get('pending_areas'),
            ))
        result = {'status': 'complete', 'output': str(output), 'scenes': scenes,
                  'park_lookup': parks, 'audits': audits,
                  'public_park_verification': 'needs_human_review'}
        write_json(output / 'summary.json', result)
        write_json(output / 'status.json', {'status': 'complete', 'stage': 'complete'})
        print('Complete: ' + str(output), flush=True)
        return result
    except Exception as error:
        write_json(output / 'status.json', {'status': 'failed', 'stage': stage,
                                         'error': str(error), 'error_type': type(error).__name__})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='data/scenes.json')
    parser.add_argument('--output', help='New output folder; defaults to a unique timestamp')
    parser.add_argument('--all-districts', action='store_true')
    args = parser.parse_args()
    run_backend(args.config, args.output, district=None if args.all_districts else 'don-mueang')


if __name__ == '__main__':
    main()
