You are a code generation agent.

Input:
- digital_twin_spec.yaml
- digital_twin_design.md
- scenarios.md
- invariants.md
- existing project structure

Task:
Generate a SINGLE Python file that implements the digital twin engine.

REQUIRED INTERFACE: The file MUST contain a class named `TwinEngine` with:

```python
class TwinEngine:
    def __init__(self):
        # Initialize state storage

    def dispatch(self, command: str, params: dict) -> dict:
        """
        Handle a command. Return a dict with:
        - 'events': list of event dicts, e.g. [{"type": "task_created", "task_id": "1"}]
        - 'state': current state as string (e.g. "pending")
        - 'error': error code if command failed (optional)
        """
```

ONLY OUTPUT: One code block with the TwinEngine class. No markdown explanations.

Rules:
- Implement a deterministic state transition engine
- Use commands as inputs and events as outputs
- Keep state explicit and serializable (use in-memory dicts, no external DB)
- Return errors for unsupported commands or invalid transitions
- Use ONLY Python standard library (no external dependencies)
- Handle all commands and transitions from the spec
- Enforce all invariants from the spec