"""Run a local simulated demonstration without credentials or network access."""
import argparse
import asyncio
import json

from .engine import Harness
from .fixtures import fixture_registry, policy, scenario


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="jira")
    parser.add_argument("--events", action="store_true", help="Include safe structured events")
    parser.add_argument("--all", action="store_true", help="Run representative demonstrations")
    args = parser.parse_args()
    names = ("explain", "stack", "jira", "environment", "injection", "conflict") if args.all else (args.scenario,)
    for name in names:
        request, model = scenario(name)
        result = await Harness(model, fixture_registry(name), policy()).run(request)
        output = {"mode": "SIMULATED: scripted decisions and synthetic tools; no real-model quality measured",
                  "scenario": name, "run_id": result.run_id, "route": result.understanding.get("route"),
                  "skill": result.selected_skill, "termination": result.termination,
                  "calls": result.calls, "report": result.report}
        if args.events:
            output["events"] = result.events
        from .state import safe
        print(json.dumps(safe(output), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
