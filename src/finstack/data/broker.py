"""
FinStack Broker Integration — Angel One SmartAPI

Provides real-time (zero-delay) market data when the user configures
their Angel One API credentials as environment variables.

Your API key is NEVER stored in code or committed to GitHub.
It lives in your local .env file which is in .gitignore.

Setup (one-time):
    Add to your .env file:
        ANGEL_API_KEY=your_api_key
        ANGEL_CLIENT_ID=your_client_id (e.g. R1234567)
        ANGEL_PASSWORD=your_pin
        ANGEL_TOTP_SECRET=your_totp_secret_key

    Install optional dependency:
        pip install finstack-mcp[broker]

Without these env vars, all tools fall back to yfinance (15-min delay).
With them, you get real-time NSE/BSE data via Angel One SmartAPI.

Angel One SmartAPI docs: https://smartapi.angelbroking.com/
"""

import os
import logging
from datetime import datetime
from typing import Optional

import httpx

from finstack.utils.cache import cached, quotes_cache, general_cache
from finstack.utils.helpers import clean_nan

logger = logging.getLogger("finstack.data.broker")

SMARTAPI_BASE = "https://apiconnect.angelbroking.com"

# ── NSE token map for common symbols (Angel One uses numeric tokens) ──
NSE_TOKEN_MAP = {
    "NIFTY": "26000",
    "BANKNIFTY": "26009",
    "FINNIFTY": "26037",
    "MIDCPNIFTY": "26074",
    "SENSEX": "1",
    "RELIANCE": "2885",
    "TCS": "11536",
    "HDFCBANK": "1333",
    "INFY": "1594",
    "ICICIBANK": "4963",
    "SBIN": "3045",
    "WIPRO": "3787",
    "AXISBANK": "5900",
    "KOTAKBANK": "1922",
    "BHARTIARTL": "10604",
    "ITC": "1660",
    "HINDUNILVR": "1394",
    "BAJFINANCE": "317",
    "MARUTI": "10999",
    "TITAN": "3506",
    "ADANIENT": "25",
    "ADANIPORTS": "15083",
    "POWERGRID": "14977",
    "NTPC": "11630",
    "ONGC": "2475",
    "LT": "11483",
    "SUNPHARMA": "3351",
    "ULTRACEMCO": "11532",
    "ASIANPAINT": "236",
    "NESTLEIND": "17963",
}


def _is_configured() -> bool:
    """Check if Angel One credentials are set in environment."""
    return all([
        os.getenv("ANGEL_API_KEY"),
        os.getenv("ANGEL_CLIENT_ID"),
        os.getenv("ANGEL_PASSWORD"),
    ])


def _get_totp() -> Optional[str]:
    """Generate TOTP from secret if pyotp is available."""
    secret = os.getenv("ANGEL_TOTP_SECRET")
    if not secret:
        return None
    try:
        import pyotp
        return pyotp.TOTP(secret).now()
    except ImportError:
        logger.warning("pyotp not installed. Run: pip install finstack-mcp[broker]")
        return None


_session_cache: dict = {}


def _get_session() -> Optional[dict]:
    """Authenticate with Angel One SmartAPI and return session tokens."""
    global _session_cache

    # Reuse token if fresh (< 6 hours old)
    if _session_cache.get("expires_at") and datetime.now().timestamp() < _session_cache["expires_at"]:
        return _session_cache

    api_key = os.getenv("ANGEL_API_KEY")
    client_id = os.getenv("ANGEL_CLIENT_ID")
    password = os.getenv("ANGEL_PASSWORD")
    totp = _get_totp()

    if not all([api_key, client_id, password]):
        return None

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00",
        "X-PrivateKey": api_key,
    }

    payload = {
        "clientcode": client_id,
        "password": password,
    }
    if totp:
        payload["totp"] = totp

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{SMARTAPI_BASE}/rest/auth/angelbroking/user/v1/loginByPassword",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") and data.get("data"):
                session = data["data"]
                _session_cache = {
                    "jwt_token": session.get("jwtToken"),
                    "refresh_token": session.get("refreshToken"),
                    "api_key": api_key,
                    "expires_at": datetime.now().timestamp() + 6 * 3600,
                }
                logger.info("Angel One session established successfully")
                return _session_cache
            else:
                logger.warning("Angel One login failed: %s", data.get("message"))
                return None

    except Exception as e:
        logger.warning("Angel One session error: %s", e)
        return None


def _get_headers(session: dict) -> dict:
    return {
        "Authorization": f"Bearer {session['jwt_token']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00",
        "X-PrivateKey": session["api_key"],
    }


def get_live_quote_angel(symbol: str) -> dict:
    """
    Real-time NSE quote via Angel One SmartAPI (zero delay).
    Falls back to yfinance if Angel One is not configured.
    """
    if not _is_configured():
        return {
            "configured": False,
            "message": "Angel One not configured. Set ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD in .env",
            "setup": "See: https://smartapi.angelbroking.com/ — your key stays local, never on GitHub",
        }

    session = _get_session()
    if not session:
        return {"error": "Angel One authentication failed. Check your credentials in .env"}

    sym_upper = symbol.upper().replace(".NS", "").replace(".BO", "")
    token = NSE_TOKEN_MAP.get(sym_upper)

    if not token:
        return {
            "error": f"Token not found for {sym_upper}. Angel One requires instrument tokens.",
            "tip": "Common indices/stocks are pre-mapped. For others, look up token on Angel One.",
        }

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{SMARTAPI_BASE}/rest/secure/angelbroking/market/v1/quote/",
                json={"mode": "FULL", "exchangeTokens": {"NSE": [token]}},
                headers=_get_headers(session),
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") and data.get("data"):
                fetched = data["data"].get("fetched", [])
                if fetched:
                    q = fetched[0]
                    ltp = q.get("ltp", 0)
                    prev_close = q.get("close", 0)
                    change = round(ltp - prev_close, 2) if prev_close else 0
                    change_pct = round(change / prev_close * 100, 2) if prev_close else 0

                    return clean_nan({
                        "symbol": sym_upper,
                        "ltp": ltp,
                        "open": q.get("open"),
                        "high": q.get("high"),
                        "low": q.get("low"),
                        "prev_close": prev_close,
                        "change": change,
                        "change_pct": change_pct,
                        "volume": q.get("tradeVolume"),
                        "avg_price": q.get("avgPrice"),
                        "lower_circuit": q.get("lowerCircuit"),
                        "upper_circuit": q.get("upperCircuit"),
                        "buy_qty": q.get("totBuyQuan"),
                        "sell_qty": q.get("totSellQuan"),
                        "52w_high": q.get("weekHighLow", {}).get("max"),
                        "52w_low": q.get("weekHighLow", {}).get("min"),
                        "data_source": "Angel One SmartAPI (real-time, zero delay)",
                        "timestamp": datetime.now().isoformat(),
                    })

            return {"error": "No data returned from Angel One", "raw": data.get("message")}

    except Exception as e:
        return {"error": f"Angel One quote failed: {e}"}


def get_market_depth_angel(symbol: str) -> dict:
    """
    Level 2 order book depth — top 5 bid/ask via Angel One SmartAPI.
    This is exchange-licensed data. Free only via broker API.
    Zerodha Kite Connect charges ₹500/month for this. Angel One SmartAPI is free.
    """
    if not _is_configured():
        return {
            "configured": False,
            "message": "Set ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD in .env for real-time depth",
        }

    session = _get_session()
    if not session:
        return {"error": "Angel One authentication failed"}

    sym_upper = symbol.upper().replace(".NS", "").replace(".BO", "")
    token = NSE_TOKEN_MAP.get(sym_upper)
    if not token:
        return {"error": f"Token not found for {sym_upper}"}

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{SMARTAPI_BASE}/rest/secure/angelbroking/market/v1/quote/",
                json={"mode": "FULL", "exchangeTokens": {"NSE": [token]}},
                headers=_get_headers(session),
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("data", {}).get("fetched"):
                q = data["data"]["fetched"][0]
                depth = q.get("depth", {})
                return clean_nan({
                    "symbol": sym_upper,
                    "ltp": q.get("ltp"),
                    "buy_depth": depth.get("buy", [])[:5],
                    "sell_depth": depth.get("sell", [])[:5],
                    "total_buy_qty": q.get("totBuyQuan"),
                    "total_sell_qty": q.get("totSellQuan"),
                    "data_source": "Angel One SmartAPI (Level 2 — real-time)",
                    "note": "Zerodha charges ₹500/mo for this. Angel One SmartAPI is free.",
                    "timestamp": datetime.now().isoformat(),
                })

            return {"error": "No depth data returned"}

    except Exception as e:
        return {"error": f"Market depth fetch failed: {e}"}


def broker_status() -> dict:
    """Return Angel One broker integration status."""
    configured = _is_configured()
    has_totp = bool(os.getenv("ANGEL_TOTP_SECRET"))

    return {
        "angel_one_configured": configured,
        "totp_configured": has_totp,
        "pyotp_available": _check_pyotp(),
        "status": "ready" if configured else "not_configured",
        "setup_instructions": {
            "step1": "Create API key at https://smartapi.angelbroking.com/",
            "step2": "Add to your .env file:",
            "env_vars": {
                "ANGEL_API_KEY": "your_api_key_from_angelbroking",
                "ANGEL_CLIENT_ID": "your_client_id (e.g. R1234567)",
                "ANGEL_PASSWORD": "your_4_digit_pin",
                "ANGEL_TOTP_SECRET": "your_totp_secret (optional but recommended)",
            },
            "step3": "pip install finstack-mcp[broker]",
            "security_note": ".env is in .gitignore — your key is NEVER pushed to GitHub",
        },
    }


def _check_pyotp() -> bool:
    try:
        import pyotp  # noqa: F401
        return True
    except ImportError:
        return False
