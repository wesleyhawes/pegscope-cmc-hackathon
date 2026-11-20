# Contributing to PegScope

PegScope is a read-only stablecoin incident desk and CMC hackathon project. Keep changes small enough to review, preserve synthetic/live source labels, and never add a key or captured private account data to the repository.

## Local setup

The application and its test suite use Python's standard library (Python 3.10+).

```bash
python3 -m unittest discover -s tests -v
python3 casefile.py --demo
python3 export_demo.py /tmp/pegscope-demo.html
```

For dashboard work, run `python3 pegscope.py serve` and check the synthetic `drift`, `recovery`, `stale`, and `quiet` views. The live view must remain empty until actual local CMC captures exist.

## Review requirements

- Add a regression for any alert transition, data-quality, API-contract, or persistence change.
- CMC access belongs in `cmc_client.py`; use the fixed provider host, finite timeout, bounded response read, and safe errors.
- Keep credentials in `CMC_API_KEY` in the environment. Do not load a dotenv file, expose a key to browser code, or record it in receipts.
- Keep local captures under the ignored `.local/` directory. Fixtures and screenshots must be synthetic or explicitly reviewed for public release.
- Do not turn missing, duplicate, stale, invalid, or out-of-order data into Normal or recovered status.
- Preserve the one-command synthetic judge path and verify the exported HTML can run offline.

## Pull request checklist

- Explain user-visible behavior and data-source effects.
- List the tests and demo commands run.
- Update README/API evidence docs if endpoint behavior, credit use, or limitations change.
- Confirm `git diff --check` is clean and no secrets or local captures are staged.
