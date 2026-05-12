import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _normalize_scenarios(scenarios: Any) -> list[dict[str, Any]]:
    if isinstance(scenarios, dict):
        result: list[dict[str, Any]] = []
        for name, steps in scenarios.items():
            result.append({"name": name, "steps": _normalize_steps(steps)})
        return result
    if isinstance(scenarios, list):
        result = []
        for item in scenarios:
            if isinstance(item, dict):
                name = item.get("name", item.get("description", "unnamed"))
                steps = item.get("steps", item) if "steps" in item else [item]
                result.append({"name": name, "steps": _normalize_steps(steps)})
            else:
                result.append({"name": str(item), "steps": []})
        return result
    return []


def _normalize_steps(steps: Any) -> list[dict[str, Any]]:
    if not isinstance(steps, list):
        steps = [steps]

    normalized: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue

        if "command" in step:
            step["expected_state"] = _yaml_str(step.get("expected_state", ""))
            normalized.append(step)
            continue

        if "when" in step:
            when = step["when"]
            command = when.get("command", "")
            if "(" in command:
                command, _ = command.split("(", 1)

            params_str = ""
            if "(" in when.get("command", ""):
                _, params_str = when["command"].split("(", 1)
                params_str = params_str.rstrip(")")

            params = {}
            if params_str:
                params_str = params_str.strip().strip('"').strip("'")
                if params_str:
                    params["light_id"] = params_str

            then = step.get("then", {})
            expected_events = then.get("events", [])
            expected_state = _yaml_str(then.get("new_state", ""))
            expected_error = then.get("error", "")

            normalized.append({
                "command": command,
                "params": params,
                "expected_events": expected_events if isinstance(expected_events, list) else [expected_events],
                "expected_state": expected_state,
                "expected_error": expected_error,
                "given": step.get("given", {}),
            })

    return normalized


def _yaml_str(val: Any) -> str:
    if isinstance(val, bool):
        return "on" if val else "off"
    return str(val) if val else ""


def _extract_givens(steps: list[dict[str, Any]]) -> dict[str, Any]:
    givens: dict[str, Any] = {}
    for step in steps:
        given = step.get("given", {})
        if isinstance(given, dict):
            light_id = given.get("light_id", given.get("id", ""))
            state = _yaml_str(given.get("state", ""))
            if light_id and state:
                givens[light_id] = state
    return givens


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
        self._twin_cls: type | None = None
        self._module: Any = None

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

        self._twin_cls = twin_cls
        self._module = module
        self._twin_instance = self._instantiate(twin_cls)

        print(f"[runner] Loaded twin: {twin_cls.__name__}")
        return self._twin_instance

    def _instantiate(self, twin_cls: type, initial_state: dict[str, Any] | None = None) -> Any:
        if initial_state:
            try:
                return twin_cls(lights=initial_state)
            except TypeError:
                try:
                    return twin_cls(initial_state)
                except Exception:
                    pass
        try:
            return twin_cls()
        except TypeError:
            try:
                from types import SimpleNamespace
                return twin_cls(SimpleNamespace(**{}), SimpleNamespace(**{}))
            except Exception:
                raise RuntimeError(
                    f"Could not instantiate {twin_cls.__name__}. "
                    "Make sure TwinEngine has a no-arg __init__ or handle constructor args."
                )

    def reinit(self, initial_state: dict[str, Any] | None = None) -> None:
        if self._twin_cls is None:
            self.load()
        assert self._twin_cls is not None
        self._twin_instance = self._instantiate(self._twin_cls, initial_state)

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

    def run_all_scenarios(self, scenarios: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
        normalized = _normalize_scenarios(scenarios)
        all_results: list[dict[str, Any]] = []

        for scenario in normalized:
            name = scenario.get("name", scenario.get("description", "unnamed"))
            steps = scenario.get("steps", [])

            initial_state = _extract_givens(steps)
            self.reinit(initial_state if initial_state else None)

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
