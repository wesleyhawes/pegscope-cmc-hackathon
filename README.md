# PegScope

A stablecoin incident desk for the person on call for a USD-denominated crypto treasury. PegScope tracks USDC, USDT and DAI. An operator can check whether a price move has persisted across distinct updates, estimate what the move means for a position and copy an incident brief with the evidence.

**Build with CMC · Round 2 · Markets and Trading Tools**

Watch the [44-second walkthrough](assets/PegScope-Demo-Preview.mp4) or open the [offline interactive replay](docs/PegScope-Interactive-Demo.html). The walkthrough includes synthetic triage states and a genuine keyless CMC request/response. The authenticated campaign-key proof remains a final recording step after event registration.

## Try it in one minute

Requires Python 3.10 or newer. The app uses the Python standard library, SQLite and plain browser JavaScript. From this directory:

```bash
python3 pegscope.py serve
```

Open **http://127.0.0.1:8765**. In **Peg drift**, select USDC. Step from frame 6 to frame 7 and see the second distinct quote trigger an incident. Frame 8 reaches −70 basis points. The example 100,000 units are marked $700 below peg. Select **Stale feed** to see the price and impact become unavailable. These are synthetic scenarios. **Recovery** demonstrates the two-update recovery condition.

To build a standalone HTML version containing all four synthetic replays, run:

```bash
python3 export_demo.py PegScope-Interactive-Demo.html
```

Open the generated file in a modern browser. It runs offline and can also be hosted as a static file. The live collector is available through the Python app.

## Collect real observations

Register on the [official event page](https://coinmarketcap.com/api/resources/api-hackathon-2026-11/) with the email on your CMC account. Supply the campaign account's key to your terminal as the environment variable `CMC_API_KEY`. The app does not read a dotenv file. Keep credentials off camera. The following command collects one authenticated sample into the local database and shows selected fields from the real response:

```bash
python3 pegscope.py sample --proof
```

Select **Live · Collected quotes** in the local app and refresh it. To gather three samples in the background of a demo, use a second terminal with the same environment and run:

```bash
python3 pegscope.py sample --count 3 --interval 60
```

For a genuine **public, keyless** trial, run `python3 pegscope.py sample --keyless --proof`. The most recently captured source determines which stream the live view displays. Keyless and authenticated observations stay separate. Standard proof projects one record and selected metadata from the response. All three assets are processed for analysis. A redacted, real keyless response captured on 2026-11-19 is recorded in [API evidence](docs/API-EVIDENCE.md); it demonstrates the public endpoint, but does not replace a fresh authenticated event-key capture for the final submission.

### Historical case file

```bash
python3 casefile.py          # Startup key required for the real March 9–14, 2023 USDC case
python3 casefile.py --demo   # completely fictional daily-candle example, works offline
```

For each UTC day, compare the signed deviation at the day's low and close, with the provider's timestamp for the low. A closing mark alone can miss the deepest move. The report does not estimate duration or use daily bars to confirm minute-scale incidents. [Circle's March 2023 account](https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes)

## CoinMarketCap endpoints

| Method and path | Inputs | What PegScope uses |
| --- | --- | --- |
| `GET /v3/cryptocurrency/quotes/latest` | `id=825,3408,4943&convert=USD` | Per-asset USD price and provider update time, plus status timestamp and credits for the receipt |
| `GET /v5/cryptocurrency/ohlcv/historical` | `id=3408&convert_id=2781&interval=1d&time_start=2023-03-09&time_end=2023-03-14` | Closed daily candles for the historical comparison, including the time of the low |
| `GET /public-api/v3/cryptocurrency/quotes/latest` | Same as latest quotes | Optional production keyless preview, explicitly labeled in the UI and receipt |

Base URL `https://pro-api.coinmarketcap.com`. Both authenticated calls use the `X-CMC_PRO_API_KEY` header on the server. [CMC cryptocurrency API reference](https://coinmarketcap.com/api/documentation/pro-api-reference/cryptocurrency)

## How the incident decision works

One basis point is 0.01%. Signed deviation is `(USD price − 1) × 10,000`. Position impact in dollars is `units × (USD price − 1)`. This is an indicative mark using an aggregate quote. Fill price, fees, redemption, issuer solvency and wallet balances are outside the calculation. The example quantity stays in the browser.

| State | Rule |
| --- | --- |
| Normal | Fresh quote below the 25 bp watch threshold and no unresolved incident |
| Watch | At least 25 bp absolute deviation with no confirmed incident |
| Incident | Two distinct, fresh updates at least 50 bp away, both above or both below peg. Clear after two distinct updates within 10 bp inclusive. |
| Unknown | Missing, invalid, conflicting, out-of-order, future-dated or older-than-180-second quote. A gap breaks consecutive runs. An open incident still needs two good readings to clear. |

These thresholds are configurable in source as product defaults. They have not been calibrated as predictors of issuer failure. The 180-second freshness window allows a 60-second sampler to miss two expected updates. Each observation keeps its source time and capture time. A repeated source timestamp cannot confirm a breach. Operator actions are read-only.

## Reliability and operating costs

The server binds to loopback, serves only named assets and never triggers an upstream call on a page view. CLI samples persist in `.local/captures.sqlite3`. Use `PEGSCOPE_DB` or `python3 pegscope.py --db /path/to/db.sqlite3 serve` to select another database. Use the same path for the collector. Collection exits on 401/403, 429, provider errors, or timeout. Honor a provider retry interval before starting a new collection. Previous valid data retains its own timestamp. The live chart displays up to 120 recent points, with incident state reconstructed from the available stream.

The reference prices a batched three-asset USD latest quote at one credit and up to 100 returned historical candles at one credit. A three-sample walk-through plus the six-day case therefore budgets about four credits. Inspect the real receipt and your own plan. After Startup expires, Basic supports authenticated latest quotes. The historical March case requires an entitled plan. Record it before the deadline and keep the synthetic HTML demo and video available during judging. [CMC reference](https://coinmarketcap.com/api/documentation/pro-api-reference/cryptocurrency) · [Plans](https://coinmarketcap.com/api/pricing/)

## Development

```bash
python3 -m unittest discover -s tests -v
```

- `cmc_client.py` handles the fixed upstream routes, authentication and minimal proof.
- `peg_engine.py` defines deterministic alert transitions and original synthetic observations.
- `pegscope.py` provides collection, persistence and the local read-only HTTP app.
- `casefile.py` computes the historical low-versus-close comparison.
- `web/` contains all dashboard assets. `export_demo.py` renders the portable replay.
- `tests/` covers alert semantics, data quality, contracts and HTTP behavior.
- `submission/` holds drafts for the entry, recording and API feedback.

Data provided by [CoinMarketCap.com](https://coinmarketcap.com/).

## License and rights

This repository is published for hackathon review under a proprietary, all-rights-reserved notice. It has no general open-source reuse license. See [LICENSE](LICENSE). Copyright can restrict copying this code and these original assets, but it does not give exclusive rights to the underlying product idea or methods.
