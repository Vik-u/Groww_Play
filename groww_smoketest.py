from __future__ import annotations

import argparse
import os
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


def _safe_summary(value: object) -> str:
    if isinstance(value, dict):
        keys = sorted(str(k) for k in value.keys())
        return f"dict(keys={keys[:12]}{'...' if len(keys) > 12 else ''})"
    if isinstance(value, list):
        return f"list(len={len(value)})"
    return type(value).__name__


def _totp_now_from_secret(totp_secret: str) -> str:
    import binascii
    import pyotp

    try:
        return pyotp.TOTP(str(totp_secret)).now()
    except (binascii.Error, ValueError) as e:
        raise ValueError(
            "Invalid `totp_secret`: it must be the Base32 TOTP secret from the QR setup. "
            "If you don't have that, remove/blank `totp_secret` and pass a 6-digit OTP using --totp."
        ) from e


def _get_access_token(*, flow: str, totp_override: str | None) -> str:
    # Note: In Groww docs, TOTP flow uses a "TOTP token" (api_key) which can be different
    # from the approval API key used in the API key + secret flow.
    cfg = _load_toml(Path(__file__).resolve().parent / ".secrets.toml")

    legacy_api_key = _first(cfg.get("api_key"), os.environ.get("GROWW_API_KEY"))
    legacy_secret = _first(cfg.get("secret"), os.environ.get("GROWW_API_SECRET"))

    approval_api_key = _first(
        cfg.get("approval_api_key"),
        legacy_api_key,
        os.environ.get("GROWW_APPROVAL_API_KEY"),
    )
    approval_secret = _first(
        cfg.get("approval_secret"),
        legacy_secret,
        os.environ.get("GROWW_APPROVAL_SECRET"),
    )

    totp_token = _first(cfg.get("totp_token"), os.environ.get("GROWW_TOTP_TOKEN"))
    totp_from_env = _first(os.environ.get("GROWW_TOTP"))
    totp_from_cfg = _first(cfg.get("totp"))
    totp = _first(totp_override, totp_from_env)
    totp_secret = _first(cfg.get("totp_secret"), os.environ.get("GROWW_TOTP_SECRET"))

    use_totp = flow == "totp" or (flow == "auto" and totp_token and (totp or totp_secret))
    if use_totp:
        if not totp_token and legacy_api_key:
            totp_token = legacy_api_key
            print("Note: using `api_key` from .secrets.toml as `totp_token` (rename it to `totp_token` to remove this message).")

        if not totp_token:
            raise SystemExit(
                "Missing totp_token. Add it to .secrets.toml or set GROWW_TOTP_TOKEN."
            )
        if not totp and not totp_secret:
            if legacy_secret:
                totp_secret = legacy_secret
                print("Note: using `secret` from .secrets.toml as `totp_secret` (rename it to `totp_secret` to remove this message).")
            else:
                totp_secret = None

        if not totp and totp_secret:
            try:
                totp = _totp_now_from_secret(str(totp_secret))
            except ValueError as e:
                if flow == "auto":
                    print(
                        "Note: `totp_secret` looks invalid; falling back to approval flow. "
                        "Fix `totp_secret` (Base32 from QR) or run with --flow totp --totp <6-digit>."
                    )
                    use_totp = False
                else:
                    raise SystemExit(str(e)) from e

        if use_totp and not totp and totp_from_cfg:
            totp = totp_from_cfg
            print("Note: using `totp` from .secrets.toml; it expires quickly, prefer `totp_secret` or --totp.")

        if use_totp and not totp:
            raise SystemExit(
                "Missing totp/totp_secret. Add totp_secret to .secrets.toml, or pass --totp, or set GROWW_TOTP."
            )
        if use_totp:
            token_obj = GrowwAPI.get_access_token(api_key=totp_token, totp=totp)
        else:
            token_obj = None

    if not use_totp:
        if not approval_api_key or not approval_secret:
            raise SystemExit(
                "Missing approval credentials. Add approval_api_key + approval_secret to .secrets.toml "
                "(or api_key + secret), or set GROWW_APPROVAL_API_KEY/GROWW_APPROVAL_SECRET."
            )
        token_obj = GrowwAPI.get_access_token(api_key=approval_api_key, secret=approval_secret)

    if isinstance(token_obj, str):
        return token_obj.strip()
    if isinstance(token_obj, dict):
        candidate = (
            token_obj.get("access_token")
            or token_obj.get("token")
            or token_obj.get("accessToken")
            or token_obj.get("jwt")
        )
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return str(token_obj).strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Non-trading smoke test for GrowwAPI auth + basic endpoints."
    )
    parser.add_argument(
        "--flow",
        choices=["auto", "approval", "totp"],
        default="auto",
        help="Which auth flow to use (default: auto).",
    )
    parser.add_argument(
        "--totp-token",
        help="TOTP token / API key for the TOTP flow (overrides .secrets.toml / env).",
    )
    parser.add_argument(
        "--totp",
        help="One-time TOTP code to paste (only used for --flow totp / auto).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout seconds for API calls (default: 10).",
    )
    args = parser.parse_args()

    if args.totp_token:
        os.environ["GROWW_TOTP_TOKEN"] = args.totp_token

    access_token = _get_access_token(flow=args.flow, totp_override=args.totp)
    groww = GrowwAPI(access_token)

    profile = groww.get_user_profile(timeout=args.timeout)
    holdings = groww.get_holdings_for_user(timeout=args.timeout)

    print("Smoke test OK (no orders placed).")
    print("get_user_profile:", _safe_summary(profile))
    print("get_holdings_for_user:", _safe_summary(holdings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
