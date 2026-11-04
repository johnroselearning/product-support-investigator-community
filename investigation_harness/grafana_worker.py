"""Private child process used to cancel the existing synchronous Grafana provider."""
import json
import sys

from providers.grafana import GrafanaProvider


def main():
    raw = sys.stdin.read(16385)
    if len(raw) > 16384:
        return 2
    print(json.dumps(GrafanaProvider().retrieve(json.loads(raw))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
