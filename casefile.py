"""Compare daily lows with closing marks during the March 2023 USDC event."""

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from cmc_client import ApiError, fetch_cmc


PATH = "/v5/cryptocurrency/ohlcv/historical"
START = date(2023, 3, 9)
END = date(2023, 3, 14)
PARAMS = {
    "id": "3408",
    "convert_id": "2781",
    "interval": "1d",
    "time_start": START.isoformat(),
    "time_end": END.isoformat(),
}


def price_bps(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("Non-numeric candle price")
    price = Decimal(str(value))
    if not price.is_finite() or price <= 0:
        raise ValueError("Invalid candle price")
    return (price - 1) * 10_000


def utc_time(value):
    if not isinstance(value, str):
        raise ValueError("Missing or invalid candle timestamp")
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("Candle timestamp lacks a UTC offset")
    return timestamp.astimezone(timezone.utc)


def format_bps(value):
    return "n/a" if value is None else f"{value:+.2f}"


def report(payload, start, end, synthetic=False):
    """Compute an auditable daily comparison, retaining missing days and fields."""
    candles = payload.get("data")
    if not isinstance(candles, list):
        raise ValueError("Expected the CMC v5 candle array")
    observations = {}
    for row in candles:
        if not isinstance(row, list) or len(row) != 10:
            raise ValueError("Expected 10 fields in a CMC v5 candle")
        day = utc_time(row[6]).date()
        if not start <= day <= end or day in observations:
            raise ValueError("Unexpected or duplicate day in candle response")
        low, close = price_bps(row[2]), price_bps(row[3])
        low_time = utc_time(row[8]) if row[8] is not None else None
        if low_time is not None and low_time.date() != day:
            raise ValueError("Low timestamp falls outside its UTC candle day")
        if low is not None and close is not None and close < low:
            raise ValueError("Daily close is below reported low")
        observations[day] = (low, close, low_time)

    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    heading = ("SYNTHETIC DRILL | fictional dollar token | no API call"
               if synthetic else "USDC | historical case file | CoinMarketCap Pro API")
    lines = [
        heading,
        f"{start} through {end} UTC | {len(observations)}/{len(days)} daily candles",
        "Signed basis points from $1.00 (100 bp = 1%)",
        "",
        "UTC day           Low (bp)   Close (bp)   Time of low (UTC)",
    ]
    for day in days:
        if day not in observations:
            lines.append(f"{day}        missing candle")
            continue
        low, close, low_time = observations[day]
        event_time = low_time.isoformat().replace("+00:00", "Z") if low_time else "unavailable"
        lines.append(f"{day}      {format_bps(low):>9}    {format_bps(close):>9}   {event_time}")

    known_lows = [(value[0], day) for day, value in observations.items()
                  if value[0] is not None]
    if not known_lows:
        raise ValueError("No usable daily lows in the requested window")
    lowest, day = min(known_lows)
    lines.extend(["", f"Lowest observed daily mark was {format_bps(lowest)} bp on {day}."])
    close = observations[day][1]
    if close is not None:
        lines.append(f"That day closed {format_bps(close)} bp from peg, "
                     f"{close - lowest:.2f} bp above the daily low.")
    lines.append("Daily extrema show the depth of a move. Its duration requires finer observations.")
    if not synthetic:
        lines.append("Data provided by CoinMarketCap.com  https://coinmarketcap.com/")
    return "\n".join(lines)


def synthetic_payload():
    # Fictional calendar dates, separate from the historical event window.
    rows = []
    for day, low, close in [
        ("2000-01-01", 0.999, 1.0),
        ("2000-01-02", 0.965, 0.995),
        ("2000-01-03", 0.994, 1.0),
    ]:
        rows.append([1.0, 1.002, low, close, None, None, day + "T00:00:00Z",
                     day + "T02:00:00Z", day + "T06:30:00Z", day + "T23:59:59.999Z"])
    return {"data": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run a labeled, offline synthetic drill")
    args = parser.parse_args(argv)
    try:
        if args.demo:
            print(report(synthetic_payload(), date(2000, 1, 1), date(2000, 1, 3), synthetic=True))
        else:
            print(report(fetch_cmc(PATH, PARAMS), START, END))
    except (ApiError, ValueError) as error:
        print(f"Historical case file unavailable: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
