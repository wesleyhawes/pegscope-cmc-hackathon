# CoinMarketCap API evidence

This is a small, credential-free projection of a real response captured by PegScope on 2026-11-19. It demonstrates the keyless production quote endpoint and the fields the application consumes. It is a point-in-time sample, not a live market display or campaign-key proof.

```text
GET https://pro-api.coinmarketcap.com/public-api/v3/cryptocurrency/quotes/latest
    ?id=825,3408,4943&convert=USD
HTTP 200
Fetched: 2026-11-19T23:01:23.618Z
CMC status: timestamp=2026-11-19T23:01:23.592Z, error_code=0, credit_count=1

{
  "id": 825,
  "symbol": "USDT",
  "quote": [{
    "symbol": "USD",
    "price": 0.9988800633191655,
    "last_updated": "2026-11-19T23:00:01.000Z"
  }]
}
```

The output is selected by the `--proof` option in `pegscope.py`; request headers, credentials and unrelated provider fields are omitted. To reproduce a fresh public call:

```bash
python3 pegscope.py sample --keyless --proof
```

A one-shot keyless refresh attempt on 2026-11-21 returned HTTP 429 (`Rate or credit limit reached`). No quote was captured and no retry was made. This is one result from this environment, not a claim about the endpoint's typical availability. The authenticated campaign-key capture is still required for the final demo.

The app also supports authenticated `/v3/cryptocurrency/quotes/latest` and `/v5/cryptocurrency/ohlcv/historical` calls. For the hackathon entry, capture the authenticated route with the event-issued key and show its code and response in the final demo. Never commit or record the key itself. [Event requirements](https://coinmarketcap.com/api/resources/api-hackathon-2026-11/) · [CMC API reference](https://coinmarketcap.com/api/documentation/pro-api-reference/cryptocurrency)
