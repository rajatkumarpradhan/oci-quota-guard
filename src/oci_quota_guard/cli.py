import argparse
import json
from pathlib import Path

from .audit import audit, load_export, worst_severity

RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline OCI service-quota audit")
    parser.add_argument("export", help="JSON limits export, e.g. examples/limits.json")
    parser.add_argument("--output", help="report JSON path; default stdout")
    parser.add_argument("--fail-on", choices=list(RANK),
                        help="exit 2 when any finding meets or beats this severity")
    args = parser.parse_args(argv)
    try:
        report = audit(load_export(args.export), Path(args.export).name)
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    worst = worst_severity(report)
    if args.fail_on and worst and RANK[worst] >= RANK[args.fail_on]:
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
