"""Deterministic, read-only PegScope analytics for USD-denominated stablecoin quotes."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from math import isfinite


ASSETS = {825: "USDT", 3408: "USDC", 4943: "DAI"}
WATCH_BPS = 25
INCIDENT_BPS = 50
CLEAR_BPS = 10
FRESH_SECONDS = 180
CONFIRMATIONS = 2
SCENARIOS = ("drift", "recovery", "stale", "quiet")


def _time(value):
    if not isinstance(value, str):
        raise ValueError("Expected an ISO 8601 timestamp with timezone")
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("Expected a timestamp with timezone")
    return timestamp.astimezone(timezone.utc)


def _utc(value):
    return value.isoformat(timespec="auto").replace("+00:00", "Z")


@dataclass
class _Tracker:
    asset_id: int
    symbol: str
    state: str = "Unknown"
    reason: str = "Awaiting a fresh quote."
    price: float | None = None
    bps: float | None = None
    updated: datetime | None = None
    observed: datetime | None = None
    observed_price: float | None = None
    latched: bool = False
    side: int = 0
    run: int = 0
    clear_run: int = 0
    series: list = field(default_factory=list)
    events: list = field(default_factory=list)

    def reset_runs(self):
        self.run = self.clear_run = self.side = 0

    def unknown(self, reason):
        self.state, self.reason = "Unknown", reason
        self.price = self.bps = None
        self.reset_runs()

    def sample(self, now, quote):
        if not isinstance(quote, dict):
            self.unknown("CMC quote is missing for this observation.")
            return
        try:
            updated = _time(quote.get("updated"))
        except (ValueError, OverflowError):
            self.unknown("Source update time is missing or invalid.")
            return
        self.updated = updated
        age = (now - updated).total_seconds()
        if age < 0:
            self.unknown("Source update time is in the future.")
            return
        if age > FRESH_SECONDS:
            self.unknown(f"Source quote is {age:.0f}s old, beyond the {FRESH_SECONDS}s freshness limit.")
            return
        if self.observed is not None and updated < self.observed:
            self.unknown("Source update time moved backward.")
            return
        price = quote.get("price")
        if type(price) not in (int, float) or price <= 0 or price > 1e300:
            self.unknown("USD quote has a missing or invalid price.")
            return
        if not isfinite(price):
            self.unknown("USD quote has a missing or invalid price.")
            return
        if updated == self.observed:
            if price != self.observed_price:
                self.unknown("Source supplied different prices for one update time.")
            elif self.state == "Unknown":
                self.reason = "Waiting for a new source update after a data gap."
            return

        if self.observed is not None and (updated - self.observed).total_seconds() > FRESH_SECONDS:
            self.reset_runs()
        self.observed, self.observed_price = updated, price
        self.price = price
        # Decimal keeps inclusive threshold comparisons exact for JSON prices such as 0.995.
        deviation = (Decimal(str(price)) - 1) * 10000
        self.bps = round(float(deviation), 3)
        magnitude = abs(deviation)
        side = 1 if deviation > 0 else -1
        if magnitude >= INCIDENT_BPS:
            self.run = self.run + 1 if side == self.side else 1
            self.side = side
        else:
            self.run = self.side = 0

        if self.run >= CONFIRMATIONS:
            self.latched = True
        if self.latched:
            self.clear_run = self.clear_run + 1 if magnitude <= CLEAR_BPS else 0
            if self.clear_run >= CONFIRMATIONS:
                self.latched = False
                self.clear_run = 0
                self.state = "Normal"
                self.reason = f"Recovered on two distinct quotes within {CLEAR_BPS} bp of $1."
            else:
                self.state = "Incident"
                if self.clear_run:
                    self.reason = f"First quote inside the {CLEAR_BPS} bp recovery band. One more clears the incident."
                elif self.run >= CONFIRMATIONS:
                    self.reason = f"{self.run} distinct quotes at least {INCIDENT_BPS} bp from $1 on the same side."
                else:
                    self.reason = f"Incident stays open until two distinct quotes are within {CLEAR_BPS} bp of $1."
        elif magnitude >= WATCH_BPS:
            self.state = "Watch"
            self.reason = ("First qualifying breach. Waiting for a second distinct quote on the same side."
                           if self.run else f"Deviation reached the {WATCH_BPS} bp watch threshold.")
        else:
            self.state = "Normal"
            self.reason = f"Fresh quote is inside the {WATCH_BPS} bp watch threshold."

    def report(self):
        return {"id": self.asset_id, "symbol": self.symbol, "state": self.state,
                "reason": self.reason, "price": self.price, "bps": self.bps,
                "run": self.run, "series": self.series, "events": self.events,
                "updated": _utc(self.updated) if self.updated else None,
                "last_valid_update": _utc(self.observed) if self.observed else None}


def analyze(frames, evaluated_at=None):
    """Replay frames in observation order. Time and state depend only on the input.

    Missing or stale samples output Unknown and break consecutive evidence. A
    confirmed incident still needs two clean samples to clear across a data gap.
    Repeated provider updates never count as distinct confirmations.
    """
    trackers = [_Tracker(asset_id, symbol) for asset_id, symbol in ASSETS.items()]
    previous = None
    for frame in frames:
        now = _time(frame["at"])
        if previous is not None and now < previous:
            raise ValueError("Observation times must be in chronological order")
        gap = previous is not None and (now - previous).total_seconds() > FRESH_SECONDS
        quotes = frame.get("quotes")
        for tracker in trackers:
            if gap:
                tracker.reset_runs()
            quote = quotes.get(str(tracker.asset_id)) if isinstance(quotes, dict) else None
            old_state = tracker.state
            tracker.sample(now, quote)
            tracker.series.append({"at": frame["at"], "bps": tracker.bps})
            if tracker.state != old_state or not tracker.events:
                tracker.events.append({"at": frame["at"], "state": tracker.state,
                                       "reason": tracker.reason, "bps": tracker.bps})
        previous = now

    evaluation = _time(evaluated_at) if evaluated_at is not None else previous
    assets = []
    for tracker in trackers:
        snapshot = tracker.report()
        if evaluation is not None and tracker.observed is not None:
            age = (evaluation - tracker.observed).total_seconds()
            if age < 0:
                snapshot.update(state="Unknown", reason="Last valid source update is in the future.",
                                price=None, bps=None)
            elif age > FRESH_SECONDS:
                snapshot.update(state="Unknown",
                                reason=f"Last valid source quote is {age:.3f}s old, beyond the {FRESH_SECONDS}s freshness limit.",
                                price=None, bps=None)
        snapshot["timeline"] = _timeline(tracker.series, tracker.events)
        assets.append(snapshot)
    group = []
    for state in ("Incident", "Watch", "Unknown", "Normal"):
        symbols = [asset["symbol"] for asset in assets if asset["state"] == state]
        if symbols:
            group.append(f"{state}: {', '.join(symbols)}")
    brief = ". ".join(group) + "." if previous else "Awaiting the first observation."
    return {"as_of": _utc(previous) if previous else None,
            "evaluated_at": _utc(evaluation) if evaluation else None,
            "assets": assets, "brief": brief}


def _timeline(series, events):
    """Summarize observed evidence without turning view-time ticks into observations."""
    valid = [point for point in series if isinstance(point.get("bps"), (int, float))]
    breach = next((point for point in valid if abs(point["bps"]) >= WATCH_BPS), None)
    confirmed = next((event for event in events if event["state"] == "Incident"), None)
    recovery = next((event for event in events if event["state"] == "Normal" and
                     confirmed is not None and event["at"] > confirmed["at"]), None)
    peak = max(valid, key=lambda point: abs(point["bps"])) if valid else None
    latest = valid[-1] if valid else None
    gaps = [point["at"] for point in series if point.get("bps") is None]
    return {"first_breach_at": breach["at"] if breach else None,
            "confirmed_at": confirmed["at"] if confirmed else None,
            "peak_deviation": ({"at": peak["at"], "bps": peak["bps"]} if peak else None),
            "most_recent_evidence": ({"at": latest["at"], "bps": latest["bps"]} if latest else None),
            "latest_state_change": events[-1] if events else None,
            "recovered_at": recovery["at"] if recovery else None,
            "unknown_intervals": gaps}


def scenario(name):
    """Create original, deterministic drill data. Values are entirely synthetic."""
    if name not in SCENARIOS:
        raise ValueError(f"Unknown drill. Choose one of {', '.join(SCENARIOS)}.")
    quiet = [0, 2, -1, 1, -3, 2, -2, 1]
    drift = [0, 2, -6, -18, -32, -55, -61, -70]
    paths = {"quiet": quiet, "stale": quiet, "drift": drift,
             "recovery": drift + [-35, -18, -8, -2]}
    anchor = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
    frames = []
    for index, usdc in enumerate(paths[name]):
        now = anchor + timedelta(minutes=index)
        deltas = {825: (1, 0, -2, 2)[index % 4], 3408: usdc, 4943: (0, -1, 1, -3)[index % 4]}
        quotes = {}
        for asset_id, bps in deltas.items():
            updated = now
            if name == "stale" and asset_id == 3408 and index >= 2:
                updated = anchor + timedelta(minutes=1)
                bps = quiet[1]
            quotes[str(asset_id)] = {"price": round(1 + bps / 10000, 5), "updated": _utc(updated)}
        frames.append({"at": _utc(now), "quotes": quotes})
    return frames
