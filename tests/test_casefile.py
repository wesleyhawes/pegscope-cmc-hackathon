import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import casefile


def candle(day, low=0.99, close=1.0):
    return [1.0, 1.01, low, close, 10000, 5000000,
            day + "T00:00:00Z", day + "T08:00:00Z",
            day + "T16:05:00Z", day + "T23:59:59.999Z"]


class CasefileTests(unittest.TestCase):
    def test_live_command_uses_usdc_usd_daily_window_and_low_time(self):
        data = {"status": {"error_code": "0"}, "data": [candle("2023-03-10", 0.99, 0.999)]}
        out = io.StringIO()
        with patch("casefile.fetch_cmc", return_value=data) as fetch, redirect_stdout(out):
            self.assertEqual(casefile.main([]), 0)
        fetch.assert_called_once_with("/v5/cryptocurrency/ohlcv/historical", {
            "id": "3408", "convert_id": "2781", "interval": "1d",
            "time_start": "2023-03-09", "time_end": "2023-03-14",
        })
        for text in ("1/6 daily candles", "-100.00", "-10.00", "90.00 bp",
                     "2023-03-10T16:05:00Z", "missing candle"):
            self.assertIn(text, out.getvalue())
        self.assertNotIn("08:00:00", out.getvalue())

    def test_missing_low_time_and_close_do_not_become_measured_values(self):
        row = candle("2023-03-10", 0.99, None)
        row[8] = None
        result = casefile.report({"data": [row]}, casefile.START, casefile.END)
        self.assertIn("n/a", result)
        self.assertIn("unavailable", result)
        self.assertNotIn("That day closed", result)

    def test_no_data_duplicate_wrong_window_and_bad_prices_fail_honestly(self):
        one = candle("2023-03-10")
        for dataset in ([], [one, one], [candle("2024-01-01")], [[1, 2]],
                        [candle("2023-03-10", float("nan"))], [candle("2023-03-10", None)],
                        [candle("2023-03-10", 1.01, 1.0)]):
            with self.subTest(dataset=dataset), self.assertRaises(ValueError):
                casefile.report({"data": dataset}, casefile.START, casefile.END)

    def test_demo_is_fictional_and_has_no_upstream_dependency(self):
        out = io.StringIO()
        with patch("casefile.fetch_cmc") as fetch, redirect_stdout(out):
            self.assertEqual(casefile.main(["--demo"]), 0)
        fetch.assert_not_called()
        self.assertIn("SYNTHETIC DRILL", out.getvalue())
        self.assertNotIn("2023", out.getvalue())
        self.assertNotIn("USDC", out.getvalue())

    def test_missing_live_data_is_never_replaced_by_a_drill(self):
        err, out = io.StringIO(), io.StringIO()
        with patch("casefile.fetch_cmc", return_value={"data": []}), redirect_stderr(err), redirect_stdout(out):
            self.assertEqual(casefile.main([]), 1)
        self.assertIn("No usable daily lows", err.getvalue())
        self.assertFalse(out.getvalue())


if __name__ == "__main__":
    unittest.main()
