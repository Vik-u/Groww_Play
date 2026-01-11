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


def _redact(value: str, *, keep_start: int = 6, keep_end: int = 4) -> str:
    if len(value) <= keep_start + keep_end:
        return "***"
    return f"{value[:keep_start]}...{value[-keep_end:]}"


def _first(*values: object) -> str | None:
    for value in values:
        if value is None:
            continue
        value = str(value).strip()
        if value:
            return value
    return None


def _normalize_access_token(value: object) -> str:
    if isinstance(value, str):
        return value
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch a Groww access token using growwapi."
    )
    parser.add_argument(
        "--flow",
        choices=["auto", "approval", "totp"],
        default="auto",
        help="Which auth flow to use (default: auto).",
    )
    parser.add_argument(
        "--totp",
        help="One-time TOTP code (overrides .secrets.toml / env).",
    )
    parser.add_argument(
        "--totp-token",
        help="TOTP token / API key for the TOTP flow (overrides .secrets.toml / env).",
    )
    parser.add_argument(
        "--print-token",
        action="store_true",
        help="Print the full access token (otherwise prints a redacted preview).",
    )
    parser.add_argument(
        "--save-token",
        action="store_true",
        help="Save the access token to .access_token (gitignored).",
    )
    args = parser.parse_args()

    secrets_path = Path(__file__).resolve().parent / ".secrets.toml"
    cfg = _load_toml(secrets_path)

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

    totp_token = _first(
        args.totp_token, cfg.get("totp_token"), os.environ.get("GROWW_TOTP_TOKEN")
    )
    totp_from_env = _first(os.environ.get("GROWW_TOTP"))
    totp_from_cfg = _first(cfg.get("totp"))
    totp = _first(args.totp, totp_from_env)
    totp_secret = _first(cfg.get("totp_secret"), os.environ.get("GROWW_TOTP_SECRET"))

    use_totp = args.flow == "totp" or (
        args.flow == "auto" and totp_token and (totp or totp_secret)
    )

    if use_totp:
        if not totp_token and legacy_api_key:
            totp_token = legacy_api_key
            print(
                "Note: using `api_key` from .secrets.toml as `totp_token` (rename it to `totp_token` to remove this message)."
            )

        if not totp_token:
            raise SystemExit(
                "Missing totp_token. Put it in .secrets.toml or set GROWW_TOTP_TOKEN."
            )
        if not totp and not totp_secret and legacy_secret:
            totp_secret = legacy_secret
            print(
                "Note: using `secret` from .secrets.toml as `totp_secret` (rename it to `totp_secret` to remove this message)."
            )

        if not totp and totp_secret:
            try:
                totp = _totp_now_from_secret(str(totp_secret))
            except ValueError as e:
                if args.flow == "auto":
                    print(
                        "Note: `totp_secret` looks invalid; falling back to approval flow. "
                        "Fix `totp_secret` (Base32 from QR) or run with --flow totp --totp <6-digit>."
                    )
                    use_totp = False
                else:
                    raise SystemExit(str(e)) from e

        if use_totp and not totp and totp_from_cfg:
            totp = totp_from_cfg
            print(
                "Note: using `totp` from .secrets.toml; it expires quickly, prefer `totp_secret` or --totp."
            )

        if use_totp and not totp:
            raise SystemExit(
                "Missing totp/totp_secret. Put `totp_secret` in .secrets.toml (recommended) "
                "or set GROWW_TOTP_SECRET, or paste a one-time `totp` / set GROWW_TOTP."
            )

        if use_totp:
            access_token_obj = GrowwAPI.get_access_token(api_key=totp_token, totp=totp)
        else:
            access_token_obj = None

    if not use_totp:
        if not approval_api_key:
            raise SystemExit(
                "Missing approval_api_key. Put it in .secrets.toml (recommended) or set GROWW_APPROVAL_API_KEY."
            )
        if not approval_secret:
            raise SystemExit(
                "Missing approval_secret. Put it in .secrets.toml (recommended) or set GROWW_APPROVAL_SECRET."
            )
        access_token_obj = GrowwAPI.get_access_token(
            api_key=approval_api_key, secret=approval_secret
        )

    access_token = _normalize_access_token(access_token_obj)

    if not access_token:
        raise SystemExit(
            "Got an empty access token back from the API; double-check your credentials and approvals."
        )

    _ = GrowwAPI(access_token)

    if args.save_token:
        (Path(__file__).resolve().parent / ".access_token").write_text(
            str(access_token).strip() + "\n", encoding="utf-8"
        )

    if args.print_token:
        print(access_token)
    else:
        print(f"Access token: {_redact(str(access_token))}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
