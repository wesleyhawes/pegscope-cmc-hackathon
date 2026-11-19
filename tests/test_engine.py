"""Regression checks for evidence, timing and signed peg thresholds."""
import copy
import unittest
from datetime import datetime, timedelta, timezone

from peg_engine import ASSETS, FRESH_SECONDS, analyze, scenario


ORIGIN = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)


def utc(sec):
    return (ORIGIN + timedelta(seconds=sec)).isoformat().replace("+00:00", "Z")


def frame(t, price, updated=None):
    return {"at": utc(t), "quotes": {"3408": {"price": price, "updated": utc(t if updated is None else updated)}}}


def usdc(frames):
    return next(row for row in analyze(frames)["assets"] if row["symbol"] == "USDC")


class PegEngineTests(unittest.TestCase):
    def test_scenario_results_and_comparators(self):
        expected = {"drift": ("Incident", -70), "recovery": ("Normal", -2),
                    "stale": ("Unknown", None), "quiet": ("Normal", 1)}
        for name, (state, bps) in expected.items():
            with self.subTest(name=name):
                frames = scenario(name)
                summary = analyze(frames)
                self.assertEqual(summary["as_of"], frames[-1]["at"])
                asset = usdc(frames)
                self.assertEqual((asset["state"], asset["bps"]), (state, bps))
                self.assertEqual(len(asset["series"]), len(frames))
                self.assertTrue(all(row["state"] == "Normal" for row in summary["assets"] if row["id"] != 3408))
        self.assertEqual([event["state"] for event in usdc(scenario("recovery"))["events"]],
                         ["Normal", "Watch", "Incident", "Normal"])
        with self.assertRaises(ValueError):
            scenario("made_up")

    def test_no_partial_normal_due_to_empty_or_missing_source(self):
        summary = analyze([])
        self.assertIsNone(summary["as_of"])
        self.assertEqual(set(ASSETS), {asset["id"] for asset in summary["assets"]})
        self.assertTrue(all(a["state"] == "Unknown" and a["series"] == [] for a in summary["assets"]))
        self.assertTrue(all(a["state"] == "Unknown" for a in analyze([{"at": utc(0)}])["assets"]))

    def test_signed_thresholds_and_same_side_confirmation(self):
        for price, bps in [(0.995, -50), (1.005, 50)]:
            with self.subTest(price=price):
                rows = [frame(0, price), frame(60, price)]
                self.assertEqual(usdc(rows[:1])["state"], "Watch")
                result = usdc(rows)
                self.assertEqual((result["state"], result["run"], result["bps"]), ("Incident", 2, bps))
        rows = [frame(0, 0.995), frame(60, 1.005)]
        self.assertEqual((usdc(rows)["state"], usdc(rows)["run"]), ("Watch", 1))
        self.assertEqual(usdc([frame(0, 0.9975)])["state"], "Watch")
        self.assertEqual(usdc([frame(0, 1.00249999)])["state"], "Normal")

    def test_duplicate_never_confirms_or_recovers(self):
        rows = [frame(0, 0.994), frame(60, 0.994, updated=0)]
        self.assertEqual((usdc(rows)["state"], usdc(rows)["run"]), ("Watch", 1))
        rows.extend([frame(120, 0.994), frame(180, 0.999), frame(240, 0.999, updated=180)])
        self.assertEqual(usdc(rows)["state"], "Incident")
        self.assertEqual(usdc(rows + [frame(300, 1.001)])["state"], "Normal")
        self.assertEqual(usdc([frame(0, 1), frame(60, 1.002, updated=0)])["state"], "Unknown")

    def test_hysteresis_and_reset_both_runs(self):
        rows = [frame(0, 0.99), frame(60, 0.99), frame(120, 1.0008), frame(180, 1.0015), frame(240, 1.0001)]
        self.assertEqual(usdc(rows)["state"], "Incident")
        self.assertEqual(usdc(rows + [frame(300, 0.9999)])["state"], "Normal")
        self.assertEqual(usdc([frame(0, 0.99), frame(60, None), frame(120, 0.99)])["state"], "Watch")

    def test_invalid_quotes_gap_without_fabricating_zero_or_recovery(self):
        for price in (0, -1, True, None, float("nan"), float("inf"), "1"):
            with self.subTest(price=price):
                row = usdc([frame(0, price)])
                self.assertEqual(row["state"], "Unknown")
                self.assertIsNone(row["price"])
                self.assertIsNone(row["series"][0]["bps"])
        self.assertEqual(usdc([frame(180, 1, updated=0)])["state"], "Normal")
        old = usdc([frame(FRESH_SECONDS + 1, 1, updated=0)])
        self.assertEqual(old["state"], "Unknown")
        self.assertEqual(old["updated"], utc(0))
        self.assertIsNone(old["last_valid_update"])
        self.assertEqual(usdc([frame(0, 1, updated=1)])["state"], "Unknown")
        self.assertEqual(usdc([frame(0, 1), frame(60, 1, updated=-1)])["state"], "Unknown")
        invalid = frame(0, 1)
        invalid["quotes"]["3408"]["updated"] = "invalid date"
        self.assertEqual(usdc([invalid])["state"], "Unknown")

    def test_restart_after_stale_and_silent_gaps(self):
        rows = [frame(0, 0.99), frame(240, 0.99, updated=0), frame(300, 0.99)]
        self.assertEqual(usdc(rows[:2])["state"], "Unknown")
        self.assertEqual(usdc(rows)["run"], 1)
        self.assertEqual(usdc([frame(0, 0.99), frame(181, 0.99, updated=120)])["run"], 1)
        self.assertEqual(usdc([frame(0, 0.99), frame(180, 0.99)])["run"], 2)
        rows = [frame(0, 0.99), frame(60, 0.99), frame(120, None), frame(180, 1)]
        self.assertEqual(usdc(rows)["state"], "Incident")
        self.assertEqual(usdc(rows + [frame(240, 1)])["state"], "Normal")

    def test_reproducible_without_mutating_frames(self):
        frames = scenario("drift")
        before = copy.deepcopy(frames)
        self.assertEqual(analyze(frames), analyze(scenario("drift")))
        self.assertEqual(frames, before)
        with self.assertRaises(ValueError):
            analyze([frame(60, 1), frame(0, 1)])


if __name__ == "__main__":
    unittest.main()
