"""Quota ladder, degenerate rows, regional drift and report shape."""
import unittest
from pathlib import Path

from oci_quota_guard import audit, audit_limit, load_export, regional_drift, worst_severity

FIXTURES = Path(__file__).resolve().parents[1] / "examples"


def row(limit, used, **kw):
    base = {"service": "compute", "name": "cores", "region": "r1", "limit": limit, "used": used}
    base.update(kw)
    return base


class LadderTests(unittest.TestCase):
    def check(self, limit, used):
        return audit_limit(row(limit, used), 0, "t")

    def test_boundaries(self):
        self.assertEqual(self.check(10, 10)[0].rule, "QUOTA002")
        self.assertEqual(self.check(10, 12)[0].rule, "QUOTA002")
        self.assertEqual(self.check(10, 11)[0].severity, "critical")  # over limit
        f = self.check(100, 90)
        self.assertEqual((f[0].rule, f[0].severity), ("QUOTA001", "critical"))
        f = self.check(100, 75)
        self.assertEqual((f[0].rule, f[0].severity), ("QUOTA001", "high"))
        f = self.check(100, 50)
        self.assertEqual((f[0].rule, f[0].severity), ("QUOTA001", "medium"))
        self.assertEqual(self.check(100, 49), [])

    def test_headroom_in_message(self):
        f = self.check(100, 90)
        self.assertIn("headroom 10", f[0].message)
        self.assertIn("t#limit-0", f[0].citation)

    def test_zero_and_negative_limits(self):
        self.assertEqual(self.check(0, 2)[0].rule, "QUOTA003")
        self.assertEqual(self.check(0, 0), [])
        self.assertEqual(self.check(-5, 1)[0].rule, "QUOTA003")

    def test_unusable_record(self):
        f = audit_limit({"service": "x"}, 2, "t")
        self.assertEqual(f[0].rule, "QUOTA003")
        self.assertIn("t#limit-2", f[0].citation)


class DriftTests(unittest.TestCase):
    def test_drift_and_no_drift(self):
        rows = [row(2, 0, service="lb", name="count", region="r1"),
                row(4, 0, service="lb", name="count", region="r2")]
        f = regional_drift(rows, "t")
        self.assertEqual(len(f), 1)
        self.assertIn("r1=2", f[0].message)
        rows[1]["limit"] = 2
        self.assertEqual(regional_drift(rows, "t"), [])

    def test_single_region_never_drifts(self):
        self.assertEqual(regional_drift([row(4, 1)], "t"), [])


class ReportTests(unittest.TestCase):
    def test_example_export(self):
        report = audit(load_export(FIXTURES / "limits.json"), "limits.json")
        self.assertEqual(report["limits_checked"], 10)
        self.assertEqual(worst_severity(report), "critical")
        self.assertEqual(report["summary"]["critical"], 3)   # e5 8/8 + lb 2/2 (QUOTA002) + alarm 94% (QUOTA001)
        rules = [f["rule"] for f in report["findings"]]
        self.assertEqual(rules.count("QUOTA002"), 2)         # e5 8/8, lb 2/2
        self.assertIn("QUOTA003", rules)                     # streaming limit 0 used 2
        self.assertIn("QUOTA004", rules)                     # lb drift 2 vs 4
        self.assertEqual(rules.count("QUOTA001"), 4)         # alarm 94%, micro 75%, storage 78%, atp 50%
        self.assertTrue(all("#" in f["citation"] for f in report["findings"]))

    def test_non_dict_row_flagged_not_crashed(self):
        report = audit({"limits": ["oops"]})
        self.assertEqual(report["findings"][0]["rule"], "QUOTA003")


if __name__ == "__main__":
    unittest.main()
