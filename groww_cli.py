from __future__ import annotations

import argparse
import code
import inspect
import json
import os
from getpass import getpass
from pathlib import Path
import tomllib

from growwapi import GrowwAPI


def _load_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def _first(*values: object) -> str | None:
    for value in values:
        if value is None:
            continue
        value = str(value).strip()
        if value:
            return value
    return None


def _totp_now_from_secret(totp_secret: str) -> str:
    import binascii
    import pyotp

    try:
        return pyotp.TOTP(str(totp_secret)).now()
    except (binascii.Error, ValueError) as e:
        raise SystemExit(
            "Invalid TOTP secret: it must be Base32 from the QR setup. "
            "If you don't have it, paste the 6-digit OTP when prompted."
        ) from e


def _print_response(value: object) -> None:
    try:
        print(json.dumps(value, indent=2, ensure_ascii=True))
    except TypeError:
        print(value)


def _list_api_methods() -> None:
    methods = []
    for name, fn in inspect.getmembers(GrowwAPI, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        sig = str(inspect.signature(fn))
        doc = inspect.getdoc(fn) or ""
        doc_line = doc.splitlines()[0] if doc else ""
        methods.append((name, sig, doc_line))

    for name, sig, doc_line in sorted(methods):
        if doc_line:
            print(f"{name}{sig} - {doc_line}")
        else:
            print(f"{name}{sig}")


def _parse_json(value: str | None, *, default: object) -> object:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON: {e.msg} at pos {e.pos}") from e


def _confirm_if_trading(method_name: str) -> None:
    trading_methods = {
        "place_order",
        "modify_order",
        "cancel_order",
        "create_smart_order",
        "modify_smart_order",
        "cancel_smart_order",
    }
    if method_name in trading_methods:
        confirm = input("Trading action requested. Type PLACE to continue: ").strip()
        if confirm != "PLACE":
            raise SystemExit("Aborted.")


def _extract_holdings(value: object) -> list[dict]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    if isinstance(value, dict):
        for key in ("holdings", "data", "items"):
            items = value.get(key)
            if isinstance(items, list):
                return [v for v in items if isinstance(v, dict)]
    return []


def _holding_matches(item: dict, query: str) -> bool:
    q = query.lower()
    for key in (
        "tradingSymbol",
        "trading_symbol",
        "symbol",
        "companyName",
        "company_name",
        "isin",
        "instrumentToken",
        "instrument_token",
    ):
        value = item.get(key)
        if value and q in str(value).lower():
            return True
    return q in json.dumps(item, default=str).lower()


def _holding_symbol_candidates(items: list[dict]) -> list[str]:
    symbols = []
    for item in items:
        for key in ("tradingSymbol", "trading_symbol", "symbol"):
            value = item.get(key)
            if value:
                symbols.append(str(value).upper())
                break
    return sorted(set(symbols))


def _search_instruments(
    df,
    query: str,
    *,
    exchange: str | None = None,
    segment: str | None = None,
    limit: int = 25,
):
    q = query.strip().lower()
    if not q:
        return df.head(0)

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
        "underlying_symbol",
    ]
    mask = None
    for col in cols:
        if col in filtered.columns:
            series = filtered[col].astype(str).str.lower()
            m = series.str.contains(q, na=False)
            mask = m if mask is None else (mask | m)
    if mask is None:
        return filtered.head(0)

    return filtered[mask].head(limit)


def _print_instrument_rows(df) -> None:
    if df is None or len(df) == 0:
        print("No instruments found.")
        return
    cols = [
        "exchange",
        "segment",
        "trading_symbol",
        "groww_symbol",
        "name",
        "isin",
        "exchange_token",
        "instrument_type",
    ]
    cols = [c for c in cols if c in df.columns]
    print(df[cols].to_string(index=False))


def _choose_flow(available_approval: bool, available_totp: bool) -> str:
    if available_approval:
        return "approval"
    if available_totp:
        return "totp"
    while True:
        choice = input("Choose flow: [1] approval (api_key+secret), [2] totp: ").strip()
        if choice in {"1", "approval"}:
            return "approval"
        if choice in {"2", "totp"}:
            return "totp"
        print("Please enter 1 or 2.")


def _get_access_token(args: argparse.Namespace) -> str:
    cfg = _load_toml(Path(__file__).resolve().parent / ".secrets.toml")

    approval_api_key = _first(
        args.approval_api_key,
        cfg.get("approval_api_key"),
        cfg.get("api_key"),
        os.environ.get("GROWW_APPROVAL_API_KEY"),
        os.environ.get("GROWW_API_KEY"),
    )
    approval_secret = _first(
        args.approval_secret,
        cfg.get("approval_secret"),
        cfg.get("secret"),
        os.environ.get("GROWW_APPROVAL_SECRET"),
        os.environ.get("GROWW_API_SECRET"),
    )

    totp_token = _first(
        args.totp_token,
        cfg.get("totp_token"),
        os.environ.get("GROWW_TOTP_TOKEN"),
    )
    totp_secret = _first(cfg.get("totp_secret"), os.environ.get("GROWW_TOTP_SECRET"))
    totp = _first(args.totp, os.environ.get("GROWW_TOTP"))

    available_approval = bool(approval_api_key and approval_secret)
    available_totp = bool(totp_token and (totp or totp_secret))

    flow = args.flow
    if flow == "auto":
        flow = _choose_flow(available_approval, available_totp)

    if flow == "approval":
        if not approval_api_key:
            approval_api_key = getpass("approval api_key: ")
        if not approval_secret:
            approval_secret = getpass("approval secret: ")
        return GrowwAPI.get_access_token(
            api_key=approval_api_key, secret=approval_secret
        )

    if not totp_token:
        totp_token = getpass("totp_token (TOTP API key): ")
    if not totp and totp_secret:
        totp = _totp_now_from_secret(totp_secret)
    if not totp:
        totp = getpass("current 6-digit OTP: ")
    return GrowwAPI.get_access_token(api_key=totp_token, totp=totp)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interactive CLI for GrowwAPI auth + safe data fetch."
    )
    parser.add_argument(
        "--flow",
        choices=["auto", "approval", "totp"],
        default="auto",
        help="Auth flow to use (default: auto).",
    )
    parser.add_argument("--approval-api-key", help="Approval flow api_key override.")
    parser.add_argument("--approval-secret", help="Approval flow secret override.")
    parser.add_argument("--totp-token", help="TOTP flow token override.")
    parser.add_argument("--totp", help="One-time OTP override (6 digits).")
    parser.add_argument(
        "--list-methods",
        action="store_true",
        help="List available GrowwAPI methods and exit.",
    )
    parser.add_argument(
        "--repl",
        action="store_true",
        help="Start an interactive Python REPL with `groww` client ready.",
    )
    parser.add_argument(
        "--call",
        help="Call a specific GrowwAPI method by name (e.g. get_quote).",
    )
    parser.add_argument(
        "--args",
        help="JSON array of positional args for --call (e.g. '[\"WIPRO\", \"NSE\", \"CASH\", 10]').",
    )
    parser.add_argument(
        "--kwargs",
        help="JSON object of keyword args for --call (e.g. '{\"trading_symbol\":\"WIPRO\"}').",
    )
    parser.add_argument(
        "--instrument-search",
        help="Search instruments by name/symbol/ISIN and exit.",
    )
    parser.add_argument("--exchange", help="Exchange filter for instrument search (e.g. NSE).")
    parser.add_argument("--segment", help="Segment filter for instrument search (e.g. CASH).")
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Max rows for instrument search (default: 25).",
    )
    args = parser.parse_args()

    if args.list_methods:
        _list_api_methods()
        return 0

    access_token = _get_access_token(args)
    groww = GrowwAPI(access_token)

    if args.instrument_search:
        df = groww.get_all_instruments()
        result = _search_instruments(
            df,
            args.instrument_search,
            exchange=args.exchange,
            segment=args.segment,
            limit=args.limit,
        )
        _print_instrument_rows(result)
        return 0

    if args.repl:
        banner = (
            "Groww REPL ready. You have `groww` and `GrowwAPI` in scope.\n"
            "Example: groww.get_quote(trading_symbol='WIPRO', exchange='NSE', segment='CASH', timeout=10)\n"
        )
        code.interact(banner=banner, local={"groww": groww, "GrowwAPI": GrowwAPI})
        return 0

    if args.call:
        method_name = args.call.strip()
        if method_name.startswith("_") or not hasattr(groww, method_name):
            raise SystemExit(f"Unknown method: {method_name}")
        method = getattr(groww, method_name)
        if not callable(method):
            raise SystemExit(f"Attribute is not callable: {method_name}")

        _confirm_if_trading(method_name)

        call_args = _parse_json(args.args, default=[])
        call_kwargs = _parse_json(args.kwargs, default={})
        if not isinstance(call_args, list):
            raise SystemExit("--args must be a JSON array")
        if not isinstance(call_kwargs, dict):
            raise SystemExit("--kwargs must be a JSON object")

        result = method(*call_args, **call_kwargs)
        _print_response(result)
        return 0

    menu = (
        "\nChoose an action:\n"
        "  1) get_user_profile\n"
        "  2) get_holdings_for_user\n"
        "  3) get_positions_for_user\n"
        "  4) get_quote\n"
        "  5) get_ltp\n"
        "  6) get_holding_detail\n"
        "  7) list_api_methods\n"
        "  8) search_instruments\n"
        "  q) quit\n"
    )

    while True:
        print(menu)
        choice = input("> ").strip().lower()
        if choice in {"q", "quit", "exit"}:
            return 0
        if choice == "1":
            _print_response(groww.get_user_profile(timeout=10))
        elif choice == "2":
            _print_response(groww.get_holdings_for_user(timeout=10))
        elif choice == "3":
            segment = input("segment (blank for all): ").strip().upper() or None
            _print_response(groww.get_positions_for_user(segment=segment, timeout=10))
        elif choice == "4":
            symbol = input("trading_symbol (e.g. WIPRO): ").strip().upper()
            exchange = input("exchange [NSE/BSE] (default NSE): ").strip().upper() or "NSE"
            segment = input("segment [CASH/FNO] (default CASH): ").strip().upper() or "CASH"
            _print_response(
                groww.get_quote(
                    trading_symbol=symbol,
                    exchange=exchange,
                    segment=segment,
                    timeout=10,
                )
            )
        elif choice == "5":
            raw = input("symbols comma-separated (e.g. WIPRO,RELIANCE): ").strip()
            exchange = input("exchange [NSE/BSE] (default NSE): ").strip().upper() or "NSE"
            segment = input("segment [CASH/FNO] (default CASH): ").strip().upper() or "CASH"
            symbols = []
            for s in (part.strip().upper() for part in raw.split(",") if part.strip()):
                if ":" in s or "_" in s:
                    symbols.append(s)
                else:
                    symbols.append(f"{exchange}_{s}")
            _print_response(groww.get_ltp(tuple(symbols), segment, timeout=10))
        elif choice == "6":
            query = input("holding symbol / ISIN / name (partial ok): ").strip()
            holdings = groww.get_holdings_for_user(timeout=10)
            items = _extract_holdings(holdings)
            matches = [item for item in items if _holding_matches(item, query)]
            if matches:
                _print_response(matches if len(matches) > 1 else matches[0])
            else:
                print("No match found.")
                print("Note: holdings only include stocks you own. Use get_quote/get_ltp for other symbols.")
        elif choice == "7":
            _list_api_methods()
        elif choice == "8":
            query = input("search (name/symbol/isin): ").strip()
            exchange = input("exchange filter (blank for any): ").strip().upper() or None
            segment = input("segment filter (blank for any): ").strip().upper() or None
            limit_raw = input("max results (default 25): ").strip()
            limit = int(limit_raw) if limit_raw.isdigit() else 25
            df = groww.get_all_instruments()
            result = _search_instruments(
                df, query, exchange=exchange, segment=segment, limit=limit
            )
            _print_instrument_rows(result)
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    raise SystemExit(main())
