"""Load a limits export, run all rules, build the report."""
from __future__ import annotations

import json
from pathlib import Path

from .rules import Finding, audit_limit, regional_drift

SEV_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}


def load_export(path) -> dict:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        assert isinstance(raw.get("limits"), list), "missing 'limits' list"
        return raw
    except (OSError, json.JSONDecodeError, AssertionError) as e:
        raise ValueError(f"cannot load limits export {path}: {e}") from e


def audit(export: dict, source: str = "export") -> dict:
    rows = export["limits"]
    findings: list[Finding] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append(Finding("QUOTA003", "high", f"{source}#limit-{i}",
                                    "unusable record (not an object); verify it manually"))
            continue
        findings += audit_limit(row, i, source)
    findings += regional_drift(rows, source)
    counts = {s: sum(1 for f in findings if f.severity == s) for s in SEV_RANK}
    return {
        "source": source,
        "limits_checked": len(rows),
        "findings": [f.__dict__ for f in sorted(
            findings, key=lambda f: (-SEV_RANK[f.severity], f.citation))],
        "summary": counts | {"total": len(findings)},
        "limits": ("Static export audit: no live Limits API call, no tenancy-wide "
                   "guarantee (only exported rows are checked), usage is a point-in-time "
                   "snapshot, and some limits are soft caps an increase request can raise."),
    }


def worst_severity(report: dict) -> str | None:
    for s in ("critical", "high", "medium", "low"):
        if report["summary"].get(s):
            return s
    return None
