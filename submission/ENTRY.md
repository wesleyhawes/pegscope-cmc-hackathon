# DoraHacks entry draft

**Title:** PegScope — stablecoin incident desk
**Track:** Markets and Trading Tools
**Short description:** Find persistent moves away from $1, quantify example treasury exposure, and hand the next operator a timestamped incident brief.

## Project description

A treasury operator sees USDC below a dollar and needs to decide whether to investigate. PegScope answers three questions on one screen. How far did it move? Has a second distinct update confirmed the move? What would the difference mean for the position under review?

The desk follows USDC, USDT and DAI using a batched CoinMarketCap USD quote. It checks each provider timestamp before classifying the observation. Operators can scrub through a synthetic move to see exactly when Watch becomes Incident, change the example position size locally, and copy the finding for a colleague. Missing or stale data produces an Unknown state and suppresses the estimate.

A second tool examines USDC during March 9–14, 2023. Using daily OHLCV, it compares the deepest reported mark with that day's close and gives the UTC time of the low. The four synthetic drills run offline so judges can exercise every branch even when markets are quiet.

## Endpoints and evidence

- `GET /v3/cryptocurrency/quotes/latest` — three stablecoins in USD, source timestamps and observed call credits.
- `GET /v5/cryptocurrency/ohlcv/historical` — six daily USDC candles with the low, close and low time.
- `GET /public-api/v3/cryptocurrency/quotes/latest` — optional, separately labeled keyless production preview.
- Attribution: [Data provided by CoinMarketCap.com](https://coinmarketcap.com/).

## What CMC made possible and where we ran into friction

One batched request gives the operator a common USD reference across three assets, with a per-quote update time. That timestamp lets PegScope distinguish a new observation from a repeated provider update. The historical endpoint supplies the time of the daily low alongside the close, which makes a six-day incident review possible with one request.

The Academy response-format article describes v3 quote lookups as an ID-keyed dictionary, while the current reference and the keyless production response use arrays. We parse the versioned reference shape and check both the asset ID and the quote currency. A version-specific before-and-after example in the Academy article would remove this ambiguity. [Academy guide](https://coinmarketcap.com/academy/article/how-to-read-coinmarketcaps-standardized-json-response-format) · [API reference](https://coinmarketcap.com/api/documentation/pro-api-reference/cryptocurrency)

## Submission links and evidence status

- Public repository: https://github.com/wesleyhawes/pegscope-cmc-hackathon
- Tested commit: [`73cd5d0`](https://github.com/wesleyhawes/pegscope-cmc-hackathon/commit/73cd5d0fad5757cd1389be1a67bea445512e10b4)
- Demo recording: https://github.com/wesleyhawes/pegscope-cmc-hackathon/blob/main/assets/PegScope-Demo-Preview.mp4
- Offline interactive replay: [download from the repository](https://github.com/wesleyhawes/pegscope-cmc-hackathon/blob/main/docs/PegScope-Interactive-Demo.html)
- Real API evidence: the preview shows a public, keyless CMC quote request and response at approximately 00:35. A redacted capture is documented in [`docs/API-EVIDENCE.md`](../docs/API-EVIDENCE.md). It is not authenticated campaign-key evidence.
- Authenticated quote and historical OHLCV runs: not captured yet; `CMC_API_KEY` is not available in the build environment. Do not claim those runs as demonstrated until captured with the entrant's own event key.
- User testing: not conducted.
- DoraHacks project URL and X post: pending entrant registration and submission; add the real URLs here after creating them.

The public repository and offline recording are ready. Before final submission, confirm the DoraHacks form accepts the keyless production response as real API evidence or record a fresh authenticated call with the event key. Fill the final project and X post URLs only after they exist.
