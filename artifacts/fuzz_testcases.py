import sys
import argparse
import random
import json
import csv

# ----------------------------------------------------------------------
# Hardcoded command space derived from twin's dispatch interface
# ----------------------------------------------------------------------
COMMANDS = {
    "set_holidays": {
        "params": {
            "dates": [
                ["2026-12-25", "2026-07-15"],
                ["2026-01-01", "2026-05-01"],
            ]
        }
    },
    "trigger_download": {
        "params": {
            "feedId": ["A-FEED", "B-FEED"],
            "businessDay": ["2026-05-13", "2026-12-25", "2026-07-15", "20260413"],
            "messageCodes": [
                ["FEED_A_CORE_L2_DC1"],
                ["FEED_A_CORE_L2_DC1", "FEED_A_CORE_L3_DC1"],
                ["FEED_B_CORE_L2_DC1", "FEED_B_CORE_L3_DC1"],
                None,   # optional
            ],
        }
    },
    "complete_download": {
        "params": {
            "job_id": ["job-1", "job-2", "job-42", "nonexistent"],
            "success": [True, False],
            "file_size": [0, 1024, 999999, None],
        }
    },
    "trigger_validation": {
        "params": {
            "feedId": ["A-FEED", "B-FEED"],
            "businessDay": ["2026-05-13", "2026-12-25", "2026-07-15"],
            "messageCodes": [
                ["FEED_A_CORE_L2_DC1"],
                ["FEED_A_CORE_L2_DC1", "FEED_A_CORE_L3_DC1"],
                ["FEED_B_CORE_L2_DC1", "FEED_B_CORE_L3_DC1"],
                None,
            ],
        }
    },
    "complete_validation": {
        "params": {
            "job_id": ["job-1", "job-2", "job-42", "nonexistent"],
            "success": [True, False],
            "validation_result": [
                {"overall": "pass"},
                {"overall": "fail", "empty_file": "exception_nonholiday"},
                {"overall": "empty_normal", "empty_file": "normal_holiday"},
                None,
            ],
            "market_events": [
                [],
                [{"type": "opening", "time": "08:00:00"}],
                None,
            ],
        }
    },
    "trigger_upload": {
        "params": {
            "feedId": ["A-FEED", "B-FEED"],
            "messageCode": [
                "FEED_A_CORE_L2_DC1",
                "FEED_A_CORE_L3_DC1",
                "FEED_B_CORE_L2_DC1",
                "FEED_B_CORE_L3_DC1",
            ],
            "businessDay": ["2026-05-13", "2026-12-25", "2026-07-15"],
        }
    },
    "complete_upload": {
        "params": {
            "job_id": ["job-1", "job-2", "job-42", "nonexistent"],
            "success": [True, False],
        }
    },
    "trigger_archive": {
        "params": {
            "feedId": ["A-FEED", "B-FEED"],
            "messageCode": [
                "FEED_A_CORE_L2_DC1",
                "FEED_A_CORE_L3_DC1",
                "FEED_B_CORE_L2_DC1",
                "FEED_B_CORE_L3_DC1",
            ],
            "businessDay": ["2026-05-13", "2026-12-25", "2026-07-15"],
        }
    },
    "complete_archive": {
        "params": {
            "job_id": ["job-1", "job-2", "job-42", "nonexistent"],
            "success": [True, False],
        }
    },
    "cron_download_task": {
        "params": {
            "businessDay": ["2026-05-13", "2026-12-25", "2026-07-15", "2026-02-30"],
        }
    },
    "cron_validation_task": {
        "params": {
            "businessDay": ["2026-05-13", "2026-12-25", "2026-07-15"],
        }
    },
    "cron_upload_task": {
        "params": {
            "businessDay": ["2026-05-13", "2026-12-25", "2026-07-15"],
        }
    },
    "cron_archive_purge_task": {
        "params": {}
    },
    "get_file_state": {
        "params": {
            "feedId": ["A-FEED", "B-FEED"],
            "messageCode": [
                "FEED_A_CORE_L2_DC1",
                "FEED_A_CORE_L3_DC1",
                "FEED_B_CORE_L2_DC1",
                "FEED_B_CORE_L3_DC1",
            ],
            "businessDay": ["2026-05-13", "2026-12-25", "2026-07-15"],
        }
    },
}

# ----------------------------------------------------------------------
# Error injection operations
# ----------------------------------------------------------------------
def _random_drop_param(step):
    """Remove a random parameter from `step["params"]` (if any)."""
    if step["params"]:
        key = random.choice(list(step["params"].keys()))
        del step["params"][key]
    return step

def _random_wrong_type(step):
    """Replace a random parameter value with a bogus type."""
    if step["params"]:
        key = random.choice(list(step["params"].keys()))
        step["params"][key] = 99999   # an integer instead of expected list/string/bool
    return step

def _random_empty_string(step):
    """Set a random parameter to an empty string."""
    if step["params"]:
        key = random.choice(list(step["params"].keys()))
        step["params"][key] = ""
    return step

def _random_extra_param(step):
    """Add an unknown extra parameter."""
    step["params"]["__extra__"] = "intruder"
    return step

ERROR_OPERATIONS = [
    _random_drop_param,
    _random_wrong_type,
    _random_empty_string,
    _random_extra_param,
]

def inject_errors(step):
    """Apply 1–2 random error mutations to a copy of `step`."""
    # copy deeply
    new_step = {"command": step["command"], "params": dict(step["params"])}
    num_mutations = random.randint(1, 2)
    for _ in range(num_mutations):
        op = random.choice(ERROR_OPERATIONS)
        op(new_step)
    return new_step

# ----------------------------------------------------------------------
# Generator
# ----------------------------------------------------------------------
def generate_sequences(count):
    """Generate `count` test sequences with mixed normal and error-injected inputs."""
    if count <= 0:
        return []

    # ~20% error sequences, the rest normal
    error_count = max(1, int(count * 0.2))
    normal_count = count - error_count

    sequences = []

    # Normal sequences
    for _ in range(normal_count):
        length = random.randint(1, 5)
        seq = []
        for _ in range(length):
            cmd = random.choice(list(COMMANDS.keys()))
            param_spec = COMMANDS[cmd]["params"]
            params = {}
            for pname, pvals in param_spec.items():
                val = random.choice(pvals)
                if val is not None:
                    params[pname] = val
            seq.append({"command": cmd, "params": params})
        sequences.append(seq)

    # Error sequences: taken from normal-like sequences with injected errors
    for _ in range(error_count):
        length = random.randint(1, 5)
        seq = []
        # generate normal steps first
        for _ in range(length):
            cmd = random.choice(list(COMMANDS.keys()))
            param_spec = COMMANDS[cmd]["params"]
            params = {}
            for pname, pvals in param_spec.items():
                val = random.choice(pvals)
                if val is not None:
                    params[pname] = val
            seq.append({"command": cmd, "params": params})
        # pick a random step and inject errors
        if seq:
            idx = random.randrange(len(seq))
            seq[idx] = inject_errors(seq[idx])
        sequences.append(seq)

    # Shuffle to mix normal and error sequences (still deterministic via seed)
    random.shuffle(sequences)
    return sequences

# ----------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------
def run_sequences(sequences, dry_run=False):
    """Execute sequences against TwinEngine and yield rows for CSV."""
    if not dry_run:
        from twin import TwinEngine

    rows = []
    for seq_id, sequence in enumerate(sequences, start=1):
        if dry_run:
            # just print sequence info
            print(f"--- Sequence {seq_id} (length {len(sequence)}) ---")
            for step_id, step in enumerate(sequence, start=1):
                print(f"  Step {step_id}: {step['command']} {json.dumps(step['params'])}")
            continue

        # Non-dry-run: execute
        engine = TwinEngine()
        for step_id, step in enumerate(sequence, start=1):
            cmd = step["command"]
            params = step["params"]
            try:
                resp = engine.dispatch(cmd, params)
            except Exception as exc:
                resp = {"events": [], "state": "", "error": f"exception: {exc}"}
            rows.append([
                seq_id,
                step_id,
                cmd,
                json.dumps(params),
                json.dumps(resp.get("events", [])),
                resp.get("state", ""),
                resp.get("error", ""),
            ])
    return rows

# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Fuzz testcase generator for digital twin")
    parser.add_argument("--count", type=int, default=100, help="Number of test sequences")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--output", type=str, default="fuzz_testcases.csv", help="CSV output path")
    parser.add_argument("--dry-run", action="store_true", help="Print sequences without executing twin")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    sequences = generate_sequences(args.count)

    if args.dry_run:
        # run_sequences with dry_run=True just prints
        run_sequences(sequences, dry_run=True)
    else:
        rows = run_sequences(sequences, dry_run=False)
        with open(args.output, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["sequence_id", "step", "command", "params_json",
                             "expected_events_json", "expected_state", "expected_error"])
            writer.writerows(rows)
        print(f"Wrote {len(rows)} testcase rows to {args.output}")

if __name__ == "__main__":
    main()