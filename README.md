# Digital Twin Codegen Agent

An LLM-powered agent pipeline that automatically generates a **digital twin** — a deterministic, executable behavioral model — from Product Requirements Documents (PRDs). The twin serves as a **test oracle**: given any command, it predicts the expected system output, enabling automated test validation against the real system-under-test.

## How It Works

```
  PRD Docs ──→ [Stage 1: Analyze] ──→ domain_inventory.md
                                        │
              [Stage 2: Spec] ◄─────────┘
                    │
                    ▼
              digital_twin_spec.yaml + scenarios.md + invariants.md
                    │
              [Stage 3: Design] ◄───────┘
                    │
                    ▼
              digital_twin_design.md
                    │
              [Stage 4: Generate] ◄─────┘
                    │
                    ▼
              generated_twin/twin.py
                    │
              [Stage 5: Test] ◄─────────┘  ──→ test_twin.py + Runner Report
                    │
              [Stage 6: Review] ◄─────────┘  ──→ review_report.md
                    │
              [Stage 7: Fuzz-Gen] ◄──────┘  ──→ fuzz_testcases.py
```

Seven sequential LLM-driven stages, each consuming the previous stage's output. Run the full pipeline or any individual stage.

## Installation

```bash
# Clone the repo
git clone <repo-url>
cd digital-twin-codegen-agent

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# Install with dependencies
pip install -e .
```

## Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-pro
OPENAI_STREAMING=false
```

The agent uses the OpenAI-compatible SDK. Set `OPENAI_API_BASE_URL` to any compatible provider (DeepSeek, OpenAI, local LLM, etc.). The URL is automatically normalized with `/v1` suffix.

## Usage

### Full Pipeline

```bash
dt-codegen build-all ./my_docs
```

Runs all 7 stages sequentially and writes outputs to `artifacts/` and `workspace/`.

### Individual Stages

```bash
# Stage 1: Analyze PRD documents → extracts domain entities, commands, states, transitions
dt-codegen analyze ./my_docs

# Stage 2: Generate behavioral spec → YAML spec from domain inventory
dt-codegen spec

# Stage 3: Generate architecture design → module/class structure
dt-codegen design

# Stage 4: Generate twin code → Python implementation (TwinEngine class)
dt-codegen generate

# Stage 5: Generate tests + run scenarios → validates twin against spec
dt-codegen test

# Stage 6: Review generated code → audit report (coverage, invariants, fidelity)
dt-codegen review

# Stage 7: Generate fuzz testcase module → twin-as-oracle CSV export
dt-codegen input-gen
```

Individual stages resume from existing artifacts on disk — you can re-run any stage without re-running previous ones.

### CLI Reference

```
dt-codegen build-all <docs_dir>    Run the full pipeline
dt-codegen analyze <docs_dir>      Run document analysis
dt-codegen spec                    Generate behavior spec
dt-codegen design                  Generate architecture design
dt-codegen generate                Generate twin implementation
dt-codegen test                    Generate tests + run scenarios
dt-codegen review                  Review generated code against spec
dt-codegen input-gen               Generate fuzz testcase module
```

## Project Structure

```
├── prompts/                          # LLM system prompts (7 stages)
│   ├── 01_document_analyzer.md       # Domain extraction from PRD
│   ├── 02_spec_generator.md          # Behavioral spec YAML generation
│   ├── 03_design_generator.md        # Architecture design
│   ├── 04_codegen.md                 # Twin code generation
│   ├── 05_test_generator.md          # Test code generation
│   ├── 06_reviewer.md                # Code review / audit
│   └── 07_input_generator.md         # Fuzz testcase module generation
│
├── src/digital_twin_codegen_agent/   # Source code
│   ├── cli.py                        # CLI entry point (argparse)
│   ├── config.py                     # .env loader + Config dataclass
│   ├── llm.py                        # OpenAI-compatible LLM client
│   ├── pipeline.py                   # Pipeline orchestrator (7 stages)
│   ├── documents/
│   │   ├── loader.py                 # Load .md/.txt files from directory
│   │   └── chunker.py                # Heading-aware document chunking
│   ├── ir/
│   │   ├── schemas.py                # IR data models (Entity, Command, Transition, etc.)
│   │   ├── parser.py                 # Parse YAML spec → IR objects
│   │   └── validator.py              # Validate spec completeness
│   ├── codegen/
│   │   └── __init__.py               # CodeGenerator (LLM → Python)
│   ├── execution/
│   │   └── runner.py                 # TwinRunner (load twin, run scenarios, compare)
│   ├── review/
│   │   ├── coverage.py               # Coverage analysis (stub)
│   │   └── report.py                 # Review report generation (stub)
│   └── artifacts/
│       └── writer.py                 # Persist pipeline outputs to disk
│
├── artifacts/                        # Pipeline outputs (auto-generated)
│   ├── domain_inventory.md
│   ├── digital_twin_spec.yaml
│   ├── digital_twin_design.md
│   ├── generated_twin.py
│   ├── fuzz_testcases.py
│   └── review_report.md
│
├── workspace/generated_twin/         # Generated twin code
│   ├── twin.py                       # TwinEngine implementation
│   ├── test_twin.py                  # Auto-generated test suite
│   └── fuzz_testcases.py             # Fuzz testcase module (twin-as-oracle CSV export)
│
├── docs/                             # Sample PRD documents
├── pyproject.toml                    # Project metadata + dependencies
├── .env                              # API configuration (not committed)
└── README.md
```

## Generated Twin Interface

Every generated twin exposes a consistent interface:

```python
class TwinEngine:
    def dispatch(self, command: str, params: dict) -> dict:
        """
        Returns:
        {
            "events": [{"type": "event_name", ...}],
            "state": "current_state",
            "error": ""           # empty on success, error code on failure
        }
        """
```

## Writing PRD Documents

Place `.md` or `.txt` files in a directory. Each file should describe the system in terms of:

- **Entities**: Domain objects and their properties
- **States**: Possible states for each entity
- **Commands**: User actions with parameters, validation rules, and expected behavior
- **Transitions**: What happens when a command fires (from state → to state, events emitted)
- **Invariants**: Rules that must always hold
- **Scenarios**: Concrete step-by-step examples

Example (`docs/light_switch_prd.md`):

```markdown
# Light Switch System

## Entities
### Light
- Properties: id (string), state (string)
- States: off, on

## Commands
### turn_on
- Parameters: light_id (string, required)
- Behavior: Sets state to "on", fires light_turned_on event
- Validation: light must exist, must not already be on

### turn_off
- Parameters: light_id (string, required)
- Behavior: Sets state to "off", fires light_turned_off event
- Validation: light must exist, must not already be off

## Business Rules
- A light that is on cannot be turned on again
- Light IDs must be unique

## Scenarios
### Turn on a light
1. turn_on("kitchen") → state=on, event=light_turned_on

### Error: turn on already on
1. turn_on("kitchen") → state=on
2. turn_on("kitchen") → error=already_on
```

## Fuzz Testcase Generation (Stage 7)

After the twin is validated by Stage 5 (Test) and Stage 6 (Review), Stage 7 generates a standalone `fuzz_testcases.py` module that uses the twin as a **test oracle** to mass-produce labeled test data:

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Spec YAML     │────▶│  Bake-in COMMANDS│────▶│  Random Mutation │
│  (commands,     │     │  dict into module│     │  of valid params │
│   params)       │     └──────────────────┘     └────────┬─────────┘
└─────────────────┘                                       │
                                                  ┌───────▼─────────┐
                                                  │ Multi-step      │
                                                  │ sequences       │
                                                  │ (twin-as-oracle)│
                                                  └───────┬─────────┘
                                                          │
                                                  ┌───────▼─────────┐
                                                  │  CSV Export     │
                                                  │  input → expect │
                                                  └─────────────────┘
```

**Key features:**
- **Twin-as-oracle**: The validated digital twin produces expected results for comparison against real system output
- **Random fuzz**: Randomly selects valid commands and mutates params within defined domains
- **Multi-step sequences**: Captures stateful behavior flows (1-5 steps per sequence)
- **Reproducible**: `--seed` flag ensures identical output across runs
- **CSV export**: Export labeled test data for real-system comparison testing

```bash
# Generate the fuzz module (via LLM)
dt-codegen input-gen

# Run the module: 100 sequences, seeded for reproducibility
python workspace/generated_twin/fuzz_testcases.py --count 100 --seed 42 --output testcases.csv

# Dry-run: preview generated sequences without twin execution
python workspace/generated_twin/fuzz_testcases.py --count 5 --dry-run
```

**CSV output format:**

```
sequence_id | step | command | params_json | expected_events_json | expected_state | expected_error
```

Each row is one step in a multi-step sequence, linked by `sequence_id`. The CSV can be fed into real-system comparison tools.

## Running Tests Against the Twin

The `test` command automatically:
1. Loads the generated `twin.py`
2. Extracts all scenarios from the YAML spec
3. Runs each scenario step-by-step via `dispatch()`
4. Compares actual events/state/errors against expected values
5. Prints a pass/fail report

Example output:
```
==================================================
  Twin Execution Report: 5/5 scenarios passed
==================================================

  Scenario: turn_on_light [PASS]
    [PASS] turn_on({"light_id": "kitchen"})
         expected events: ['light_turned_on']
         actual events:   ['light_turned_on']
         expected state:  on
         actual state:    on

  Scenario: non_existent_light [PASS]
    [PASS] turn_on({"light_id": "unknown"})
         expected error:  light_not_found
         actual error:    light_not_found
==================================================
  Total: 5/5 passed.
==================================================
```

## Dependencies

- **Python** >= 3.10
- **openai** >= 1.0.0 — LLM API client (OpenAI-compatible)
- **pyyaml** >= 6.0 — YAML spec parsing
- **python-dotenv** >= 1.0.0 — .env file loading

No other external dependencies. The generated twin uses only Python standard library.
