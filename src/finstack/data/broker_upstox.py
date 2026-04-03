"""
FinStack Broker Integration — Upstox API v2

Real-time (zero-delay) NSE/BSE market data via Upstox API.
Free for Upstox account holders. Requires one-time OAuth setup.

Setup (one-time):
    1. Create an app at https://developer.upstox.com/ → "Create App"
       - Redirect URI: https://localhost:5555/ (or any URL you control)
    2. Add to your .env file:
        UPSTOX_API_KEY=your_api_key
        UPSTOX_API_SECRET=your_api_secret
        UPSTOX_ACCESS_TOKEN=your_access_token  (refresh daily or use OAuth flow)
    3. pip install finstack-mcp[broker]

How to get access_token (daily step):
    Run: python -m finstack.brokers.upstox_auth
    OR paste this URL in browser, log in, copy the `code` param from redirect URL:
    https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=YOUR_KEY&redirect_uri=https://localhost:5555/

Upstox API docs: https://upstox.com/developer/api-documentation/

Without these env vars, falls back to yfinance (15-min delay).
"""

import os
import logging
from datetime import datetime, timedelta

import httpx

from finstack.utils.helpers import clean_nan

logger = logging.getLogger("finstack.data.broker_upstox")

UPSTOX_BASE = "https://api.upstox.com/v2"

# ── Upstox uses ISIN-based instrument keys. Common NSE symbols ──
# Format: NSE_EQ|<ISIN>  for equities, NSE_INDEX|<name> for indices
NSE_INSTRUMENT_MAP = {
    "NIFTY":      "NSE_INDEX|Nifty 50",
    "BANKNIFTY":  "NSE_INDEX|Nifty Bank",
    "FINNIFTY":   "NSE_INDEX|Nifty Fin Service",
    "MIDCPNIFTY": "NSE_INDEX|NIFTY MID SELECT",
    "SENSEX":     "BSE_INDEX|SENSEX",
    "RELIANCE":   "NSE_EQ|INE002A01018",
    "TCS":        "NSE_EQ|INE467B01029",
    "HDFCBANK":   "NSE_EQ|INE040A01034",
    "INFY":       "NSE_EQ|INE009A01021",
    "ICICIBANK":  "NSE_EQ|INE090A01021",
    "SBIN":       "NSE_EQ|INE062A01020",
    "WIPRO":      "NSE_EQ|INE075A01022",
    "AXISBANK":   "NSE_EQ|INE238A01034",
    "KOTAKBANK":  "NSE_EQ|INE237A01028",
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "ITC":        "NSE_EQ|INE154A01025",
    "HINDUNILVR": "NSE_EQ|INE030A01027",
    "BAJFINANCE": "NSE_EQ|INE296A01024",
    "MARUTI":     "NSE_EQ|INE585B01010",
    "TITAN":      "NSE_EQ|INE280A01028",
    "ADANIENT":   "NSE_EQ|INE423A01024",
    "ADANIPORTS": "NSE_EQ|INE742F01042",
    "POWERGRID":  "NSE_EQ|INE752E01010",
    "NTPC":       "NSE_EQ|INE733E01010",
    "ONGC":       "NSE_EQ|INE213A01029",
    "LT":         "NSE_EQ|INE018A01030",
    "SUNPHARMA":  "NSE_EQ|INE044A01036",
    "ULTRACEMCO": "NSE_EQ|INE481G01011",
    "ASIANPAINT": "NSE_EQ|INE021A01026",
    "NESTLEIND":  "NSE_EQ|INE239A01016",
}

# Upstox interval names for historical candles
INTERVAL_MAP = {
    "1m":   "1minute",
    "3m":   "3minute",
    "5m":   "5minute",
    "10m":  "10minute",
    "15m":  "15minute",
    "30m":  "30minute",
    "60m":  "60minute",
    "1h":   "60minute",
    "1d":   "day",
    "1wk":  "week",
    "1mo":  "month",
}


def _is_configured() -> bool:
    return bool(os.getenv("UPSTOX_API_KEY") and os.getenv("UPSTOX_ACCESS_TOKEN"))


def _get_headers() -> dict:
    token = os.getenv("UPSTOX_ACCESS_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Api-Version": "2.0",
    }


def get_live_quote_upstox(symbol: str) -> dict:
    """Real-time NSE quote via Upstox API v2 (zero delay)."""
    if not _is_configured():
        return {
            "configured": False,
            "message": "Upstox not configured. Set UPSTOX_API_KEY and UPSTOX_ACCESS_TOKEN in .env",
            "setup": "Create app at https://developer.upstox.com/ — stays local, never on GitHub",
        }

    sym = symbol.upper().replace(".NS", "").replace(".BO", "")
    instrument_key = NSE_INSTRUMENT_MAP.get(sym)
    if not instrument_key:
        return {
            "error": f"Instrument key not found for {sym}.",
            "tip": "Common Nifty50 stocks are pre-mapped. For others, use the Upstox instrument search.",
        }

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{UPSTOX_BASE}/market-quote/quotes",
                params={"instrument_key": instrument_key},
                headers=_get_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "success" and data.get("data"):
                q = list(data["data"].values())[0]
                ohlc = q.get("ohlc", {})
                ltp = q.get("last_price", 0)
                prev_close = ohlc.get("close", 0)
                change = round(ltp - prev_close, 2) if prev_close else 0
                change_pct = round(change / prev_close * 100, 2) if prev_close else 0

                return clean_nan({
                    "symbol": sym,
                    "ltp": ltp,
                    "open": ohlc.get("open"),
                    "high": ohlc.get("high"),
                    "low": ohlc.get("low"),
                    "prev_close": prev_close,
                    "change": change,
                    "change_pct": change_pct,
                    "volume": q.get("volume"),
                    "avg_price": q.get("average_price"),
                    "lower_circuit": q.get("lower_circuit_limit"),
                    "upper_circuit": q.get("upper_circuit_limit"),
                    "buy_qty": q.get("total_buy_quantity"),
                    "sell_qty": q.get("total_sell_quantity"),
                    "52w_high": q.get("52_week_high"),
                    "52w_low": q.get("52_week_low"),
                    "data_source": "Upstox API v2 (real-time, zero delay)",
                    "timestamp": datetime.now().isoformat(),
                })

            return {"error": "No data from Upstox", "raw": data.get("errors")}

    except Exception as e:
        return {"error": f"Upstox quote failed: {e}"}


def get_market_depth_upstox(symbol: str) -> dict:
    """Level 2 order book depth via Upstox API v2 — top 5 bid/ask."""
    if not _is_configured():
        return {"configured": False, "message": "Set UPSTOX_API_KEY and UPSTOX_ACCESS_TOKEN in .env"}

    sym = symbol.upper().replace(".NS", "").replace(".BO", "")
    instrument_key = NSE_INSTRUMENT_MAP.get(sym)
    if not instrument_key:
        return {"error": f"Instrument key not found for {sym}"}

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{UPSTOX_BASE}/market-quote/quotes",
                params={"instrument_key": instrument_key},
                headers=_get_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "success" and data.get("data"):
                q = list(data["data"].values())[0]
                depth = q.get("depth", {})
                return clean_nan({
                    "symbol": sym,
                    "ltp": q.get("last_price"),
                    "buy_depth": depth.get("buy", [])[:5],
                    "sell_depth": depth.get("sell", [])[:5],
                    "total_buy_qty": q.get("total_buy_quantity"),
                    "total_sell_qty": q.get("total_sell_quantity"),
                    "data_source": "Upstox API v2 (Level 2 — real-time)",
                    "timestamp": datetime.now().isoformat(),
                })

            return {"error": "No depth data from Upstox"}

    except Exception as e:
        return {"error": f"Upstox depth failed: {e}"}


def get_candle_data_upstox(symbol: str, interval: str = "1d", from_date: str = None, to_date: str = None) -> dict:
    """
    Historical OHLCV candle data via Upstox API v2.
    Zero delay for intraday. Returns data in LightweightCharts-compatible format.

    interval: 1m, 3m, 5m, 10m, 15m, 30m, 60m/1h, 1d, 1wk, 1mo
    from_date / to_date: "YYYY-MM-DD"
    """
    if not _is_configured():
        return {"configured": False, "message": "Upstox not configured"}

    sym = symbol.upper().replace(".NS", "").replace(".BO", "")
    instrument_key = NSE_INSTRUMENT_MAP.get(sym)
    if not instrument_key:
        return {"error": f"Instrument key not found for {sym}. Add it to NSE_INSTRUMENT_MAP in broker_upstox.py"}

    upstox_interval = INTERVAL_MAP.get(interval.lower(), "day")
    is_intraday = interval.lower() not in ("1d", "1wk", "1mo", "day", "week", "month")

    now = datetime.now()
    if to_date is None:
        to_date = now.strftime("%Y-%m-%d")
    if from_date is None:
        days_back_map = {
            "1minute": 3, "3minute": 5, "5minute": 5, "10minute": 10,
            "15minute": 10, "30minute": 15, "60minute": 30,
            "day": 365, "week": 730, "month": 1825,
        }
        days_back = days_back_map.get(upstox_interval, 30)
        from_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")

    # Upstox intraday vs historical use different endpoints
    endpoint = (
        f"{UPSTOX_BASE}/historical-candle/intraday/{instrument_key}/{upstox_interval}"
        if is_intraday
        else f"{UPSTOX_BASE}/historical-candle/{instrument_key}/{upstox_interval}/{to_date}/{from_date}"
    )

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(endpoint, headers=_get_headers())
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "success" and data.get("data", {}).get("candles"):
                candles = data["data"]["candles"]
                records = []
                for c in candles:
                    # Upstox: [timestamp, open, high, low, close, volume, oi]
                    if len(c) < 6:
                        continue
                    ts, o, h, low, cl, vol = c[0], c[1], c[2], c[3], c[4], c[5]
                    try:
                        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                        if not is_intraday:
                            time_val = dt.strftime("%Y-%m-%d")
                        else:
                            time_val = int(dt.timestamp())
                    except Exception:
                        time_val = str(ts)
                    records.append({
                        "date":   time_val,
                        "open":   round(float(o),  2),
                        "high":   round(float(h),  2),
                        "low":    round(float(low),  2),
                        "close":  round(float(cl), 2),
                        "volume": int(vol),
                    })

                return clean_nan({
                    "symbol":      sym,
                    "exchange":    "NSE",
                    "interval":    interval,
                    "data_points": len(records),
                    "data":        records,
                    "data_source": "Upstox API v2 (zero delay)",
                })

            return {"error": "No candle data from Upstox", "raw": data.get("errors", "")}

    except Exception as e:
        return {"error": f"Upstox candle fetch failed: {e}"}


def broker_status_upstox() -> dict:
    configured = _is_configured()
    has_secret = bool(os.getenv("UPSTOX_API_SECRET"))
    return {
        "upstox_configured": configured,
        "access_token_set": bool(os.getenv("UPSTOX_ACCESS_TOKEN")),
        "api_secret_set": has_secret,
        "status": "ready" if configured else "not_configured",
        "note": "Upstox access token expires daily — re-run OAuth flow each day or use a token refresh script.",
        "setup_instructions": {
            "step1": "Create app at https://developer.upstox.com/ (free for account holders)",
            "step2": "Add to .env:",
            "env_vars": {
                "UPSTOX_API_KEY":      "your_api_key",
                "UPSTOX_API_SECRET":   "your_api_secret",
                "UPSTOX_ACCESS_TOKEN": "your_daily_access_token",
            },
            "step3": "pip install finstack-mcp[broker]",
            "docs": "https://upstox.com/developer/api-documentation/",
        },
    }
