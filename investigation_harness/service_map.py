"""Trusted, bounded service catalog: investigative leads, never access grants."""
from copy import deepcopy

_FIELDS = {"service", "aliases", "routes", "components", "environments", "datasources", "telemetry_labels", "dependencies", "owners"}


class ServiceMap:
    def __init__(self, entries=()):
        entries = list(entries)
        if len(entries) > 100:
            raise ValueError("Service map exceeds bound")
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) - _FIELDS or not isinstance(entry.get("service"), str) or not entry["service"]:
                raise ValueError("Invalid service mapping")
            for key, value in entry.items():
                if key == "service":
                    valid = len(value) <= 128
                elif key == "telemetry_labels":
                    valid = isinstance(value, dict) and len(value) <= 20 and all(isinstance(k, str) and isinstance(v, str) and 0 < len(k) <= 128 and 0 < len(v) <= 128 for k, v in value.items())
                else:
                    valid = isinstance(value, list) and len(value) <= 20 and all(isinstance(v, str) and 0 < len(v) <= 128 for v in value)
                if not valid:
                    raise ValueError("Invalid service mapping field")
        self._entries = deepcopy(entries)

    def leads(self, service):
        if not service:
            return []
        matches = [e for e in self._entries if service in [e["service"], *e.get("aliases", []), *e.get("routes", []), *e.get("components", [])]]
        return deepcopy(matches[:10])
