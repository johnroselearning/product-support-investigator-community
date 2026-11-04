import argparse
import json
from .store import TraceStore

def main():
    parser = argparse.ArgumentParser(description='Inspect sanitized application execution traces')
    parser.add_argument('--db')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    for name in ('inspect', 'export'):
        command = sub.add_parser(name)
        command.add_argument('trace_id')
        command.add_argument('--format', choices=['json'], default='json')
    args = parser.parse_args()
    store = TraceStore(args.db)
    try:
        if args.command == 'list':
            result = [{k: t[k] for k in ('trace_id', 'timestamp', 'skill_applied', 'final_status')} for t in store.list()]
        else:
            result = store.get(args.trace_id)
            if args.command == 'inspect':
                result['incomplete_phases'] = [p['phase_id'] for p in result['phases'] if p['status'] in ('not_run', 'failed')]
        print(json.dumps(result, indent=2))
    except KeyError:
        parser.exit(1, 'Trace not found\n')

if __name__ == '__main__':
    main()
