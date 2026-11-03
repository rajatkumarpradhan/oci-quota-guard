# oci-quota-guard

Offline audit of an OCI **service-quota / limits export** (JSON): flags quotas that are
at their limit, short on headroom, drifting between regions, or inconsistent, before
they block a deployment.

## Why this matters

Every OCI service limit is a soft cap: compute shapes, block volumes, load balancers,
alarms, streaming partitions. When a Terraform apply or a scale-out hits the cap, the
deployment fails *after* the plan looked fine. The fix is a limit-increase request,
which takes time, so the finding is useful only if it arrives early. This tool reads a
limits export and answers, deterministically:

- which quotas are **at or over** their limit right now
- which are **short on headroom** (usage ladder: >=50% medium, >=75% high, >=90% critical)
- where the **same limit differs across regions** (drift worth confirming)
- which records are **inconsistent** (usage above a zero limit, unparseable rows) and
  need a human look rather than a silent skip

## Rules (deterministic, cited)

| Rule | Severity | Meaning |
|---|---|---|
| QUOTA002 | critical | Usage at or over the limit: the next deployment fails |
| QUOTA001 | medium/high/critical | Headroom ladder at 50% / 75% / 90% of the limit |
| QUOTA003 | high | Inconsistent record: zero limit with usage, or an unparseable row. Never crashes the audit |
| QUOTA004 | low | Same service limit differs across regions: confirm intended scope |

Every finding cites its input record (`file#limit-N`).

## Try it

```bash
pip install -e .
oci-quota-guard examples/limits.json --fail-on high   # exit 2: findings at/above high
python3 scripts/eval_gate.py                          # labeled behavior gate
python3 -m unittest discover -s tests                 # unit tests
```

`--output out.json` writes the JSON report; `--fail-on {low,medium,high,critical}` sets
the CI exit code (2 when a finding at/above that severity exists, 0 otherwise).

## Input format

```json
{"limits": [{"service": "compute", "name": "standard-e5-core-count",
             "region": "ap-mumbai-1", "limit": 8, "used": 8}]}
```

## Honest limits

- **Offline / synthetic**: reads a static export you provide. No OCI SDK, no live
  Limits API calls, no tenancy required. Usage values are point-in-time snapshots, not
  forecasts.
- The usage ladder thresholds (50/75/90) are conventions, not Oracle-documented
  defaults; adjust `USAGE_LADDER` in `rules.py` for your team.
- Regional drift is informational: identical names with different limits are often
  intentional (prod vs dev regions).
- All limits in OCI are soft; this tool cannot request an increase. That is a support
  request in the OCI Console.

Built by Rajat Kumar Pradhan as part of a daily OCI portfolio practice.
