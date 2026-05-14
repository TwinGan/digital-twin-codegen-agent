## Architecture for Simplified Executable Digital Twin Model

### Overview

The model reproduces the **externally observable states and outputs** of the Historical Market Data PCAP Pipeline. It is deterministic, driven purely by injected test fixtures, and avoids any real infrastructure. The design focuses on reproducing the lifecycle of `PCAPFile` entities (states, validation results) and the generation of jobs, events, and alerts as defined in the digital twin spec.

### Modules & Classes

| Module | Class | Responsibility |
|--------|-------|----------------|
| **Core Model** | `PipelineModel` | Orchestrates all state transitions, job creation, event emission. Holds all state. |
| **Calendar** | `Calendar` | Provides holiday/weekday checking based on a static list. |
| **State Store** | `PCAPFile` (dataclass), `Job` (dataclass), `ValidationResult` (dict) | Immutable value objects representing entity state. |
| **Event Bus** | `EventLog` (list of dicts) | Collects all generated events for later comparison. |
| **Test Fixture Injection** | `TestScenario` (helper) | Configures expected download/validation outcomes per file before simulation. |
| **Comparison** | `ModelComparator` | Compares expected (model) outputs with actual SUT outputs. |

No database or network modules are needed – all state lives in memory.

### State Representation

#### 1. `PCAPFile`
```python
@dataclass
class PCAPFile:
    feed_id: str          # "A-FEED" or "B-FEED"
    message_code: str     # e.g. "FEED_A_CORE_L2_DC1"
    business_day: str     # ISO date "2026-05-13"
    state: str            # one of the lifecycle states (see below)
    size: Optional[int] = None
    validation_result: Optional[dict] = None
    market_state_events: Optional[list] = None

    # Unique identity: (feed_id, message_code, business_day)
```

**Lifecycle states** (extended from spec):
- `not_downloaded`  (initial)
- `downloaded`      (valid download output, size > 0)
- `validated_pass`  (validation overall = pass)
- `validated_fail`  (validation overall = fail)
- `uploaded`         (*after* successful upload)
- `archived`         (terminal)
- `empty_holiday`    (terminal, set when file is empty on a holiday – special end state)

Transitions are governed by job completions (see Command Handling below).

#### 2. `Job`
```python
@dataclass
class Job:
    job_id: str          # unique
    type: str            # "download", "validate", "upload", "archive"
    parameters: dict     # {feed_id, message_code, business_day}
    state: str           # "triggered", "running", "succeeded", "failed"
    error: Optional[str] = None
```

#### 3. `ValidationResult`
A dictionary with keys:
- `file_level`: `"pass"`|`"fail"`
- `protocol_level`: `"pass"`|`"fail"`
- `packet_level`: `"pass"`|`"fail"`
- `empty_file`: `"normal_holiday"`|`"exception_nonholiday"`|`"not_empty"`
- `overall`: `"pass"`|`"fail"`|`"empty_normal"`

Set by the model when a validation job completes, using the pre‑injected fixture.

#### 4. Events
All events are dictionaries stored in `EventLog`:
```python
event = {
    "type": "JobTriggered"|"JobSucceeded"|"JobFailed"|"DownloadFailureAlert"| ...,
    "timestamp": iso_string,    # optional, for ordering
    "payload": { ... }
}
```

### Command Handling Flow

The model exposes high‑level methods that correspond to API triggers or cron tasks.  
Every command first checks preconditions, job idempotency, then transitions state and emits events.

#### Method signatures (on `PipelineModel`)

- **`trigger_download(feed, code, date) -> job_id`**
- **`complete_download(job_id, success: bool, file_size: int)`**
- **`trigger_validation(feed, code, date) -> job_id`**
- **`complete_validation(job_id, success: bool, overall: str, empty_file: str, market_events: list)`**
- **`trigger_upload(feed, code, date) -> job_id`**
- **`complete_upload(job_id, success: bool)`**
- **`trigger_archive(feed, code, date) -> job_id`**
- **`complete_archive(job_id, success: bool)`**

*Note*: `complete_*` methods accept the final outcome; the model does not simulate the actual work. If a validation job “succeeds” (job.state = succeeded) but the validation result is `overall=fail`, the alert is still fired.

#### Pre‑condition checking
- `trigger_download`: no job of type “download” for same params exists in triggered/running state.
- `trigger_validation`: PCAPFile must be in `downloaded` state.
- `trigger_upload`: PCAPFile must be `validated_pass`.
- `trigger_archive`: PCAPFile must be `uploaded`.

If pre‑conditions are violated, the method raises an exception (test must ensure correct sequencing).

#### Flow example – download
1. `trigger_download` → creates `Job(state=triggered)`, emits `JobTriggered`.
2. `complete_download(job_id, success=True, file_size=150000)`:
   - Job → `succeeded`, emits `JobSucceeded`.
   - PCAPFile → `downloaded`, `size` set, filename generated (e.g. `LMEFTcad_yyyymmdd.zip`).
   - If `success=False`: Job → `failed`, emits `JobFailed` **and** `DownloadFailureAlert`.

### Event Generation Flow

Events are emitted at every state change. The following table summarises the triggers:

| Event | Trigger Condition |
|-------|-------------------|
| `JobTriggered` | Any job enters state `triggered` |
| `JobSucceeded` | Job transitions to `succeeded` |
| `JobFailed` | Job transitions to `failed` |
| `DownloadFailureAlert` | `JobFailed` for a download job |
| `ValidationFailureAlert` | `ValidationResult.overall = fail` (regardless of job success) |
| `EmptyFileNonHolidayAlert` | `ValidationResult.empty_file = exception_nonholiday` |
| `UploadFailureAlert` | `JobFailed` for an upload job |
| `OtherExceptionAlert` | Any unclassified exception (system error) |
| `MarketStateEventsRecorded` | After a successful validation that found market state messages (payload includes the list) |
| `DashboardUpdated` | After every validation result (payload aggregates trading states for that business day) |

**Note on market state events and dashboard**:  
When a validation job completes and the overall is `pass`, the model uses the injected `market_state_events` list to emit `MarketStateEventsRecorded`. Immediately afterwards, it emits `DashboardUpdated` with an aggregated view of all market states for that business day (constructed from all valid files seen so far). If injected events are empty, the dashboard update is still sent (with an empty stateset) to reflect that the day was processed.

### Comparison Strategy

The model is designed to be executed **before or after** the real SUT for a given scenario, producing an expected trace.

1. **Setup**:  
   - Configure the `Calendar` with the holiday list.  
   - For each (feed, code, date) that will be involved, call  
     `model.set_expected_download(feed, code, date, file_size)` and  
     `model.set_expected_validation(feed, code, date, overall, empty_file, market_events)`.  
   - This defines the ground truth.

2. **Execution**:  
   - Run the same sequence of commands on the model as the test script does on the SUT (e.g., `trigger_download`, `complete_download`, etc.).  
   - The model updates its internal state and event log.

3. **Comparison**:  
   - **State comparison**: For every `PCAPFile` that exists in the model, query the SUT for the same entity (via database or API) and assert that:
     - `state` matches (the model may have `empty_holiday`; if SUT uses a different terminal state, adapt mapping).
     - `validation_result` matches (if present).
   - **Event/log comparison**:  
     The model’s `EventLog` contains all expected alerts and status events. The test verifies that:
     - Email alerts were sent to the correct recipient groups (by checking the SUT’s mail log or mock inbox).
     - Dashboard update calls were made (if the SUT exposes such a hook).
   - **Market state events**: Compare the extracted market state events (from the SUT’s output) with the injected fixture.

   The comparison can be performed as a simple **diff** between two JSON structures (expected vs actual), allowing small tolerance in event ordering if the SUT is asynchronous. A good practice is to capture the final snapshot of entities and the set of unique events, ignoring time‑ordering nuances.

### Limitations

1. **No real packet validation** – The model relies on pre‑injected outcomes; it cannot detect protocol‑level issues from a real PCAP.
2. **No concurrency or timing** – Jobs are processed sequentially; the one‑hour delay and exact cron scheduling are not simulated.
3. **Simplified empty‑holiday handling** – The introduction of `empty_holiday` as a terminal state is a model choice; the real system may behave differently (e.g., no persistent file entry).
4. **No Corvil API simulation** – All data is assumed to come from the Corvil platform, but the model does not emulate it.
5. **Static calendar** – Holidays are a fixed list; no dynamic updates.
6. **Single‑threaded execution** – The model does not enforce that only one job of a type runs at a time beyond naive state checks; it’s up to the test to sequence actions correctly.
7. **Filename generation** – Uses a placeholder pattern; real naming may vary per metal/market.
8. **Alert content** – The model emits alert events but does not generate the exact email body.
9. **No duplicate detection** – If a job is triggered while one is running, the model will either allow it (if no state check) or raise an error; the spec’s “only one instance” rule is not fully implemented, requiring careful test design.

The model is sufficient to generate **expected results** for all given scenarios and invariants, providing a reference oracle for the SUT’s externally visible behaviour.