# Maintainer instructions for PegScope

This repository is the original Round 2 entry for Markets and Trading Tools. Preserve the executable judge path in the README and keep the live proof reproducible. Use Python 3.10+ standard library and native web assets unless a necessary feature justifies a dependency.

1. Run `python3 -m unittest discover -s tests -v` and `python3 casefile.py --demo` from the repository root. Start `python3 pegscope.py serve` and exercise drift, recovery, stale, quiet and the live empty state. After UI edits run `python3 export_demo.py /tmp/pegscope-demo.html` and try the export offline.
2. Route provider access through `cmc_client.py`. Keep credentials in the environment, use the fixed CMC host, and set an explicit timeout. Check HTTP and CMC payload status. Keep the browser, logs, CI and public repository free of secrets, local captures and account details.
3. Preserve evidence types. Source labels distinguish synthetic, public keyless and authenticated API. Only the campaign key can validate the event entry. Record the code, call and minimal real response together. A failing provider request must remain visible as a failure.
4. Keep currency IDs, source timestamps and direction of the peg move intact. Use `quote[].last_updated` for freshness. Never bridge a data gap to count a confirmation. Daily candle extrema do not establish incident duration. Add a regression for any changed state transition.
5. The static export shares the live UI and engine. If its asset references change, update the exporter and test direct file opening. Keep exposure local to the browser.
6. Keep the build read-only. No exchange orders or private portfolio dependencies are necessary. Preserve the small public code boundary. Use `submission/` for release drafts. Check all URLs anonymously before the final submission.
