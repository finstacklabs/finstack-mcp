"""
Fyers API v3 integration for FinStack MCP.

Setup:
    pip install fyers-apiv3
    Add to .env:
        FYERS_APP_ID=your_app_id          # from myapi.fyers.in
        FYERS_ACCESS_TOKEN=your_token     # generated via OAuth flow
        FYERS_CLIENT_ID=your_client_id

Get credentials: https://myapi.fyers.in/
"""
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("finstack.fyers")

# NSE symbol format for Fyers: "NSE:RELIANCE-EQ"
def _fyers_symbol(symbol: str) -> str:
    s = symbol.upper().replace(".NS", "").replace(".BO", "")
    return f"NSE:{s}-EQ"

def _fyers_index(symbol: str) -> str:
    INDEX_MAP = {
        "NIFTY50": "NSE:NIFTY50-INDEX",
        "BANKNIFTY": "NSE:NIFTYBANK-INDEX",
        "SENSEX": "BSE:SENSEX-INDEX",
    }
    return INDEX_MAP.get(symbol.upper(), f"NSE:{symbol.upper()}-INDEX")

def _is_configured() -> bool:
    return bool(os.getenv("FYERS_APP_ID") and os.getenv("FYERS_ACCESS_TOKEN"))

def _get_client():
    """Return authenticated Fyers client."""
    try:
        from fyers_apiv3 import fyersModel
    except ImportError:
        raise ImportError("Run: pip install fyers-apiv3")

    app_id      = os.getenv("FYERS_APP_ID", "")
    access_token = os.getenv("FYERS_ACCESS_TOKEN", "")
    client_id   = os.getenv("FYERS_CLIENT_ID", "")

    token = f"{client_id}:{access_token}" if client_id else access_token

    fyers = fyersModel.FyersModel(
        client_id=app_id,
        is_async=False,
        token=token,
        log_path=""
    )
    return fyers


def get_live_quote_fyers(symbol: str) -> dict:
    """Real-time NSE quote via Fyers API v3."""
    if not _is_configured():
        return {"error": "Fyers not configured. Add FYERS_APP_ID and FYERS_ACCESS_TOKEN to .env"}

    try:
        fyers = _get_client()
        data = {"symbols": _fyers_symbol(symbol)}
        response = fyers.quotes(data=data)

        if response.get("s") != "ok":
            return {"error": f"Fyers API error: {response.get('message', 'Unknown')}"}

        q = response["d"][0]["v"]
        return {
            "symbol": symbol.upper(),
            "ltp": q.get("lp", 0),
            "open": q.get("open_price", 0),
            "high": q.get("high_price", 0),
            "low": q.get("low_price", 0),
            "close": q.get("prev_close_price", 0),
            "volume": q.get("volume", 0),
            "change": q.get("ch", 0),
            "change_pct": q.get("chp", 0),
            "52w_high": q.get("52w_high", 0),
            "52w_low": q.get("52w_low", 0),
            "source": "fyers",
        }
    except Exception as e:
        logger.error("Fyers quote error: %s", e)
        return {"error": str(e)}


def get_candle_data_fyers(symbol: str, interval: str = "D", days: int = 30) -> dict:
    """Historical OHLCV candles from Fyers.

    interval options: "1", "2", "3", "5", "10", "15", "20", "30", "60", "120", "240", "D", "W", "M"
    """
    if not _is_configured():
        return {"error": "Fyers not configured"}

    INTERVAL_MAP = {
        "1m": "1", "3m": "3", "5m": "5", "10m": "10", "15m": "15",
        "30m": "30", "1h": "60", "2h": "120", "4h": "240",
        "1d": "D", "1D": "D", "1w": "W", "1mo": "M",
    }
    fyers_interval = INTERVAL_MAP.get(interval, interval)

    try:
        fyers = _get_client()
        date_format = "%Y-%m-%d"
        to_date   = datetime.today().strftime(date_format)
        from_date = (datetime.today() - timedelta(days=days)).strftime(date_format)

        data = {
            "symbol": _fyers_symbol(symbol),
            "resolution": fyers_interval,
            "date_format": "1",
            "range_from": from_date,
            "range_to": to_date,
            "cont_flag": "1",
        }
        response = fyers.history(data=data)

        if response.get("s") != "ok":
            return {"error": f"Fyers history error: {response.get('message', 'Unknown')}"}

        candles = []
        for c in response.get("candles", []):
            ts, o, h, low, close, vol = c
            dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            candles.append({"date": dt, "open": o, "high": h, "low": low, "close": close, "volume": vol})

        return {"symbol": symbol.upper(), "interval": interval, "data": candles, "source": "fyers"}
    except Exception as e:
        logger.error("Fyers candle error: %s", e)
        return {"error": str(e)}


def broker_status_fyers() -> dict:
    """Check Fyers API configuration status."""
    configured = _is_configured()
    return {
        "broker": "Fyers",
        "configured": configured,
        "app_id_set": bool(os.getenv("FYERS_APP_ID")),
        "access_token_set": bool(os.getenv("FYERS_ACCESS_TOKEN")),
        "status": "ready" if configured else "not_configured",
        "setup_instructions": (
            "1. Create app at https://myapi.fyers.in/\n"
            "2. Complete OAuth flow to get access token\n"
            "3. Add to .env:\n"
            "   FYERS_APP_ID=your_app_id\n"
            "   FYERS_ACCESS_TOKEN=your_token\n"
            "   FYERS_CLIENT_ID=your_client_id\n"
            "4. pip install fyers-apiv3"
        ) if not configured else "Fyers API is configured and ready.",
        "note": "Access token expires daily. Re-run OAuth flow each morning or automate with TOTP.",
    }
