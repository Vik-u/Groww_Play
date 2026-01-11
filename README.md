# Groww_Play

A small toolkit around the `growwapi` SDK: notebooks for auth, a CLI for quick calls, a Gradio UI for browsing endpoints, and a smoke test script. This repo is designed for read-only exploration by default.

## What is in here

- `groww_auth.py`: fetches an access token using approval or TOTP flow.
- `groww_cli.py`: interactive CLI + one-shot `--call` for any SDK method.
- `groww_gradio.py`: Gradio UI for quotes, LTP/OHLC, portfolio, orders, historical data, and feeds.
- `groww_smoketest.py`: non-trading smoke test (profile + holdings).
- `test.ipynb`: minimal auth examples.
- `groww_auth.ipynb`: notebook version of auth with token preview.
- `GROWW_API_REFERENCE.md`: local SDK reference (generated from installed `growwapi`).

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

## Secrets and auth

1) Create secrets file:

```sh
cp .secrets.example.toml .secrets.toml
```

2) Fill in **one** of these flows:

- Approval flow (daily approval required):
  - `approval_api_key`
  - `approval_secret`

- TOTP flow (recommended for automation):
  - `totp_token`
  - `totp_secret` (Base32 from QR)
  - Optional `totp` (one-time code; expires fast)

`.secrets.toml` is gitignored; never commit it.

## Quick usage

### Get a token

```sh
python groww_auth.py
```

Options:
- `--flow approval|totp|auto`
- `--totp 123456` (one-time code override)
- `--print-token` (prints full token)
- `--save-token` (writes `.access_token`, gitignored)

### CLI demo

```sh
python groww_cli.py --flow totp --totp 123456 --call get_quote \
  --kwargs '{"trading_symbol":"WIPRO","exchange":"NSE","segment":"CASH"}'
```

### Gradio UI

```sh
python groww_gradio.py
```

Open the printed URL. In the **Auth** tab, click **Connect** (the UI keeps its own token state).

### Smoke test (read-only)

```sh
python groww_smoketest.py --flow auto
```

## Notes

- The UI blocks trading actions unless you explicitly allow them.
- Some quote fields can be null depending on market hours or instrument type.
- If you see `ModuleNotFoundError: growwapi`, run the setup step again.

## Troubleshooting

- **Buttons do nothing in Gradio**: click **Connect** first; the UI does not share the CLI token.
- **TOTP fails**: remove `totp` from `.secrets.toml` and rely on `totp_secret`, or paste a fresh OTP.
- **Not connected errors**: verify your `totp_token` or `approval_api_key/secret` are valid.
