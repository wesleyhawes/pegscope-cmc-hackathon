# CoinMarketCap API feedback

PegScope uses a batched USD quote request for USDT, USDC and DAI. The per-asset `last_updated` value is useful for detecting repeated or stale observations, while the response status timestamp and credit count help operators keep a compact request receipt.

The integration currently supports the v3 quotes response as an array of assets with nested USD quote arrays, and validates asset IDs, symbols, quote currency and timestamps before using a value. Schema examples that clearly identify the response shape by API version would make implementation easier to verify. The app treats unrecognized or incomplete shapes as missing data rather than silently clearing an alert.

The historical OHLCV endpoint supplies daily low, close and low timestamp fields for a compact retrospective. The application explicitly avoids using daily candles to claim the duration of an intraday event.
