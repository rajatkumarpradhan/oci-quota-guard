"""Quota-rule eval gate: fixture cases must classify exactly as expected."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from oci_quota_guard import audit

def main() -> int:
    fixture = json.loads((Path(__file__).resolve().parents[1] / "examples" / "eval-fixture.json").read_text())
    failures = 0
    for i, case in enumerate(fixture["cases"], 1):
        report = audit({"limits": case["limits"]}, "eval-fixture")
        got = sorted({f["rule"] for f in report["findings"]})
        want = sorted(case["expect_rules"])
        problems = [] if got == want else [f"rules: expected {want}, got {got}"]
        for name, sev in (case.get("expect_severity") or {}).items():
            match = [f for f in report["findings"] if f"#{name}" not in f["citation"] and f"/{name}" in f["message"]]
            if not match or match[0]["severity"] != sev:
                problems.append(f"severity for {name}: expected {sev}, got {[m['severity'] for m in match]}")
        failures += bool(problems)
        print(f"{'PASS' if not problems else 'FAIL'} case {i}: {case['name']}")
        for p in problems:
            print(f"      {p}")
    print(f"eval gate: {len(fixture['cases']) - failures}/{len(fixture['cases'])} cases classified as expected")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
