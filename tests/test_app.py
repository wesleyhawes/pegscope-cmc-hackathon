"""Transport, persistence, live-clock and local HTTP integration tests for PegScope."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from io import BytesIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen

import cmc_client as cmc
import pegscope as app


# Local marker intentionally unrelated to a real CMC key.
MARKER = "offline-test-only-header-marker"
BASE_TIME = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)


def stamp(seconds):
    return (BASE_TIME + timedelta(seconds=seconds)).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def save(db, source, at, price, observed=None):
    updated = stamp(at if observed is None else observed)
    frame = {"at": stamp(at), "quotes": {"3408": {"price": price, "updated": updated}}}
    app.add_capture(db, frame, {"source": source, "fetched_at": frame["at"], "endpoint": cmc.QUOTES})


def one_asset(snapshot, symbol="USDC"):
    return next(asset for asset in snapshot["assets"] if asset["symbol"] == symbol)


def example():
    return {
        "status": {"timestamp": stamp(0), "error_code": 0, "credit_count": 1, "other": "omit_me"},
        "data": [{"id": 3408, "symbol": "USDC", "other": "omit_me",
                  "quote": [{"id": 2781, "symbol": "USD", "price": 0.9965,
                             "last_updated": stamp(0), "volume_24h": 123.4, "other": "omit_me"}]}]
    }


@contextmanager
def mock_reply(payload, status=200):
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    with patch.object(cmc, "build_opener") as builder:
        response = BytesIO(raw)
        response.status = status
        builder.return_value.open.return_value = response
        yield builder.return_value.open


class CmcClientTests(unittest.TestCase):
    def test_authenticated_source_and_receipt(self):
        with patch.dict(os.environ, {"CMC_API_KEY": MARKER}), mock_reply(example()) as opener:
            frame, evidence, receipt = cmc.quote_sample(lambda: stamp(10))
        call = opener.call_args
        req = call.args[0]
        parsed = urlsplit(req.full_url)
        self.assertEqual((parsed.scheme, parsed.netloc, parsed.path),
                         ("https", "pro-api.coinmarketcap.com", cmc.QUOTES))
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(dict((k.lower(), v) for k, v in req.header_items())["x-cmc_pro_api_key"], MARKER)
        self.assertEqual(parse_qs(parsed.query), {"id": ["825,3408,4943"], "convert": ["USD"]})
        self.assertNotIn(MARKER, req.full_url)
        self.assertGreater(call.kwargs["timeout"], 0)
        self.assertNotIn(MARKER, json.dumps([frame, evidence, receipt]))
        self.assertNotIn("omit_me", json.dumps(receipt))
        self.assertEqual(receipt["http_status"], 200)
        self.assertEqual(receipt["response_excerpt"]["status"]["credit_count"], 1)
        self.assertEqual(receipt["response_excerpt"]["data"][0]["quote"][0]["price"], 0.9965)
        self.assertEqual(frame["quotes"]["3408"]["volume_24h"], 123.4)
        self.assertEqual(set(frame["quotes"]), {"3408"})
        self.assertEqual(evidence["endpoint"], cmc.QUOTES)

    def test_keyless_stays_keyless_even_when_key_is_set(self):
        with patch.dict(os.environ, {"CMC_API_KEY": MARKER}), mock_reply(example()) as opener:
            _, evidence, receipt = cmc.quote_sample(lambda: stamp(10), public=True)
        req = opener.call_args.args[0]
        self.assertEqual(urlsplit(req.full_url).path, cmc.PUBLIC_QUOTES)
        self.assertNotIn("x-cmc_pro_api_key", {k.lower() for k, _ in req.header_items()})
        self.assertNotIn(MARKER, repr(req.header_items()) + req.full_url + json.dumps(receipt))
        self.assertIn("keyless", evidence["source"].lower())
        self.assertEqual(cmc.NoRedirects().redirect_request(req, None, 302, "redirect", {}, "https://example.com"), None)

    def test_invalid_path_or_missing_key_does_not_send_request(self):
        with patch.dict(os.environ, {"CMC_API_KEY": ""}), patch.object(cmc, "build_opener") as opener:
            for path in [cmc.QUOTES, "/not-an-endpoint", "https://example.com"]:
                with self.subTest(path=path), self.assertRaises(cmc.ApiError):
                    cmc.fetch_cmc(path, {})
            opener.assert_not_called()

    def test_provider_failures_are_safe_and_429_has_retry_delay(self):
        for status_code in [401, 403, 429, 500]:
            with self.subTest(status_code=status_code), patch.object(cmc, "build_opener") as opener:
                opener.return_value.open.side_effect = HTTPError("https://example.com", status_code,
                    MARKER, {"Retry-After": "45"}, BytesIO(MARKER.encode()))
                with self.assertRaises(cmc.ApiError) as caught:
                    cmc.fetch_cmc(cmc.PUBLIC_QUOTES, cmc.PARAMS)
                answer = str(caught.exception)
                self.assertIn(str(status_code), answer)
                self.assertNotIn(MARKER, answer)
                if status_code == 429:
                    self.assertIn("45", answer)
        with patch.object(cmc, "build_opener") as opener:
            opener.return_value.open.side_effect = URLError(MARKER)
            with self.assertRaises(cmc.ApiError) as caught:
                cmc.fetch_cmc(cmc.PUBLIC_QUOTES, cmc.PARAMS)
            self.assertNotIn(MARKER, str(caught.exception))
        for payload in [b"not json", {"status": []}, b"x" * (cmc.MAX_RESPONSE + 1),
                        {"status": {"error_code": MARKER}}]:
            with mock_reply(payload), self.assertRaises(cmc.ApiError) as caught:
                cmc.fetch_cmc(cmc.PUBLIC_QUOTES, cmc.PARAMS)
            self.assertNotIn(MARKER, str(caught.exception))
        with mock_reply(example(), status=206), self.assertRaises(cmc.ApiError):
            cmc.fetch_cmc(cmc.PUBLIC_QUOTES, cmc.PARAMS)

    def test_invalid_identity_currency_and_null_price(self):
        for mutation in [lambda r: r.update(symbol="USDT"), lambda r: r.update(id=999999)]:
            payload = example()
            mutation(payload["data"][0])
            with self.assertRaises(cmc.ApiError):
                cmc.parse_quotes(payload)
        payload = example()
        payload["data"] *= 2
        with self.assertRaises(cmc.ApiError):
            cmc.parse_quotes(payload)
        with self.assertRaises(cmc.ApiError):
            cmc.parse_quotes({"data": {}})
        payload = example()
        payload["data"][0]["quote"][0]["symbol"] = "USDT"
        self.assertEqual(cmc.parse_quotes(payload), ({}, []))
        payload = example()
        payload["data"][0]["quote"][0]["price"] = None
        quotes, preview = cmc.parse_quotes(payload)
        self.assertIsNone(quotes["3408"]["price"])
        self.assertEqual(preview, [])

    def test_badly_typed_ids_and_out_of_range_numbers(self):
        payload = example()
        payload["data"].append({"id": []})
        quotes, _ = cmc.parse_quotes(payload)
        self.assertEqual(set(quotes), {"3408"})
        payload["data"][0]["quote"][0]["price"] = 10 ** 400
        parsed, proof = cmc.parse_quotes(payload)
        self.assertIsNone(parsed["3408"]["price"])
        self.assertEqual(proof, [])


class CaptureAndReportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.db = Path(self.temporary.name) / "subdir" / "captures.sqlite3"

    def test_history_uses_single_source_and_deduplicates(self):
        save(self.db, "keyless", 0, 0.993)
        save(self.db, "authenticated", 60, 0.994)
        save(self.db, "authenticated", 60, 0.994)
        report = app.report(self.db, "live", current=lambda: stamp(90))
        self.assertEqual((report["step"], report["source"]), (1, "authenticated"))
        self.assertEqual((one_asset(report)["state"], one_asset(report)["run"]), ("Watch", 1))
        self.assertEqual(one_asset(report, "USDT")["state"], "Unknown")
        save(self.db, "authenticated", 120, 0.993)
        report = app.report(self.db, "live", current=lambda: stamp(121))
        self.assertEqual(report["evidence"]["fetched_at"], stamp(120))
        self.assertEqual((one_asset(report)["state"], one_asset(report)["run"]), ("Incident", 2))
        self.assertEqual(len(app.live_history(self.db)[0]), 2)

    def test_frozen_and_live_clocks(self):
        for mode in app.MODES:
            first = app.report(self.db, mode, current=lambda: stamp(0))
            later = app.report(self.db, mode, current=lambda: stamp(99999))
            self.assertEqual(first, later)
            self.assertIsNone(first["evidence"])
        with self.assertRaises(LookupError):
            app.report(self.db, "live")
        save(self.db, "example", 0, 1.0)
        for elapsed, state in [(0, "Normal"), (180, "Normal"), (181, "Unknown")]:
            self.assertEqual(one_asset(app.report(self.db, "live", current=lambda: stamp(elapsed)))["state"], state)
        for mode, step in [("unlisted", None), ("live", 1), ("quiet", 0), ("drift", 123456)]:
            with self.subTest(mode=mode, step=step), self.assertRaises(ValueError):
                app.report(self.db, mode, step)

    def test_future_quote_is_not_replayed_as_a_new_observation_on_refresh(self):
        save(self.db, "future-feed", 0, 1.0, observed=60)
        first = app.report(self.db, "live", current=lambda: stamp(65))
        again = app.report(self.db, "live", current=lambda: stamp(66))
        for report in (first, again):
            asset = one_asset(report)
            self.assertEqual(asset["state"], "Unknown")
            self.assertEqual(asset["series"], [{"at": stamp(0), "bps": None}])
            self.assertEqual(report["as_of"], stamp(0).replace(".000Z", "Z"))
        self.assertEqual(first["evaluated_at"], stamp(65).replace(".000Z", "Z"))
        self.assertEqual(again["evaluated_at"], stamp(66).replace(".000Z", "Z"))
        save(self.db, "future-feed", 70, 1.0)
        restored = app.report(self.db, "live", current=lambda: stamp(71))
        self.assertEqual(one_asset(restored)["state"], "Normal")
        self.assertEqual(len(one_asset(restored)["series"]), 2)

    def test_live_expiry_uses_inclusive_boundary_and_keeps_fractional_time(self):
        save(self.db, "boundary", 0, 1.0)
        valid = app.report(self.db, "live", current=lambda: stamp(180))
        expired = app.report(self.db, "live", current=lambda: stamp(180.001))
        self.assertEqual(one_asset(valid)["state"], "Normal")
        self.assertEqual(one_asset(expired)["state"], "Unknown")
        self.assertEqual(expired["evaluated_at"], "2026-11-18T12:03:00.001000Z")
        self.assertEqual(len(one_asset(expired)["series"]), 1)

    def test_http_report_errors_and_success_on_loopback(self):
        class QuietHandler(app.handler_for(self.db)):
            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler) as server:
            thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
            thread.start()
            root = f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(root + "/api/report?mode=drift", timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn("json", response.headers["Content-Type"])
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                    self.assertEqual(one_asset(json.load(response))["state"], "Incident")
                for path, code in [("/api/report?mode=drift&step=bogus", 400),
                                   ("/api/report?mode=live", 409), ("/unknown", 404)]:
                    with self.subTest(path=path), self.assertRaises(HTTPError) as caught:
                        urlopen(root + path, timeout=5)
                    with caught.exception as err:
                        self.assertEqual(err.code, code)
                        self.assertIn("error", json.load(err))
            finally:
                server.shutdown()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
