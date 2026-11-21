# DoraHacks entry draft

**Title:** PegScope — stablecoin incident desk
**Track:** Markets and Trading Tools
**Short description:** Find persistent moves away from $1, quantify example treasury exposure, and hand the next operator a timestamped incident brief.

## Project description

A treasury operator sees USDC below a dollar and needs to decide whether to investigate. PegScope answers three questions on one screen. How far did it move? Has a second distinct update confirmed the move? What would the difference mean for the position under review?

The desk follows USDC, USDT and DAI using a batched CoinMarketCap USD quote. It checks each provider timestamp before classifying the observation. Operators can scrub through a synthetic move to see exactly when Watch becomes Incident, change the example position size locally, and copy the finding for a colleague. Missing or stale data produces an Unknown state and suppresses the estimate.

A second tool examines USDC during March 9–14, 2023. Using daily OHLCV, it compares the deepest reported mark with that day's close and gives the UTC time of the low. The four synthetic drills run offline so judges can exercise every branch even when markets are quiet.

## Endpoints and evidence

- `GET /public-api/v3/cryptocurrency/quotes/latest` — real keyless production call captured for the demo; returns USD quotes and source timestamps for three stablecoins.
- `GET /v3/cryptocurrency/quotes/latest` — authenticated route implemented for the same three-asset quote workflow; a campaign-key capture is not yet recorded.
- `GET /v5/cryptocurrency/ohlcv/historical` — historical comparison route implemented for daily USDC candles; a live run is not yet recorded.
- Attribution: [Data provided by CoinMarketCap.com](https://coinmarketcap.com/).

## What CMC made possible and where we ran into friction

One batched request gives the operator a common USD reference across three assets, with a per-quote update time. That timestamp lets PegScope distinguish a new observation from a repeated provider update. The historical endpoint supplies the time of the daily low alongside the close, which makes a six-day incident review possible with one request.

The Academy response-format article describes v3 quote lookups as an ID-keyed dictionary, while the current reference and the keyless production response use arrays. We parse the versioned reference shape and check both the asset ID and the quote currency. A version-specific before-and-after example in the Academy article would remove this ambiguity. [Academy guide](https://coinmarketcap.com/academy/article/how-to-read-coinmarketcaps-standardized-json-response-format) · [API reference](https://coinmarketcap.com/api/documentation/pro-api-reference/cryptocurrency)

## Submission links and evidence status

- Public repository: https://github.com/wesleyhawes/pegscope-cmc-hackathon
- Public baseline reviewed: [`224bbd4`](https://github.com/wesleyhawes/pegscope-cmc-hackathon/commit/224bbd4a8350ef56116f616dee2975ecc9e0d384). Code candidate `abd9d356b6deb38f0e8c60179998fc68a9960c64` passes all 27 local tests and is published on GitHub and backed up on Gitea. The latest GitHub Actions run passed on Python 3.10 and 3.13 in [run 44932886444](https://github.com/wesleyhawes/pegscope-cmc-hackathon/actions/runs/44932886444).
- Demo recording: https://github.com/wesleyhawes/pegscope-cmc-hackathon/blob/main/assets/PegScope-Demo-Preview.mp4
- Offline interactive replay: [download from the repository](https://github.com/wesleyhawes/pegscope-cmc-hackathon/blob/main/docs/PegScope-Interactive-Demo.html)
- Real API evidence: the preview shows a public, keyless CMC quote request and response at approximately 00:35. A redacted capture is documented in [`docs/API-EVIDENCE.md`](../docs/API-EVIDENCE.md). It is not authenticated campaign-key evidence.
- Authenticated quote and historical OHLCV runs: not captured yet; `CMC_API_KEY` is not available in the build environment. Do not claim those runs as demonstrated until captured with the entrant's own event key.
- User testing: not conducted.
- DoraHacks project URL and X post: pending entrant registration and submission; add the real URLs here after creating them.

The public baseline and offline recording are available. The keyless response is a real CMC production API call. The refresh fix, incident timeline, and rehearsal script are prepared locally but have not been published. A fresh authenticated quote and historical run would validate campaign-key paths and strengthen the demo. Fill in the DoraHacks project and X post URLs once those are created.
