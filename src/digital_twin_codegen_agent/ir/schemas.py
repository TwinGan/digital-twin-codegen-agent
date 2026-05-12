from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PropertyDef:
    name: str
    type: str
    required: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PropertyDef:
        return cls(
            name=data["name"],
            type=data.get("type", "string"),
            required=data.get("required", False),
        )


@dataclass
class Entity:
    name: str
    states: list[str] = field(default_factory=list)
    properties: list[PropertyDef] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entity:
        props = [PropertyDef.from_dict(p) for p in data.get("properties", [])]
        return cls(
            name=data["name"],
            states=data.get("states", []),
            properties=props,
        )


@dataclass
class CommandParam:
    name: str
    type: str
    required: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommandParam:
        return cls(
            name=data["name"],
            type=data.get("type", "string"),
            required=data.get("required", False),
        )


@dataclass
class Command:
    name: str
    description: str = ""
    parameters: list[CommandParam] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Command:
        params = [CommandParam.from_dict(p) for p in data.get("parameters", [])]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            parameters=params,
        )


@dataclass
class Transition:
    command: str
    from_state: str | None
    to_state: str
    conditions: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Transition:
        from_state = data.get("from_state")
        if from_state == "null" or from_state == "":
            from_state = None
        return cls(
            command=data["command"],
            from_state=from_state,
            to_state=data["to_state"],
            conditions=data.get("conditions", []),
            events=data.get("events", []),
        )


@dataclass
class ValidationRule:
    rule: str
    applies_to: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationRule:
        return cls(
            rule=data["rule"],
            applies_to=data.get("applies_to", []),
        )


@dataclass
class ScenarioStep:
    command: str
    params: dict[str, Any] = field(default_factory=dict)
    expected_events: list[str] = field(default_factory=list)
    expected_state: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScenarioStep:
        return cls(
            command=data["command"],
            params=data.get("params", {}),
            expected_events=data.get("expected_events", []),
            expected_state=data.get("expected_state", ""),
        )


@dataclass
class Scenario:
    name: str
    steps: list[ScenarioStep] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scenario:
        steps = [ScenarioStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            name=data["name"],
            steps=steps,
        )


@dataclass
class TwinSpec:
    name: str = ""
    version: str = "1.0.0"
    entities: list[Entity] = field(default_factory=list)
    commands: list[Command] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    validation_rules: list[ValidationRule] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)
    scenarios: list[Scenario] = field(default_factory=list)

    def get_command(self, name: str) -> Command | None:
        for cmd in self.commands:
            if cmd.name == name:
                return cmd
        return None

    def get_entity(self, name: str) -> Entity | None:
        for ent in self.entities:
            if ent.name == name:
                return ent
        return None

    def get_transitions_for_command(self, command_name: str) -> list[Transition]:
        return [t for t in self.transitions if t.command == command_name]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TwinSpec:
        twin_data = data.get("twin", {})
        entities = [Entity.from_dict(e) for e in data.get("entities", [])]
        commands = [Command.from_dict(c) for c in data.get("commands", [])]
        transitions = [Transition.from_dict(t) for t in data.get("transitions", [])]
        rules = [ValidationRule.from_dict(r) for r in data.get("validation_rules", [])]
        scenarios = [Scenario.from_dict(s) for s in data.get("scenarios", [])]
        return cls(
            name=twin_data.get("name", ""),
            version=twin_data.get("version", "1.0.0"),
            entities=entities,
            commands=commands,
            transitions=transitions,
            validation_rules=rules,
            invariants=data.get("invariants", []),
            scenarios=scenarios,
        )
