import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StepResult:
    command: str
    params: dict[str, Any]
    expected_events: list[str]
    expected_state: str
    expected_error: str
    actual_events: list[str]
    actual_state: str
    actual_error: str
    passed: bool
    raw_result: Any = field(default=None, repr=False)


class TwinRunner:
    def __init__(self, twin_module_path: Path):
        self.twin_module_path = twin_module_path
        self._twin_instance: Any = None

    def load(self) -> Any:
        if not self.twin_module_path.exists():
            raise FileNotFoundError(f"Twin module not found: {self.twin_module_path}")

        spec = importlib.util.spec_from_file_location("twin", self.twin_module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load module from {self.twin_module_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules["twin"] = module
        spec.loader.exec_module(module)

        twin_attrs = ("TwinEngine", "DigitalTwin", "Twin", "CommandHandler")
        twin_cls = None
        for attr in twin_attrs:
            if hasattr(module, attr):
                twin_cls = getattr(module, attr)
                break

        if twin_cls is None:
            found = [a for a in dir(module) if not a.startswith("_") and isinstance(getattr(module, a), type)]
            raise RuntimeError(
                f"No twin class found. Found classes: {found}. "
                f"Expected one of: {twin_attrs}"
            )

        try:
            self._twin_instance = twin_cls()
        except TypeError:
            try:
                from types import SimpleNamespace
                self._twin_instance = twin_cls(SimpleNamespace(**{}), SimpleNamespace(**{}))
            except Exception:
                raise RuntimeError(
                    f"Could not instantiate {twin_cls.__name__}. "
                    "Make sure TwinEngine has a no-arg __init__ or handle constructor args."
                )

        print(f"[runner] Loaded twin: {twin_cls.__name__}")
        return self._twin_instance

    def dispatch(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._twin_instance is None:
            self.load()

        params = params or {}

        method_name = "dispatch"
        if hasattr(self._twin_instance, "dispatch"):
            method_name = "dispatch"
        elif hasattr(self._twin_instance, "handle"):
            method_name = "handle"
        else:
            raise RuntimeError(
                f"Twin instance has no 'dispatch' or 'handle' method. "
                f"Available methods: {[m for m in dir(self._twin_instance) if not m.startswith('_')]}"
            )

        method = getattr(self._twin_instance, method_name)
        result = method(command, params)

        return self._normalize_result(result)

    def _normalize_result(self, result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return {
                "events": result.get("events", []),
                "state": result.get("state", ""),
                "error": result.get("error", ""),
            }

        if hasattr(result, "event_type"):
            return {
                "events": [{"type": result.event_type, **(result.payload if hasattr(result, "payload") else {})}],
                "state": "",
                "error": "",
            }

        if hasattr(result, "event") and hasattr(result, "error_code"):
            if hasattr(result, "event"):
                ev = result.event
                return {
                    "events": [{"type": ev.event_type, **(ev.payload if hasattr(ev, "payload") else {})}],
                    "state": result.task_after.status if hasattr(result, "task_after") and result.task_after else "",
                    "error": "",
                }
            else:
                return {"events": [], "state": "", "error": result.error_code}

        if hasattr(result, "error_code"):
            return {"events": [], "state": "", "error": result.error_code}

        if hasattr(result, "event"):
            ev = result.event
            return {
                "events": [{"type": ev.event_type, **(ev.payload if hasattr(ev, "payload") else {})}],
                "state": result.task_after.status if hasattr(result, "task_after") and result.task_after else "",
                "error": "",
            }

        return {"events": [], "state": str(result), "error": ""}

    def run_scenario_steps(self, steps: list[dict[str, Any]]) -> list[StepResult]:
        if self._twin_instance is None:
            self.load()

        results: list[StepResult] = []
        for step in steps:
            cmd = step.get("command", "")
            params = step.get("params", {})
            expected_events = step.get("expected_events", [])
            expected_state = step.get("expected_state", "")
            expected_error = step.get("expected_error", "")

            normalized = self.dispatch(cmd, params)

            actual_events = []
            if normalized["events"]:
                actual_events = [e.get("type", "") for e in normalized["events"]]
            actual_state = normalized.get("state", "")
            actual_error = normalized.get("error", "")

            if expected_error:
                passed = actual_error == expected_error
            else:
                events_match = (
                    not expected_events
                    or set(actual_events) == set(expected_events)
                )
                state_match = (
                    not expected_state
                    or actual_state == expected_state
                )
                passed = events_match and state_match

            results.append(StepResult(
                command=cmd,
                params=params,
                expected_events=expected_events if isinstance(expected_events, list) else [expected_events],
                expected_state=expected_state,
                expected_error=expected_error,
                actual_events=actual_events,
                actual_state=actual_state,
                actual_error=actual_error,
                passed=passed,
                raw_result=normalized,
            ))

        return results

    def run_all_scenarios(self, scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
        all_results: list[dict[str, Any]] = []
        for scenario in scenarios:
            name = scenario.get("name", scenario.get("description", "unnamed"))
            steps = scenario.get("steps", [])
            step_results = self.run_scenario_steps(steps)
            scenario_passed = all(sr.passed for sr in step_results)
            all_results.append({
                "scenario": name,
                "passed": scenario_passed,
                "steps": [
                    {
                        "command": sr.command,
                        "params": sr.params,
                        "expected_events": sr.expected_events,
                        "expected_state": sr.expected_state,
                        "expected_error": sr.expected_error,
                        "actual_events": sr.actual_events,
                        "actual_state": sr.actual_state,
                        "actual_error": sr.actual_error,
                        "passed": sr.passed,
                    }
                    for sr in step_results
                ],
            })
        return all_results

    def print_report(self, results: list[dict[str, Any]]) -> None:
        total = len(results)
        passed = sum(1 for r in results if r["passed"])
        print(f"\n{'='*50}")
        print(f"  Twin Execution Report: {passed}/{total} scenarios passed")
        print(f"{'='*50}")
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"\n  Scenario: {r['scenario']} [{status}]")
            for step in r["steps"]:
                s = "PASS" if step["passed"] else "FAIL"
                print(f"    [{s}] {step['command']}({json.dumps(step['params'])})")
                if step["expected_events"]:
                    print(f"         expected events: {step['expected_events']}")
                    print(f"         actual events:   {step['actual_events']}")
                if step["expected_state"]:
                    print(f"         expected state:  {step['expected_state']}")
                    print(f"         actual state:    {step['actual_state']}")
                if step["expected_error"]:
                    print(f"         expected error:  {step['expected_error']}")
                    print(f"         actual error:    {step['actual_error']}")
        print(f"\n{'='*50}")
        print(f"  Total: {passed}/{total} passed.")
        print(f"{'='*50}")
