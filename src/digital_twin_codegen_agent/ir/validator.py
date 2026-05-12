from dataclasses import dataclass, field

from .schemas import TwinSpec


@dataclass
class ValidationResult:
    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.passed = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_spec(spec: TwinSpec) -> ValidationResult:
    result = ValidationResult()

    if not spec.name:
        result.add_warning("Twin spec has no name")
    if not spec.commands:
        result.add_error("No commands defined")
    if not spec.transitions:
        result.add_error("No transitions defined")
    if not spec.scenarios:
        result.add_warning("No scenarios defined")

    command_names = {cmd.name for cmd in spec.commands}

    for transition in spec.transitions:
        if transition.command not in command_names:
            result.add_error(
                f"Transition '{transition.command} -> {transition.to_state}' "
                f"references undefined command '{transition.command}'"
            )
        if not transition.events:
            result.add_warning(
                f"Transition '{transition.command} -> {transition.to_state}' has no events"
            )
        if not transition.conditions:
            result.add_warning(
                f"Transition '{transition.command} -> {transition.to_state}' has no conditions"
            )

    for rule in spec.validation_rules:
        for cmd_name in rule.applies_to:
            if cmd_name not in command_names:
                result.add_warning(
                    f"Validation rule '{rule.rule}' references unknown command '{cmd_name}'"
                )

    defined_states: set[str] = set()
    for entity in spec.entities:
        defined_states.update(entity.states)
    for transition in spec.transitions:
        if transition.to_state not in defined_states and transition.to_state:
            result.add_warning(
                f"Transition '{transition.command} -> {transition.to_state}' "
                f"targets state '{transition.to_state}' not defined in any entity"
            )
        if transition.from_state and transition.from_state not in defined_states:
            result.add_warning(
                f"Transition '{transition.command}' starts from unknown state '{transition.from_state}'"
            )

    for cmd in spec.commands:
        if cmd.name not in {t.command for t in spec.transitions}:
            result.add_warning(f"Command '{cmd.name}' has no transitions")

    for invariant in spec.invariants:
        if not invariant.strip():
            result.add_warning("Empty invariant string found")

    for scenario in spec.scenarios:
        for step in scenario.steps:
            if step.command not in command_names:
                result.add_error(
                    f"Scenario '{scenario.name}' step references undefined command '{step.command}'"
                )
            if step.expected_state and step.expected_state not in defined_states:
                result.add_warning(
                    f"Scenario '{scenario.name}' step expects state '{step.expected_state}' "
                    f"not defined in any entity"
                )

    return result
