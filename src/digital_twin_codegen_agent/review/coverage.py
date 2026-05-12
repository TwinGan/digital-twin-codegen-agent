import re
from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class CoverageGap:
    category: str
    item: str
    detail: str = ""
    severity: str = "warning"


@dataclass
class CoverageResult:
    spec_commands: list[str] = field(default_factory=list)
    spec_events: list[str] = field(default_factory=list)
    spec_errors: list[str] = field(default_factory=list)
    spec_invariants: list[str] = field(default_factory=list)
    spec_transitions: list[dict[str, Any]] = field(default_factory=list)

    code_commands: list[str] = field(default_factory=list)
    code_events: list[str] = field(default_factory=list)
    code_errors: list[str] = field(default_factory=list)

    gaps: list[CoverageGap] = field(default_factory=list)

    @property
    def command_coverage(self) -> float:
        if not self.spec_commands:
            return 1.0
        spec_set = set(self.spec_commands)
        code_set = set(self.code_commands)
        return len(spec_set & code_set) / len(spec_set)

    @property
    def event_coverage(self) -> float:
        if not self.spec_events:
            return 1.0
        spec_set = set(self.spec_events)
        code_set = set(self.code_events)
        return len(spec_set & code_set) / len(spec_set)

    @property
    def error_coverage(self) -> float:
        if not self.spec_errors:
            return 1.0
        spec_set = set(self.spec_errors)
        code_set = set(self.code_errors)
        return len(spec_set & code_set) / len(spec_set)


def analyze_coverage(spec_yaml: str, generated_code: str) -> CoverageResult:
    result = CoverageResult()

    spec_data = yaml.safe_load(spec_yaml)
    if spec_data is None:
        result.gaps.append(CoverageGap("parse", "spec", "Cannot parse spec YAML", "error"))
        return result

    _extract_spec_commands(spec_data, result)
    _extract_spec_transitions(spec_data, result)
    _extract_spec_invariants(spec_data, result)

    _extract_code_commands(generated_code, result)
    _extract_code_events(generated_code, result)
    _extract_code_errors(generated_code, result)

    _find_gaps(result)

    return result


def _extract_spec_commands(spec_data: dict[str, Any], result: CoverageResult) -> None:
    commands = spec_data.get("commands", {})
    if isinstance(commands, dict):
        for cmd_name, cmd_def in commands.items():
            if isinstance(cmd_def, dict):
                result.spec_commands.append(cmd_name)
                effect = cmd_def.get("effect", {})
                event_name = effect.get("emit_event", "")
                if event_name and event_name not in result.spec_events:
                    result.spec_events.append(event_name)
                for v in cmd_def.get("validation", []):
                    if isinstance(v, dict):
                        error = v.get("error", "")
                        if error and error not in result.spec_errors:
                            result.spec_errors.append(error)
    elif isinstance(commands, list):
        for cmd in commands:
            if isinstance(cmd, dict):
                result.spec_commands.append(cmd.get("name", ""))

    validation_rules = spec_data.get("validation_rules", [])
    if isinstance(validation_rules, list):
        for rule in validation_rules:
            if isinstance(rule, dict):
                error = rule.get("error_code", "")
                if error and error not in result.spec_errors:
                    result.spec_errors.append(error)

    events = spec_data.get("events", [])
    if isinstance(events, list):
        for ev in events:
            if isinstance(ev, str) and ev not in result.spec_events:
                result.spec_events.append(ev)
            elif isinstance(ev, dict):
                ev_name = ev.get("name", ev.get("type", ""))
                if ev_name and ev_name not in result.spec_events:
                    result.spec_events.append(ev_name)


def _extract_spec_transitions(spec_data: dict[str, Any], result: CoverageResult) -> None:
    transitions = spec_data.get("transition_rules", spec_data.get("transitions", []))
    if isinstance(transitions, list):
        for t in transitions:
            if isinstance(t, dict):
                result.spec_transitions.append({
                    "command": t.get("command", ""),
                    "from_state": t.get("from", ""),
                    "to_state": t.get("to", ""),
                    "event": t.get("event", ""),
                    "error": t.get("error", ""),
                })


def _extract_spec_invariants(spec_data: dict[str, Any], result: CoverageResult) -> None:
    invariants = spec_data.get("invariants", [])
    if isinstance(invariants, list):
        for inv in invariants:
            if isinstance(inv, str):
                result.spec_invariants.append(inv)
            elif isinstance(inv, dict):
                for v in inv.values():
                    if isinstance(v, str):
                        result.spec_invariants.append(v)


def _extract_code_commands(code: str, result: CoverageResult) -> None:
    for m in re.finditer(r'if command\s*==\s*"([^"]+)"', code):
        result.code_commands.append(m.group(1))
    for m in re.finditer(r"if command\s*==\s*'([^']+)'", code):
        result.code_commands.append(m.group(1))
    for m in re.finditer(r"_handle_(\w+)", code):
        cmd = m.group(1)
        if cmd not in result.code_commands:
            result.code_commands.append(cmd)


def _extract_code_events(code: str, result: CoverageResult) -> None:
    for m in re.finditer(r'"type":\s*"([^"]+)"', code):
        result.code_events.append(m.group(1))
    for m in re.finditer(r"emit_event.*?['\"](\w+)['\"]", code):
        result.code_events.append(m.group(1))


def _extract_code_errors(code: str, result: CoverageResult) -> None:
    for m in re.finditer(r'"error":\s*"([^"]+)"', code):
        error = m.group(1)
        if error and error not in result.code_errors:
            result.code_errors.append(error)
    for m in re.finditer(r'error_code\s*=\s*"([^"]+)"', code):
        result.code_errors.append(m.group(1))
    for m in re.finditer(r"Error\(\"([^\"]+)\"\)", code):
        result.code_errors.append(m.group(1))


def _find_gaps(result: CoverageResult) -> None:
    spec_cmd_set = set(result.spec_commands)
    code_cmd_set = set(result.code_commands)

    for cmd in sorted(spec_cmd_set - code_cmd_set):
        result.gaps.append(CoverageGap("command", cmd, "Spec command not found in generated code", "error"))

    for cmd in sorted(code_cmd_set - spec_cmd_set):
        if cmd != "unknown_command":
            result.gaps.append(CoverageGap("command", cmd, "Code handles command not in spec", "warning"))

    spec_event_set = set(result.spec_events)
    code_event_set = set(result.code_events)

    for ev in sorted(spec_event_set - code_event_set):
        result.gaps.append(CoverageGap("event", ev, "Spec event not emitted in code", "error"))

    spec_err_set = set(result.spec_errors)
    code_err_set = set(result.code_errors)

    for err in sorted(spec_err_set - code_err_set):
        if err:
            result.gaps.append(CoverageGap("error_code", err, "Spec error code not handled in code", "error"))

    for transition in result.spec_transitions:
        cmd = transition.get("command", "")
        if cmd not in code_cmd_set:
            continue
        ev = transition.get("event", "")
        if ev and ev not in code_event_set:
            result.gaps.append(CoverageGap(
                "transition", f"{cmd}: {transition.get('from_state','?')} -> {transition.get('to_state','?')}",
                f"Expected event '{ev}' not found in code", "error"
            ))
