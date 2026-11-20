# PegScope architecture

```text
CMC API ── authenticated/keyless CLI ──> cmc_client.py ──> local SQLite captures
                                                              │
                                                              v
Browser <── loopback HTTP ── pegscope.py ──> peg_engine.py ──> JSON report

casefile.py ── authenticated historical OHLCV ──> daily low-vs-close report
export_demo.py ── synthetic scenarios + web assets ──> standalone offline HTML
```

## Boundaries

- `cmc_client.py` owns the fixed upstream host, allowed endpoint paths, secret header, timeouts, response cap, schema validation, and minimal proof projection.
- `pegscope.py` owns CLI sampling, local SQLite capture persistence, and a loopback-only read-only web server. Opening the dashboard does not make an upstream API call.
- `peg_engine.py` is a deterministic state machine. Source timestamps, capture times, stale gaps, and distinct source updates determine whether a quote is usable.
- `casefile.py` parses daily OHLCV rows and compares low/close marks. Daily candles do not establish intraday duration.
- `export_demo.py` packages the same UI and synthetic scenarios into a self-contained offline HTML file.

The live path never falls back to synthetic data. Synthetic drills have an explicit label and no upstream dependency.
