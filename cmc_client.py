"""Read-only CoinMarketCap transport and a narrowly projected quote receipt."""

import json
import math
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from peg_engine import ASSETS

BASE = "https://pro-api.coinmarketcap.com"
QUOTES = "/v3/cryptocurrency/quotes/latest"
HISTORY = "/v5/cryptocurrency/ohlcv/historical"
PUBLIC_QUOTES = "/public-api" + QUOTES
IDS = ASSETS
PARAMS = {"id": ",".join(map(str, IDS)), "convert": "USD"}
MAX_RESPONSE = 2_000_000


class ApiError(Exception):
    """An error safe to display in a recording."""


class NoRedirects(HTTPRedirectHandler):
    # A provider redirect must never forward authentication to a new host.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_cmc(path, params):
    if path not in (QUOTES, HISTORY, PUBLIC_QUOTES):
        raise ApiError("Unknown CMC endpoint.")
    headers = {"Accept": "application/json", "User-Agent": "PegScope/1.0"}
    if path != PUBLIC_QUOTES:
        key = os.environ.get("CMC_API_KEY", "").strip()
        if not key:
            raise ApiError("Set CMC_API_KEY in this terminal to use the authenticated endpoint.")
        headers["X-CMC_PRO_API_KEY"] = key
    request = Request(BASE + path + "?" + urlencode(params), headers=headers)
    try:
        with build_opener(NoRedirects()).open(request, timeout=15) as response:
            if response.status != 200:
                raise ApiError(f"Unexpected HTTP status {response.status}.")
            raw = response.read(MAX_RESPONSE + 1)
    except HTTPError as error:
        messages = {401: "Check the local key.", 403: "Check the plan entitlement.",
                    429: "Rate or credit limit reached. Pause before retrying."}
        hint = messages.get(error.code, "Check provider status and request parameters.")
        after = error.headers.get("Retry-After", "")
        if error.code == 429 and after.isdecimal():
            hint += f" Provider retry delay: {after[:8]} seconds."
        raise ApiError(f"CMC HTTP {error.code}. {hint}") from None
    except (URLError, TimeoutError, OSError):
        raise ApiError("CMC connection failed or timed out. Retry after checking connectivity.") from None
    if len(raw) > MAX_RESPONSE:
        raise ApiError("Provider response exceeded the expected size.")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        raise ApiError("Provider returned invalid JSON.") from None
    if not isinstance(data, dict) or not isinstance(data.get("status"), dict):
        raise ApiError("Provider response is missing the status object.")
    code = str(data["status"].get("error_code"))
    if code != "0":
        safe_code = code if code.isdecimal() and len(code) <= 8 else "unknown"
        raise ApiError(f"CMC reported error code {safe_code}.")
    return data


def _number(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    if value < 0 or value > 1e300 or not math.isfinite(value) or (positive and value == 0):
        return None
    return value


def parse_quotes(payload):
    """Missing assets/fields become gaps. Schema changes must never imply an all-clear."""
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ApiError("Expected a v3 data array. Check the quotes contract.")
    quotes = {}
    excerpt = []
    seen = set()
    for asset in rows:
        if not isinstance(asset, dict) or type(asset.get("id")) is not int or asset["id"] not in IDS:
            continue
        cid = asset["id"]
        if cid in seen or asset.get("symbol") != IDS[cid]:
            raise ApiError("Ambiguous or mismatched asset ID in quote response.")
        seen.add(cid)
        pairings = asset.get("quote")
        if not isinstance(pairings, list):
            continue
        matches = [q for q in pairings if isinstance(q, dict) and
                   q.get("symbol") == "USD" and q.get("id") in (None, 2781)]
        if len(matches) != 1:
            continue
        usd = matches[0]
        updated = usd.get("last_updated")
        price = _number(usd.get("price"), positive=True)
        quotes[str(cid)] = {"price": price, "updated": updated if isinstance(updated, str) else None,
                            "volume_24h": _number(usd.get("volume_24h"))}
        if price is not None:
            fields = {k: usd[k] for k in ("symbol", "price", "last_updated") if k in usd}
            excerpt.append({"id": cid, "symbol": asset["symbol"], "quote": [fields]})
    if rows and not seen:
        raise ApiError("CMC returned none of the requested IDs. Check the provider response.")
    return quotes, excerpt


def quote_sample(at, public=False):
    path = PUBLIC_QUOTES if public else QUOTES
    payload = fetch_cmc(path, PARAMS)
    quotes, excerpt = parse_quotes(payload)
    # Stamp the observation after network I/O to avoid comparing to an earlier local clock.
    fetched = at()
    status = {key: payload["status"][key] for key in
              ("timestamp", "error_code", "credit_count") if key in payload["status"]}
    source = "CoinMarketCap public API (keyless)" if public else "CoinMarketCap authenticated API"
    evidence = {"endpoint": path, "source": source, "fetched_at": fetched,
                "credit_count": status.get("credit_count"), "provider_at": status.get("timestamp")}
    receipt = {"source": source, "request": {"method": "GET", "endpoint": BASE + path,
               "params": PARAMS}, "http_status": 200, "fetched_at": fetched,
               "response_excerpt": {"status": status, "data": excerpt[:1]}}
    return {"at": fetched, "quotes": quotes}, evidence, receipt
