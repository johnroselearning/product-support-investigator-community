#!/usr/bin/env python3
"""Read a bounded JSON request on stdin; emit normalized evidence on stdout."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers.grafana import GrafanaProvider


def main():
    raw = sys.stdin.read(16_385)
    try:
        request = json.loads(raw) if len(raw) <= 16_384 else {}
    except ValueError:
        request = {}
    print(json.dumps(GrafanaProvider().retrieve(request), ensure_ascii=True))


if __name__ == '__main__':
    main()
