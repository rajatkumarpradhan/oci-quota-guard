"""Deterministic service-quota audit rules over a limits/usage export.

Every finding cites its export row and shows the numbers the rule computed.
Thresholds are this project's review convention (stated in the README), not
an Oracle rule.
"""
from __future__ import annotations

from dataclasses import dataclass

USAGE_LADDER = [  # (rule, min ratio used/limit, severity)
    ("QUOTA002", 1.0, "critical"),    # at or over the limit
    ("QUOTA001", 0.9, "critical"),
    ("QUOTA001", 0.75, "high"),
    ("QUOTA001", 0.5, "medium"),
]


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    citation: str
    message: str


def audit_limit(row: dict, index: int, source: str) -> list[Finding]:
    citation = f"{source}#limit-{index}"
    name = f"{row.get('service', '?')}/{row.get('name', '?')}"
    scope = f"{row.get('region', '?')}" + (f"/{row['scope']}" if row.get("scope") else "")
    try:
        limit, used = float(row["limit"]), float(row["used"])
    except (KeyError, TypeError, ValueError):
        return [Finding("QUOTA003", "high", citation,
                        f"{name} ({scope}): unusable record - limit/used missing or non-numeric; verify it manually")]
    if limit < 0 or used < 0:
        return [Finding("QUOTA003", "high", citation,
                        f"{name} ({scope}): negative limit/used in export; verify it manually")]
    findings = []
    if limit == 0:
        if used > 0:
            findings.append(Finding("QUOTA003", "high", citation,
                                    f"{name} ({scope}): limit is 0 but used is {used:g} - inconsistent export or a hard-gated resource; verify manually"))
        return findings
    ratio = used / limit
    for rule, min_ratio, severity in USAGE_LADDER:
        if ratio >= min_ratio:
            headroom = limit - used
            findings.append(Finding(rule, severity, citation,
                                    f"{name} ({scope}): {used:g}/{limit:g} used ({ratio * 100:.0f}%), headroom {headroom:g}"))
            break
    return findings


def regional_drift(rows: list[dict], source: str) -> list[Finding]:
    """Same service+name with different limits across regions - review note."""
    by_key: dict[tuple, dict[str, float]] = {}
    for row in rows:
        try:
            key = (str(row["service"]), str(row["name"]))
            by_key.setdefault(key, {})[str(row.get("region", "?"))] = float(row["limit"])
        except (KeyError, TypeError, ValueError):
            continue
    findings = []
    for (service, name), regions in sorted(by_key.items()):
        if len(regions) > 1 and len(set(regions.values())) > 1:
            detail = ", ".join(f"{r}={v:g}" for r, v in sorted(regions.items()))
            findings.append(Finding("QUOTA004", "low", f"{source}#{service}/{name}",
                                    f"{service}/{name}: limit differs by region ({detail}) - confirm increases were requested where intended"))
    return findings
