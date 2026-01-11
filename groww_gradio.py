from __future__ import annotations

import datetime as dt
import inspect
import json
import os
from pathlib import Path
import tomllib

import gradio as gr
from growwapi import GrowwAPI, GrowwFeed


INSTRUMENT_CACHE = {"df": None}
FEED_CACHE: dict[str, GrowwFeed] = {}


def _load_cfg() -> dict:
    path = Path(__file__).resolve().parent / ".secrets.toml"
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _first(*values: object) -> str | None:
    for value in values:
        if value is None:
            continue
        value = str(value).strip()
        if value:
            return value
    return None


def _normalize_token(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        candidate = (
            value.get("access_token")
            or value.get("token")
            or value.get("accessToken")
            or value.get("jwt")
        )
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return str(value).strip()


def _parse_json(value: str) -> object:
    if not value.strip():
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e.msg} at pos {e.pos}") from e


def _require_no_trading(method_name: str, allow_trading: bool) -> None:
    trading_methods = {
        "place_order",
        "modify_order",
        "cancel_order",
        "create_smart_order",
        "modify_smart_order",
        "cancel_smart_order",
    }
    if method_name in trading_methods and not allow_trading:
        raise ValueError("Trading action blocked. Enable 'Allow trading actions' to proceed.")

def _totp_now_from_secret(totp_secret: str) -> str:
    import binascii
    import pyotp

    try:
        return pyotp.TOTP(str(totp_secret)).now()
    except (binascii.Error, ValueError) as e:
        raise ValueError(
            "Invalid TOTP secret: it must be Base32 from the QR setup. "
            "If you don't have it, paste the 6-digit OTP manually."
        ) from e


def _format_exchange_symbols(symbols: str, exchange: str) -> tuple[str, ...]:
    items = []
    for raw in symbols.split(","):
        sym = raw.strip().upper()
        if not sym:
            continue
        if ":" in sym or "_" in sym:
            items.append(sym)
        else:
            items.append(f"{exchange}_{sym}")
    return tuple(items)


def _prune_nulls(value: object) -> object:
    if isinstance(value, dict):
        cleaned: dict = {}
        for key, item in value.items():
            if item is None:
                continue
            cleaned[key] = _prune_nulls(item)
        return cleaned
    if isinstance(value, list):
        return [_prune_nulls(item) for item in value if item is not None]
    return value

def _now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _relative_range(amount: int, unit: str) -> tuple[str, str]:
    end = dt.datetime.now()
    if unit == "minutes":
        start = end - dt.timedelta(minutes=amount)
    elif unit == "hours":
        start = end - dt.timedelta(hours=amount)
    else:
        start = end - dt.timedelta(days=amount)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def _get_client(token: str) -> GrowwAPI:
    return GrowwAPI(token)


def _get_feed(token: str) -> GrowwFeed:
    if token not in FEED_CACHE:
        FEED_CACHE[token] = GrowwFeed(_get_client(token))
    return FEED_CACHE[token]


def _lookup_instrument(
    groww: GrowwAPI,
    exchange: str,
    trading_symbol: str,
    exchange_token: str | None,
) -> dict:
    if exchange_token:
        return {"exchange_token": exchange_token, "exchange": exchange}
    return groww.get_instrument_by_exchange_and_trading_symbol(
        exchange=exchange, trading_symbol=trading_symbol.strip().upper()
    )

def connect(
    flow: str,
    use_secrets: bool,
    approval_api_key: str,
    approval_secret: str,
    totp_token: str,
    totp_secret: str,
    totp: str,
):
    cfg = _load_cfg() if use_secrets else {}

    approval_api_key = _first(
        approval_api_key, cfg.get("approval_api_key"), cfg.get("api_key")
    )
    approval_secret = _first(
        approval_secret, cfg.get("approval_secret"), cfg.get("secret")
    )
    totp_token = _first(totp_token, cfg.get("totp_token"))
    totp_secret = _first(totp_secret, cfg.get("totp_secret"))
    totp = _first(totp, cfg.get("totp"))

    if flow == "auto":
        flow = "approval" if (approval_api_key and approval_secret) else "totp"

    try:
        if flow == "approval":
            if not approval_api_key or not approval_secret:
                return "", "Missing approval api_key/secret."
            token_obj = GrowwAPI.get_access_token(
                api_key=approval_api_key, secret=approval_secret
            )
        else:
            if not totp_token:
                return "", "Missing totp_token."
            if not totp:
                if not totp_secret:
                    return "", "Missing totp or totp_secret."
                totp = _totp_now_from_secret(totp_secret)
            token_obj = GrowwAPI.get_access_token(api_key=totp_token, totp=totp)

        token = _normalize_token(token_obj)
        _ = _get_client(token)
        redacted = token[:6] + "..." + token[-4:] if len(token) > 12 else "***"
        return token, f"Connected. Token: {redacted}"
    except Exception as e:
        return "", f"Auth error: {e}"


def get_quote(token: str, trading_symbol: str, exchange: str, segment: str):
    if not token:
        return {"error": "Not connected"}
    try:
        groww = _get_client(token)
        return groww.get_quote(
            trading_symbol=trading_symbol.strip().upper(),
            exchange=exchange,
            segment=segment,
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}


def get_quote_clean(token: str, trading_symbol: str, exchange: str, segment: str):
    result = get_quote(token, trading_symbol, exchange, segment)
    if isinstance(result, dict) and "error" not in result:
        return _prune_nulls(result)
    return result


def get_ltp(token: str, symbols: str, exchange: str, segment: str):
    if not token:
        return {"error": "Not connected"}
    try:
        groww = _get_client(token)
        exchange_symbols = _format_exchange_symbols(symbols, exchange)
        return groww.get_ltp(exchange_symbols, segment, timeout=10)
    except Exception as e:
        return {"error": str(e)}


def get_ohlc(token: str, symbols: str, exchange: str, segment: str):
    if not token:
        return {"error": "Not connected"}
    try:
        groww = _get_client(token)
        exchange_symbols = _format_exchange_symbols(symbols, exchange)
        return groww.get_ohlc(exchange_symbols, segment, timeout=10)
    except Exception as e:
        return {"error": str(e)}


def get_profile(token: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_user_profile(timeout=10)
    except Exception as e:
        return {"error": str(e)}


def get_holdings(token: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_holdings_for_user(timeout=10)
    except Exception as e:
        return {"error": str(e)}


def get_positions(token: str, segment: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_positions_for_user(
            segment=segment or None, timeout=10
        )
    except Exception as e:
        return {"error": str(e)}


def get_margin(token: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_available_margin_details(timeout=10)
    except Exception as e:
        return {"error": str(e)}


def get_order_list(token: str, page: int, page_size: int, segment: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_order_list(
            page=page or 0,
            page_size=page_size or 25,
            segment=segment or None,
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}


def get_order_detail(token: str, segment: str, order_id: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_order_detail(
            segment=segment, groww_order_id=order_id.strip(), timeout=10
        )
    except Exception as e:
        return {"error": str(e)}


def get_order_status(token: str, segment: str, order_id: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_order_status(
            segment=segment, groww_order_id=order_id.strip(), timeout=10
        )
    except Exception as e:
        return {"error": str(e)}


def get_order_status_by_reference(token: str, segment: str, reference_id: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_order_status_by_reference(
            segment=segment, order_reference_id=reference_id.strip(), timeout=10
        )
    except Exception as e:
        return {"error": str(e)}


def get_trade_list_for_order(
    token: str, segment: str, order_id: str, page: int, page_size: int
):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_trade_list_for_order(
            groww_order_id=order_id.strip(),
            segment=segment,
            page=page or 0,
            page_size=page_size or 25,
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}


def get_smart_order_list(
    token: str,
    smart_order_type: str,
    segment: str,
    status: str,
    page: int,
    page_size: int,
    start_date_time: str,
    end_date_time: str,
):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_smart_order_list(
            smart_order_type=smart_order_type or None,
            segment=segment or None,
            status=status or None,
            page=page or None,
            page_size=page_size or None,
            start_date_time=start_date_time or None,
            end_date_time=end_date_time or None,
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}


def get_smart_order(token: str, segment: str, smart_order_type: str, smart_order_id: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_smart_order(
            segment=segment,
            smart_order_type=smart_order_type,
            smart_order_id=smart_order_id.strip(),
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}


def get_order_margin_details(token: str, segment: str, orders_json: str):
    if not token:
        return {"error": "Not connected"}
    try:
        orders = _parse_json(orders_json)
        if not isinstance(orders, list):
            return {"error": "orders_json must be a JSON list of order dicts"}
        return _get_client(token).get_order_margin_details(
            segment=segment, orders=orders, timeout=10
        )
    except Exception as e:
        return {"error": str(e)}


def get_instrument_by_exchange_and_trading_symbol(token: str, exchange: str, trading_symbol: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_instrument_by_exchange_and_trading_symbol(
            exchange=exchange, trading_symbol=trading_symbol.strip().upper()
        )
    except Exception as e:
        return {"error": str(e)}


def get_instrument_by_exchange_token(token: str, exchange_token: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_instrument_by_exchange_token(
            exchange_token=exchange_token.strip()
        )
    except Exception as e:
        return {"error": str(e)}


def get_instrument_by_groww_symbol(token: str, groww_symbol: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_instrument_by_groww_symbol(
            groww_symbol=groww_symbol.strip()
        )
    except Exception as e:
        return {"error": str(e)}


def get_expiries(token: str, exchange: str, underlying_symbol: str, year: int, month: int):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_expiries(
            exchange=exchange,
            underlying_symbol=underlying_symbol.strip().upper(),
            year=year or None,
            month=month or None,
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}


def get_contracts(token: str, exchange: str, underlying_symbol: str, expiry_date: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_contracts(
            exchange=exchange,
            underlying_symbol=underlying_symbol.strip().upper(),
            expiry_date=expiry_date.strip(),
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}


def get_option_chain(token: str, exchange: str, underlying: str, expiry_date: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_option_chain(
            exchange=exchange,
            underlying=underlying.strip().upper(),
            expiry_date=expiry_date.strip(),
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}


def get_greeks(token: str, exchange: str, underlying: str, trading_symbol: str, expiry: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_client(token).get_greeks(
            exchange=exchange,
            underlying=underlying.strip().upper(),
            trading_symbol=trading_symbol.strip().upper(),
            expiry=expiry.strip(),
        )
    except Exception as e:
        return {"error": str(e)}


def call_method(token: str, method_name: str, args_json: str, kwargs_json: str, allow_trading: bool):
    if not token:
        return {"error": "Not connected"}
    if not method_name.strip():
        return {"error": "Method name is required"}
    try:
        groww = _get_client(token)
        if not hasattr(groww, method_name):
            return {"error": f"Unknown method: {method_name}"}
        method = getattr(groww, method_name)
        if not callable(method):
            return {"error": f"Not callable: {method_name}"}

        _require_no_trading(method_name, allow_trading)

        args = _parse_json(args_json) if args_json.strip() else []
        kwargs = _parse_json(kwargs_json) if kwargs_json.strip() else {}
        if not isinstance(args, list):
            return {"error": "--args must be JSON array"}
        if not isinstance(kwargs, dict):
            return {"error": "--kwargs must be JSON object"}

        return method(*args, **kwargs)
    except Exception as e:
        return {"error": str(e)}


def feed_subscribe_ltp(
    token: str,
    exchange: str,
    segment: str,
    trading_symbol: str,
    exchange_token: str,
):
    if not token:
        return {"error": "Not connected"}
    try:
        groww = _get_client(token)
        instrument = _lookup_instrument(
            groww, exchange, trading_symbol, exchange_token or None
        )
        instrument_list = [
            {
                "exchange": exchange,
                "segment": segment,
                "exchange_token": instrument.get("exchange_token"),
            }
        ]
        feed = _get_feed(token)
        return feed.subscribe_ltp(instrument_list)
    except Exception as e:
        return {"error": str(e)}


def feed_get_ltp(token: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_feed(token).get_ltp()
    except Exception as e:
        return {"error": str(e)}


def feed_unsubscribe_ltp(
    token: str,
    exchange: str,
    segment: str,
    exchange_token: str,
):
    if not token:
        return {"error": "Not connected"}
    try:
        instrument_list = [
            {
                "exchange": exchange,
                "segment": segment,
                "exchange_token": exchange_token.strip(),
            }
        ]
        return _get_feed(token).unsubscribe_ltp(instrument_list)
    except Exception as e:
        return {"error": str(e)}


def feed_subscribe_market_depth(
    token: str,
    exchange: str,
    segment: str,
    trading_symbol: str,
    exchange_token: str,
):
    if not token:
        return {"error": "Not connected"}
    try:
        groww = _get_client(token)
        instrument = _lookup_instrument(
            groww, exchange, trading_symbol, exchange_token or None
        )
        instrument_list = [
            {
                "exchange": exchange,
                "segment": segment,
                "exchange_token": instrument.get("exchange_token"),
            }
        ]
        feed = _get_feed(token)
        return feed.subscribe_market_depth(instrument_list)
    except Exception as e:
        return {"error": str(e)}


def feed_get_market_depth(token: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_feed(token).get_market_depth()
    except Exception as e:
        return {"error": str(e)}


def feed_unsubscribe_market_depth(
    token: str,
    exchange: str,
    segment: str,
    exchange_token: str,
):
    if not token:
        return {"error": "Not connected"}
    try:
        instrument_list = [
            {
                "exchange": exchange,
                "segment": segment,
                "exchange_token": exchange_token.strip(),
            }
        ]
        return _get_feed(token).unsubscribe_market_depth(instrument_list)
    except Exception as e:
        return {"error": str(e)}


def feed_subscribe_index_value(
    token: str,
    exchange: str,
    segment: str,
    trading_symbol: str,
    exchange_token: str,
):
    if not token:
        return {"error": "Not connected"}
    try:
        groww = _get_client(token)
        instrument = _lookup_instrument(
            groww, exchange, trading_symbol, exchange_token or None
        )
        instrument_list = [
            {
                "exchange": exchange,
                "segment": segment,
                "exchange_token": instrument.get("exchange_token"),
            }
        ]
        feed = _get_feed(token)
        return feed.subscribe_index_value(instrument_list)
    except Exception as e:
        return {"error": str(e)}


def feed_get_index_value(token: str):
    if not token:
        return {"error": "Not connected"}
    try:
        return _get_feed(token).get_index_value()
    except Exception as e:
        return {"error": str(e)}


def feed_unsubscribe_index_value(
    token: str,
    exchange: str,
    segment: str,
    exchange_token: str,
):
    if not token:
        return {"error": "Not connected"}
    try:
        instrument_list = [
            {
                "exchange": exchange,
                "segment": segment,
                "exchange_token": exchange_token.strip(),
            }
        ]
        return _get_feed(token).unsubscribe_index_value(instrument_list)
    except Exception as e:
        return {"error": str(e)}


def search_instruments(token: str, query: str, exchange: str, segment: str, limit: int):
    if not token:
        return "Not connected"
    try:
        groww = _get_client(token)
        if INSTRUMENT_CACHE["df"] is None:
            INSTRUMENT_CACHE["df"] = groww.get_all_instruments()
        df = INSTRUMENT_CACHE["df"]
        q = query.strip().lower()
        if not q:
            return "Enter a search term."

        filtered = df
        if exchange:
            filtered = filtered[filtered["exchange"].str.upper() == exchange.upper()]
        if segment:
            filtered = filtered[filtered["segment"].str.upper() == segment.upper()]

        cols = [
            "trading_symbol",
            "groww_symbol",
            "name",
            "isin",
            "exchange_token",
            "exchange",
            "segment",
            "instrument_type",
        ]
        cols = [c for c in cols if c in filtered.columns]

        mask = None
        for col in ["trading_symbol", "groww_symbol", "name", "isin"]:
            if col in filtered.columns:
                m = filtered[col].astype(str).str.lower().str.contains(q, na=False)
                mask = m if mask is None else (mask | m)
        if mask is None:
            return "No instruments found."

        view = filtered[mask].head(limit)
        if view.empty:
            return "No instruments found."
        return view[cols]
    except Exception as e:
        return f"Error: {e}"


def get_historical(
    token: str,
    method: str,
    trading_symbol: str,
    groww_symbol: str,
    exchange: str,
    segment: str,
    interval_minutes: int,
    candle_interval: str,
    start_time: str,
    end_time: str,
    use_relative: bool,
    relative_amount: int,
    relative_unit: str,
):
    if not token:
        return {"error": "Not connected"}, []

    if use_relative:
        start_time, end_time = _relative_range(relative_amount, relative_unit)

    try:
        groww = _get_client(token)
        if method == "historical_candles_v2":
            data = groww.get_historical_candles(
                exchange=exchange,
                segment=segment,
                groww_symbol=groww_symbol.strip(),
                start_time=start_time,
                end_time=end_time,
                candle_interval=candle_interval,
                timeout=15,
            )
        else:
            data = groww.get_historical_candle_data(
                trading_symbol=trading_symbol.strip().upper(),
                exchange=exchange,
                segment=segment,
                start_time=start_time,
                end_time=end_time,
                interval_in_minutes=interval_minutes or None,
                timeout=15,
            )
        return data, _candles_to_rows(data)
    except Exception as e:
        return {"error": str(e)}, []


def _extract_candles(data: object) -> list:
    if isinstance(data, dict):
        for key in ("candles", "data", "candle_data", "historical_data", "result"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    if isinstance(data, list):
        return data
    return []


def _format_ts(value: object) -> str | None:
    if value is None:
        return None
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return str(value)
    # Heuristic: >1e12 likely ms; >1e9 likely seconds.
    if ts > 1_000_000_000_000:
        ts = ts / 1000.0
    try:
        return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return str(value)


def _candles_to_rows(data: object) -> list[dict]:
    rows = []
    for candle in _extract_candles(data):
        row: dict[str, object] = {}
        if isinstance(candle, dict):
            row["timestamp"] = _format_ts(
                candle.get("timestamp")
                or candle.get("time")
                or candle.get("t")
                or candle.get("date")
            )
            row["open"] = candle.get("open") or candle.get("o")
            row["high"] = candle.get("high") or candle.get("h")
            row["low"] = candle.get("low") or candle.get("l")
            row["close"] = candle.get("close") or candle.get("c")
            row["volume"] = candle.get("volume") or candle.get("v")
        elif isinstance(candle, (list, tuple)):
            row["timestamp"] = _format_ts(candle[0] if len(candle) > 0 else None)
            row["open"] = candle[1] if len(candle) > 1 else None
            row["high"] = candle[2] if len(candle) > 2 else None
            row["low"] = candle[3] if len(candle) > 3 else None
            row["close"] = candle[4] if len(candle) > 4 else None
            row["volume"] = candle[5] if len(candle) > 5 else None
        else:
            continue
        rows.append(row)
    return rows

def _parse_candle_close(candle: object) -> float | None:
    if isinstance(candle, dict):
        for key in ("close", "c"):
            if key in candle:
                try:
                    return float(candle[key])
                except (TypeError, ValueError):
                    return None
    if isinstance(candle, (list, tuple)) and len(candle) >= 5:
        try:
            return float(candle[4])
        except (TypeError, ValueError):
            return None
    return None


def backtest_simple(
    token: str,
    trading_symbol: str,
    exchange: str,
    segment: str,
    start_time: str,
    end_time: str,
    interval_minutes: int,
):
    if not token:
        return {"error": "Not connected"}
    try:
        groww = _get_client(token)
        data = groww.get_historical_candle_data(
            trading_symbol=trading_symbol.strip().upper(),
            exchange=exchange,
            segment=segment,
            start_time=start_time,
            end_time=end_time,
            interval_in_minutes=interval_minutes or None,
            timeout=15,
        )
        candles = _extract_candles(data)
        closes = [c for c in (_parse_candle_close(x) for x in candles) if c is not None]
        if len(closes) < 2:
            return {"error": "Not enough candle data to compute backtest summary."}
        start_close = closes[0]
        end_close = closes[-1]
        return {
            "count": len(closes),
            "start_close": start_close,
            "end_close": end_close,
            "return_pct": ((end_close - start_close) / start_close) * 100.0,
        }
    except Exception as e:
        return {"error": str(e)}


def list_methods() -> str:
    lines = []
    for name, fn in inspect.getmembers(GrowwAPI, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        sig = str(inspect.signature(fn))
        doc = inspect.getdoc(fn) or ""
        summary = doc.splitlines()[0] if doc else ""
        if summary:
            lines.append(f"- {name}{sig} — {summary}")
        else:
            lines.append(f"- {name}{sig}")
    return "\n".join(lines)


with gr.Blocks(title="Groww API Explorer") as demo:
    gr.Markdown("# Groww API Explorer")
    gr.Markdown(
        "Use `.secrets.toml` (recommended) or paste values here. "
        "This UI only calls **read‑only** endpoints by default."
    )

    token_state = gr.State("")

    with gr.Accordion("Auth", open=True):
        flow = gr.Radio(
            ["auto", "approval", "totp"],
            value="auto",
            label="Auth flow",
        )
        use_secrets = gr.Checkbox(value=True, label="Use .secrets.toml defaults")
        with gr.Row():
            approval_api_key = gr.Textbox(label="approval_api_key", type="password")
            approval_secret = gr.Textbox(label="approval_secret", type="password")
        with gr.Row():
            totp_token = gr.Textbox(label="totp_token", type="password")
            totp_secret = gr.Textbox(label="totp_secret (Base32)", type="password")
            totp = gr.Textbox(label="one‑time OTP", type="password")
        connect_btn = gr.Button("Connect")
        status = gr.Textbox(label="Status", interactive=False)

        connect_btn.click(
            connect,
            inputs=[
                flow,
                use_secrets,
                approval_api_key,
                approval_secret,
                totp_token,
                totp_secret,
                totp,
            ],
            outputs=[token_state, status],
        )

    with gr.Tab("Live Data"):
        gr.Markdown("### Quote (single symbol)")
        with gr.Row():
            q_symbol = gr.Textbox(value="WIPRO", label="trading_symbol")
            q_exchange = gr.Dropdown(["NSE", "BSE"], value="NSE", label="exchange")
            q_segment = gr.Dropdown(["CASH", "FNO"], value="CASH", label="segment")
        q_clean = gr.Checkbox(value=True, label="Hide null fields")
        with gr.Row():
            q_btn = gr.Button("Get Quote")
            q_btn_clean = gr.Button("Get Quote (clean)")
        q_out = gr.JSON()
        q_btn.click(get_quote, inputs=[token_state, q_symbol, q_exchange, q_segment], outputs=q_out)
        q_btn_clean.click(get_quote_clean, inputs=[token_state, q_symbol, q_exchange, q_segment], outputs=q_out)

        gr.Markdown("### LTP / OHLC (multiple symbols)")
        symbols = gr.Textbox(
            value="WIPRO,RELIANCE", label="symbols (comma‑separated)"
        )
        ltp_exchange = gr.Dropdown(["NSE", "BSE"], value="NSE", label="exchange")
        ltp_segment = gr.Dropdown(["CASH", "FNO"], value="CASH", label="segment")
        with gr.Row():
            ltp_btn = gr.Button("Get LTP")
            ohlc_btn = gr.Button("Get OHLC")
        ltp_out = gr.JSON()
        ohlc_out = gr.JSON()
        ltp_btn.click(get_ltp, inputs=[token_state, symbols, ltp_exchange, ltp_segment], outputs=ltp_out)
        ohlc_btn.click(get_ohlc, inputs=[token_state, symbols, ltp_exchange, ltp_segment], outputs=ohlc_out)

        gr.Markdown("### Market Depth (Feed)")
        with gr.Row():
            md_symbol = gr.Textbox(value="WIPRO", label="trading_symbol")
            md_exchange = gr.Dropdown(["NSE", "BSE"], value="NSE", label="exchange")
            md_segment = gr.Dropdown(["CASH", "FNO"], value="CASH", label="segment")
        md_exchange_token = gr.Textbox(label="exchange_token (optional)")
        with gr.Row():
            md_sub_btn = gr.Button("Subscribe Depth")
            md_get_btn = gr.Button("Get Depth")
            md_unsub_btn = gr.Button("Unsubscribe Depth")
        md_out = gr.JSON()
        md_sub_btn.click(
            feed_subscribe_market_depth,
            inputs=[token_state, md_exchange, md_segment, md_symbol, md_exchange_token],
            outputs=md_out,
        )
        md_get_btn.click(feed_get_market_depth, inputs=[token_state], outputs=md_out)
        md_unsub_btn.click(
            feed_unsubscribe_market_depth,
            inputs=[token_state, md_exchange, md_segment, md_exchange_token],
            outputs=md_out,
        )

    with gr.Tab("Portfolio"):
        with gr.Row():
            profile_btn = gr.Button("Get Profile")
            holdings_btn = gr.Button("Get Holdings")
        profile_out = gr.JSON()
        holdings_out = gr.JSON()
        profile_btn.click(get_profile, inputs=[token_state], outputs=profile_out)
        holdings_btn.click(get_holdings, inputs=[token_state], outputs=holdings_out)

        gr.Markdown("### Positions")
        pos_segment = gr.Dropdown(
            ["", "CASH", "FNO"], value="", label="segment (optional)"
        )
        pos_btn = gr.Button("Get Positions")
        pos_out = gr.JSON()
        pos_btn.click(get_positions, inputs=[token_state, pos_segment], outputs=pos_out)

        gr.Markdown("### Margin")
        margin_btn = gr.Button("Get Available Margin")
        margin_out = gr.JSON()
        margin_btn.click(get_margin, inputs=[token_state], outputs=margin_out)

        gr.Markdown("### Order Margin (Basket)")
        orders_json = gr.Textbox(
            label="orders JSON (list of order dicts)",
            lines=6,
            placeholder='[{"segment":"CASH","exchange":"NSE","trading_symbol":"WIPRO","transaction_type":"BUY","quantity":1,"product":"CNC","order_type":"MARKET"}]',
        )
        orders_segment = gr.Dropdown(["CASH", "FNO"], value="CASH", label="segment")
        orders_margin_btn = gr.Button("Get Order Margin")
        orders_margin_out = gr.JSON()
        orders_margin_btn.click(
            get_order_margin_details,
            inputs=[token_state, orders_segment, orders_json],
            outputs=orders_margin_out,
        )

    with gr.Tab("Orders"):
        gr.Markdown("### Order List")
        with gr.Row():
            order_page = gr.Number(value=0, precision=0, label="page")
            order_page_size = gr.Number(value=25, precision=0, label="page_size")
            order_segment = gr.Dropdown(["", "CASH", "FNO"], value="", label="segment (optional)")
        order_list_btn = gr.Button("Get Orders")
        order_list_out = gr.JSON()
        order_list_btn.click(
            get_order_list,
            inputs=[token_state, order_page, order_page_size, order_segment],
            outputs=order_list_out,
        )

        gr.Markdown("### Order Detail / Status")
        with gr.Row():
            order_id = gr.Textbox(label="groww_order_id")
            order_seg = gr.Dropdown(["CASH", "FNO"], value="CASH", label="segment")
        with gr.Row():
            order_detail_btn = gr.Button("Get Order Detail")
            order_status_btn = gr.Button("Get Order Status")
        order_detail_out = gr.JSON()
        order_status_out = gr.JSON()
        order_detail_btn.click(
            get_order_detail,
            inputs=[token_state, order_seg, order_id],
            outputs=order_detail_out,
        )
        order_status_btn.click(
            get_order_status,
            inputs=[token_state, order_seg, order_id],
            outputs=order_status_out,
        )

        gr.Markdown("### Order Status by Reference")
        ref_id = gr.Textbox(label="order_reference_id")
        ref_btn = gr.Button("Get Status by Reference")
        ref_out = gr.JSON()
        ref_btn.click(
            get_order_status_by_reference,
            inputs=[token_state, order_seg, ref_id],
            outputs=ref_out,
        )

        gr.Markdown("### Trade List for Order")
        with gr.Row():
            trade_page = gr.Number(value=0, precision=0, label="page")
            trade_page_size = gr.Number(value=25, precision=0, label="page_size")
        trade_btn = gr.Button("Get Trades")
        trade_out = gr.JSON()
        trade_btn.click(
            get_trade_list_for_order,
            inputs=[token_state, order_seg, order_id, trade_page, trade_page_size],
            outputs=trade_out,
        )

    with gr.Tab("Smart Orders"):
        gr.Markdown("### Smart Order List")
        with gr.Row():
            so_type = gr.Dropdown(["", "GTT", "OCO"], value="", label="smart_order_type (optional)")
            so_segment = gr.Dropdown(["", "CASH", "FNO"], value="", label="segment (optional)")
            so_status = gr.Textbox(label="status (optional)")
        with gr.Row():
            so_page = gr.Number(value=0, precision=0, label="page (optional)")
            so_page_size = gr.Number(value=25, precision=0, label="page_size (optional)")
        with gr.Row():
            so_start = gr.Textbox(label="start_date_time (optional)")
            so_end = gr.Textbox(label="end_date_time (optional)")
        so_list_btn = gr.Button("Get Smart Orders")
        so_list_out = gr.JSON()
        so_list_btn.click(
            get_smart_order_list,
            inputs=[token_state, so_type, so_segment, so_status, so_page, so_page_size, so_start, so_end],
            outputs=so_list_out,
        )

        gr.Markdown("### Smart Order Detail")
        so_id = gr.Textbox(label="smart_order_id")
        so_detail_btn = gr.Button("Get Smart Order")
        so_detail_out = gr.JSON()
        so_detail_btn.click(
            get_smart_order,
            inputs=[token_state, so_segment, so_type, so_id],
            outputs=so_detail_out,
        )

    with gr.Tab("Instrument Search"):
        search_query = gr.Textbox(label="search name/symbol/isin")
        s_exchange = gr.Textbox(label="exchange filter (optional)")
        s_segment = gr.Textbox(label="segment filter (optional)")
        s_limit = gr.Slider(1, 200, value=25, step=1, label="limit")
        search_btn = gr.Button("Search")
        search_out = gr.Dataframe(label="results")
        search_btn.click(
            search_instruments,
            inputs=[token_state, search_query, s_exchange, s_segment, s_limit],
            outputs=search_out,
        )

    with gr.Tab("Derivatives"):
        gr.Markdown("### Expiries")
        with gr.Row():
            exp_exchange = gr.Dropdown(["NSE", "BSE"], value="NSE", label="exchange")
            exp_underlying = gr.Textbox(label="underlying_symbol (e.g. NIFTY)")
            exp_year = gr.Number(value=0, precision=0, label="year (optional)")
            exp_month = gr.Number(value=0, precision=0, label="month (optional)")
        exp_btn = gr.Button("Get Expiries")
        exp_out = gr.JSON()
        exp_btn.click(
            get_expiries,
            inputs=[token_state, exp_exchange, exp_underlying, exp_year, exp_month],
            outputs=exp_out,
        )

        gr.Markdown("### Contracts")
        with gr.Row():
            con_exchange = gr.Dropdown(["NSE", "BSE"], value="NSE", label="exchange")
            con_underlying = gr.Textbox(label="underlying_symbol (e.g. NIFTY)")
            con_expiry = gr.Textbox(label="expiry_date (yyyy-MM-dd)")
        con_btn = gr.Button("Get Contracts")
        con_out = gr.JSON()
        con_btn.click(
            get_contracts,
            inputs=[token_state, con_exchange, con_underlying, con_expiry],
            outputs=con_out,
        )

        gr.Markdown("### Option Chain")
        with gr.Row():
            oc_exchange = gr.Dropdown(["NSE", "BSE"], value="NSE", label="exchange")
            oc_underlying = gr.Textbox(label="underlying (e.g. NIFTY)")
            oc_expiry = gr.Textbox(label="expiry_date (yyyy-MM-dd)")
        oc_btn = gr.Button("Get Option Chain")
        oc_out = gr.JSON()
        oc_btn.click(
            get_option_chain,
            inputs=[token_state, oc_exchange, oc_underlying, oc_expiry],
            outputs=oc_out,
        )

        gr.Markdown("### Greeks")
        with gr.Row():
            gr_exchange = gr.Dropdown(["NSE", "BSE"], value="NSE", label="exchange")
            gr_underlying = gr.Textbox(label="underlying (e.g. NIFTY)")
            gr_symbol = gr.Textbox(label="trading_symbol (option/future)")
            gr_expiry = gr.Textbox(label="expiry (yyyy-MM-dd)")
        gr_btn = gr.Button("Get Greeks")
        gr_out = gr.JSON()
        gr_btn.click(
            get_greeks,
            inputs=[token_state, gr_exchange, gr_underlying, gr_symbol, gr_expiry],
            outputs=gr_out,
        )

    with gr.Tab("Historical Data"):
        gr.Markdown(
            "Candle format: timestamp, open, high, low, close, volume (table below)."
        )
        method = gr.Radio(
            ["historical_candle_data", "historical_candles_v2"],
            value="historical_candle_data",
            label="method",
        )
        with gr.Row():
            h_symbol = gr.Textbox(value="WIPRO", label="trading_symbol")
            h_groww_symbol = gr.Textbox(label="groww_symbol (for v2)")
        with gr.Row():
            h_exchange = gr.Dropdown(["NSE", "BSE"], value="NSE", label="exchange")
            h_segment = gr.Dropdown(["CASH", "FNO"], value="CASH", label="segment")
        with gr.Row():
            h_interval_min = gr.Number(value=5, precision=0, label="interval_in_minutes")
            h_candle_interval = gr.Dropdown(
                ["1minute", "2minute", "5minute", "10minute", "15minute", "30minute", "1hour", "4hour", "1day", "1week", "1month"],
                value="5minute",
                label="candle_interval (v2)",
            )
        with gr.Row():
            h_start = gr.Textbox(value=_now_str(), label="start_time (yyyy-MM-dd HH:mm:ss)")
            h_end = gr.Textbox(value=_now_str(), label="end_time (yyyy-MM-dd HH:mm:ss)")
        use_relative = gr.Checkbox(value=True, label="Use relative range")
        with gr.Row():
            rel_amount = gr.Number(value=60, precision=0, label="relative amount")
            rel_unit = gr.Dropdown(["minutes", "hours", "days"], value="minutes", label="relative unit")
        hist_btn = gr.Button("Get Historical Data")
        hist_out = gr.JSON()
        hist_table = gr.Dataframe(label="candles")
        hist_btn.click(
            get_historical,
            inputs=[
                token_state,
                method,
                h_symbol,
                h_groww_symbol,
                h_exchange,
                h_segment,
                h_interval_min,
                h_candle_interval,
                h_start,
                h_end,
                use_relative,
                rel_amount,
                rel_unit,
            ],
            outputs=[hist_out, hist_table],
        )

    with gr.Tab("Backtesting (simple)"):
        gr.Markdown("Compute a simple return between first/last candle in a range.")
        with gr.Row():
            bt_symbol = gr.Textbox(value="WIPRO", label="trading_symbol")
            bt_exchange = gr.Dropdown(["NSE", "BSE"], value="NSE", label="exchange")
            bt_segment = gr.Dropdown(["CASH", "FNO"], value="CASH", label="segment")
        with gr.Row():
            bt_start = gr.Textbox(label="start_time (yyyy-MM-dd HH:mm:ss)")
            bt_end = gr.Textbox(label="end_time (yyyy-MM-dd HH:mm:ss)")
            bt_interval = gr.Number(value=5, precision=0, label="interval_in_minutes")
        bt_btn = gr.Button("Run Backtest")
        bt_out = gr.JSON()
        bt_btn.click(
            backtest_simple,
            inputs=[token_state, bt_symbol, bt_exchange, bt_segment, bt_start, bt_end, bt_interval],
            outputs=bt_out,
        )

    with gr.Tab("Feed"):
        gr.Markdown("Subscribe to live feeds (LTP / Index). Use exchange_token from Instrument Search.")
        with gr.Row():
            fd_symbol = gr.Textbox(value="WIPRO", label="trading_symbol")
            fd_exchange = gr.Dropdown(["NSE", "BSE"], value="NSE", label="exchange")
            fd_segment = gr.Dropdown(["CASH", "FNO"], value="CASH", label="segment")
        fd_exchange_token = gr.Textbox(label="exchange_token (optional)")
        with gr.Row():
            fd_ltp_sub = gr.Button("Subscribe LTP")
            fd_ltp_get = gr.Button("Get LTP Feed")
            fd_ltp_unsub = gr.Button("Unsubscribe LTP")
        fd_ltp_out = gr.JSON()
        fd_ltp_sub.click(
            feed_subscribe_ltp,
            inputs=[token_state, fd_exchange, fd_segment, fd_symbol, fd_exchange_token],
            outputs=fd_ltp_out,
        )
        fd_ltp_get.click(feed_get_ltp, inputs=[token_state], outputs=fd_ltp_out)
        fd_ltp_unsub.click(
            feed_unsubscribe_ltp,
            inputs=[token_state, fd_exchange, fd_segment, fd_exchange_token],
            outputs=fd_ltp_out,
        )

        gr.Markdown("### Index Feed")
        with gr.Row():
            idx_symbol = gr.Textbox(value="NIFTY", label="trading_symbol")
            idx_exchange = gr.Dropdown(["NSE", "BSE"], value="NSE", label="exchange")
            idx_segment = gr.Dropdown(["CASH", "FNO"], value="CASH", label="segment")
        idx_exchange_token = gr.Textbox(label="exchange_token (optional)")
        with gr.Row():
            idx_sub = gr.Button("Subscribe Index")
            idx_get = gr.Button("Get Index Feed")
            idx_unsub = gr.Button("Unsubscribe Index")
        idx_out = gr.JSON()
        idx_sub.click(
            feed_subscribe_index_value,
            inputs=[token_state, idx_exchange, idx_segment, idx_symbol, idx_exchange_token],
            outputs=idx_out,
        )
        idx_get.click(feed_get_index_value, inputs=[token_state], outputs=idx_out)
        idx_unsub.click(
            feed_unsubscribe_index_value,
            inputs=[token_state, idx_exchange, idx_segment, idx_exchange_token],
            outputs=idx_out,
        )

    with gr.Tab("SDK Methods"):
        methods_md = gr.Markdown()
        methods_btn = gr.Button("List Methods")
        methods_btn.click(list_methods, inputs=[], outputs=methods_md)

    with gr.Tab("Method Call"):
        allow_trading = gr.Checkbox(value=False, label="Allow trading actions")
        method_name = gr.Textbox(label="method name (e.g. get_quote)")
        method_args = gr.Textbox(label="args JSON array", lines=2, placeholder='["WIPRO", "NSE", "CASH", 10]')
        method_kwargs = gr.Textbox(label="kwargs JSON object", lines=3, placeholder='{"trading_symbol":"WIPRO","exchange":"NSE","segment":"CASH"}')
        call_btn = gr.Button("Call Method")
        call_out = gr.JSON()
        call_btn.click(
            call_method,
            inputs=[token_state, method_name, method_args, method_kwargs, allow_trading],
            outputs=call_out,
        )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=True)
