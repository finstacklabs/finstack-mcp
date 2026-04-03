"""
ICICI Breeze API integration for FinStack MCP.

Setup:
    pip install breeze-connect
    Add to .env:
        ICICI_API_KEY=your_api_key
        ICICI_API_SECRET=your_api_secret
        ICICI_SESSION_TOKEN=your_session_token   # refresh daily from app

Get credentials: https://api.icicidirect.com/
Session token: Login to ICICIdirect app → My Account → Generate API Session
"""
import os
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("finstack.icici")

# ICICI uses stock codes, not NSE symbols
# Common stock codes (NSE symbol → ICICI stock code)
ICICI_STOCK_CODES = {
    "RELIANCE":  "RELIST",
    "TCS":       "TCS",
    "HDFCBANK":  "HDFBAN",
    "INFY":      "INFTEC",
    "ICICIBANK": "ICICIB",
    "SBIN":      "STABAN",
    "WIPRO":     "WIPRO",
    "AXISBANK":  "AXIBAN",
    "MARUTI":    "MARUTI",
    "TITAN":     "TITAN",
    "BAJFINANCE": "BAJFI",
    "LT":        "LARTOU",
    "HDFC":      "HDFCLT",
    "KOTAKBANK": "KOTMAH",
    "ASIANPAINT": "ASIPAI",
}


def _is_configured() -> bool:
    return bool(
        os.getenv("ICICI_API_KEY") and
        os.getenv("ICICI_API_SECRET") and
        os.getenv("ICICI_SESSION_TOKEN")
    )


def _get_client():
    """Return authenticated Breeze client."""
    try:
        from breeze_connect import BreezeConnect
    except ImportError:
        raise ImportError("Run: pip install breeze-connect")

    breeze = BreezeConnect(api_key=os.getenv("ICICI_API_KEY", ""))
    breeze.generate_session(
        api_secret=os.getenv("ICICI_API_SECRET", ""),
        session_token=os.getenv("ICICI_SESSION_TOKEN", "")
    )
    return breeze


def get_live_quote_icici(symbol: str) -> dict:
    """Real-time NSE quote via ICICI Breeze API."""
    if not _is_configured():
        return {"error": "ICICI Breeze not configured. Add ICICI_API_KEY, ICICI_API_SECRET, ICICI_SESSION_TOKEN to .env"}

    try:
        breeze = _get_client()
        stock_code = ICICI_STOCK_CODES.get(symbol.upper(), symbol.upper())

        response = breeze.get_quotes(
            stock_code=stock_code,
            exchange_code="NSE",
            product_type="cash",
            expiry_date="",
            right="",
            strike_price="",
        )

        if not response or "Success" not in response.get("Status", ""):
            return {"error": f"ICICI Breeze error: {response.get('Error', 'Unknown')}"}

        d = response["Success"][0]
        ltp   = float(d.get("ltp", 0) or 0)
        prev  = float(d.get("close", 0) or 0)
        change = round(ltp - prev, 2)
        change_pct = round((change / prev * 100) if prev else 0, 2)

        return {
            "symbol": symbol.upper(),
            "ltp": ltp,
            "open": float(d.get("open", 0) or 0),
            "high": float(d.get("high", 0) or 0),
            "low":  float(d.get("low", 0) or 0),
            "prev_close": prev,
            "volume": int(d.get("total_quantity_traded", 0) or 0),
            "change": change,
            "change_pct": change_pct,
            "source": "icici_breeze",
        }
    except Exception as e:
        logger.error("ICICI quote error: %s", e)
        return {"error": str(e)}


def get_candle_data_icici(symbol: str, interval: str = "1day", days: int = 30) -> dict:
    """Historical OHLCV candles from ICICI Breeze.

    interval options: "1minute", "5minute", "30minute", "1day"
    """
    if not _is_configured():
        return {"error": "ICICI Breeze not configured"}

    INTERVAL_MAP = {
        "1m": "1minute", "5m": "5minute", "15m": "15minute",
        "30m": "30minute", "1h": "1hour",
        "1d": "1day", "1D": "1day",
    }
    breeze_interval = INTERVAL_MAP.get(interval, "1day")

    try:
        breeze = _get_client()
        stock_code = ICICI_STOCK_CODES.get(symbol.upper(), symbol.upper())

        to_date   = datetime.today()
        from_date = to_date - timedelta(days=days)

        response = breeze.get_historical_data(
            interval=breeze_interval,
            from_date=from_date.strftime("%Y-%m-%dT07:00:00.000Z"),
            to_date=to_date.strftime("%Y-%m-%dT07:00:00.000Z"),
            stock_code=stock_code,
            exchange_code="NSE",
            product_type="cash",
        )

        if not response or response.get("Status") != "Success":
            return {"error": f"ICICI history error: {response.get('Error', 'Unknown')}"}

        candles = []
        for c in response.get("Success", []):
            candles.append({
                "date":   c.get("datetime", "")[:10],
                "open":   float(c.get("open", 0) or 0),
                "high":   float(c.get("high", 0) or 0),
                "low":    float(c.get("low", 0) or 0),
                "close":  float(c.get("close", 0) or 0),
                "volume": int(c.get("volume", 0) or 0),
            })

        return {"symbol": symbol.upper(), "interval": interval, "data": candles, "source": "icici_breeze"}
    except Exception as e:
        logger.error("ICICI candle error: %s", e)
        return {"error": str(e)}


def broker_status_icici() -> dict:
    """Check ICICI Breeze configuration status."""
    configured = _is_configured()
    return {
        "broker": "ICICI Breeze",
        "configured": configured,
        "api_key_set": bool(os.getenv("ICICI_API_KEY")),
        "api_secret_set": bool(os.getenv("ICICI_API_SECRET")),
        "session_token_set": bool(os.getenv("ICICI_SESSION_TOKEN")),
        "status": "ready" if configured else "not_configured",
        "setup_instructions": (
            "1. Get API key from https://api.icicidirect.com/\n"
            "2. Each morning: ICICIdirect app → My Account → Generate API Session\n"
            "3. Copy session token to .env:\n"
            "   ICICI_API_KEY=your_api_key\n"
            "   ICICI_API_SECRET=your_api_secret\n"
            "   ICICI_SESSION_TOKEN=your_session_token\n"
            "4. pip install breeze-connect"
        ) if not configured else "ICICI Breeze is configured and ready.",
        "note": "Session token must be refreshed daily from the ICICIdirect mobile app.",
    }
