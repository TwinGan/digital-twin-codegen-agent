from dataclasses import dataclass

from .coverage import CoverageResult, CoverageGap


@dataclass
class ReviewReport:
    passed: bool
    command_cov_pct: float
    event_cov_pct: float
    error_cov_pct: float
    gaps: list[CoverageGap]
    formatted: str


def generate_report(coverage: CoverageResult, llm_review: str = "") -> ReviewReport:
    total_gaps = coverage.gaps
    error_gaps = [g for g in total_gaps if g.severity == "error"]
    passed = len(error_gaps) == 0

    lines: list[str] = []
    lines.append("# Coverage Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Verdict**: {'PASS' if passed else 'FAIL'}")
    lines.append(f"- **Command Coverage**: {coverage.command_coverage:.0%} "
                 f"({len(set(coverage.spec_commands) & set(coverage.code_commands))}/{len(coverage.spec_commands)})")
    lines.append(f"- **Event Coverage**: {coverage.event_coverage:.0%} "
                 f"({len(set(coverage.spec_events) & set(coverage.code_events))}/{len(coverage.spec_events)})")
    lines.append(f"- **Error Code Coverage**: {coverage.error_coverage:.0%} "
                 f"({len(set(coverage.spec_errors) & set(coverage.code_errors))}/{len(coverage.spec_errors)})")
    lines.append(f"- **Gaps Found**: {len(error_gaps)} errors, "
                 f"{len([g for g in total_gaps if g.severity == 'warning'])} warnings")
    lines.append("")

    lines.append("## Command Coverage")
    lines.append("")
    lines.append("| Command | In Spec | In Code | Covered |")
    lines.append("|---------|---------|---------|---------|")
    all_commands = sorted(set(coverage.spec_commands) | set(coverage.code_commands))
    for cmd in all_commands:
        in_spec = "Yes" if cmd in coverage.spec_commands else "No"
        in_code = "Yes" if cmd in coverage.code_commands else "No"
        covered = "PASS" if cmd in coverage.spec_commands and cmd in coverage.code_commands else (
            "EXTRA" if cmd not in coverage.spec_commands else "MISSING"
        )
        lines.append(f"| {cmd} | {in_spec} | {in_code} | {covered} |")
    lines.append("")

    lines.append("## Event Coverage")
    lines.append("")
    lines.append("| Event | In Spec | In Code | Covered |")
    lines.append("|-------|---------|---------|---------|")
    all_events = sorted(set(coverage.spec_events) | set(coverage.code_events))
    for ev in all_events:
        in_spec = "Yes" if ev in coverage.spec_events else "No"
        in_code = "Yes" if ev in coverage.code_events else "No"
        covered = "PASS" if ev in coverage.spec_events and ev in coverage.code_events else "MISSING"
        lines.append(f"| {ev} | {in_spec} | {in_code} | {covered} |")
    lines.append("")

    if coverage.spec_errors or coverage.code_errors:
        lines.append("## Error Code Coverage")
        lines.append("")
        lines.append("| Error Code | In Spec | In Code | Covered |")
        lines.append("|------------|---------|---------|---------|")
        all_errors = sorted(set(coverage.spec_errors) | set(coverage.code_errors))
        for err in all_errors:
            if not err:
                continue
            in_spec = "Yes" if err in coverage.spec_errors else "No"
            in_code = "Yes" if err in coverage.code_errors else "No"
            covered = "PASS" if err in coverage.spec_errors and err in coverage.code_errors else "MISSING"
            lines.append(f"| {err} | {in_spec} | {in_code} | {covered} |")
        lines.append("")

    lines.append("## Gaps")
    lines.append("")
    if total_gaps:
        for gap in total_gaps:
            prefix = "[ERROR]" if gap.severity == "error" else "[WARN]"
            lines.append(f"- {prefix} [{gap.category}] {gap.item}: {gap.detail}")
    else:
        lines.append("No gaps found. All spec items covered in code.")
    lines.append("")

    lines.append("## Invariants from Spec")
    lines.append("")
    for inv in coverage.spec_invariants:
        lines.append(f"- {inv}")
    lines.append("")

    if llm_review:
        lines.append("---")
        lines.append("")
        lines.append("## LLM Review")
        lines.append("")
        lines.append(llm_review)

    formatted = "\n".join(lines)

    return ReviewReport(
        passed=passed,
        command_cov_pct=coverage.command_coverage,
        event_cov_pct=coverage.event_coverage,
        error_cov_pct=coverage.error_coverage,
        gaps=total_gaps,
        formatted=formatted,
    )
