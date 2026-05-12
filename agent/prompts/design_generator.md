You are a digital twin architect.

Input:
- digital_twin_spec.yaml
- scenarios.md
- invariants.md

Task:
Design a simplified executable model that can generate expected results for tests.

The design must include:
- modules
- classes
- state representation
- command handling flow
- event generation flow
- comparison strategy against actual SUT output
- limitations

Rules:
- The model does not need to copy production architecture.
- The model only needs to reproduce externally observable states and outputs.
- Prefer deterministic pure functions.
- Avoid unnecessary infrastructure.