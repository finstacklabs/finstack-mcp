"""
FinStack Broker Integration — Dhan API v2

Real-time (zero-delay) NSE/BSE market data via Dhan API.
Free for Dhan account holders. No OAuth dance — uses a long-lived access token.

Setup (one-time):
    1. Login to https://web.dhan.co → My Profile → API → Generate Access Token
    2. Add to your .env file:
        DHAN_ACCESS_TOKEN=your_access_token
        DHAN_CLIENT_ID=your_client_id
    3. pip install finstack-mcp[broker]

Dhan access tokens are valid for 30 days (much easier than Upstox daily refresh).

Dhan API docs: https://dhanhq.co/docs/latest/

Without these env vars, falls back to yfinance (15-min delay).
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx

from finstack.utils.helpers import clean_nan

logger = logging.getLogger("finstack.data.broker_dhan")

DHAN_BASE = "https://api.dhan.co/v2"

# ── Dhan uses numeric security IDs. Common NSE symbols ──
# These are Dhan's internal scrip codes for NSE Equity segment
NSE_SECURITY_MAP = {
    "RELIANCE":   "2885",
    "TCS":        "11536",
    "HDFCBANK":   "1333",
    "INFY":       "1594",
    "ICICIBANK":  "4963",
    "SBIN":       "3045",
    "WIPRO":      "3787",
    "AXISBANK":   "5900",
    "KOTAKBANK":  "1922",
    "BHARTIARTL": "10604",
    "ITC":        "1660",
    "HINDUNILVR": "1394",
    "BAJFINANCE": "317",
    "MARUTI":     "10999",
    "TITAN":      "3506",
    "ADANIENT":   "25",
    "ADANIPORTS": "15083",
    "POWERGRID":  "14977",
    "NTPC":       "11630",
    "ONGC":       "2475",
    "LT":         "11483",
    "SUNPHARMA":  "3351",
    "ULTRACEMCO": "11532",
    "ASIANPAINT": "236",
    "NESTLEIND":  "17963",
    # Indices use different exchange segment
    "NIFTY":      "13",
    "BANKNIFTY":  "25",
    "SENSEX":     "1",
}

# Dhan segment codes
SEGMENT_NSE_EQ  = "NSE_EQ"
SEGMENT_NSE_IDX = "IDX_I"

# Dhan chart resolution strings
DHAN_INTERVAL_MAP = {
    "1m":  "1",
    "5m":  "5",
    "15m": "15",
    "25m": "25",
    "60m": "60",
    "1h":  "60",
    "1d":  "D",
    "1wk": "W",
    "1mo": "M",
}


def _is_configured() -> bool:
    return bool(os.getenv("DHAN_ACCESS_TOKEN") and os.getenv("DHAN_CLIENT_ID"))


def _get_headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('DHAN_ACCESS_TOKEN', '')}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_live_quote_dhan(symbol: str) -> dict:
    """Real-time NSE quote via Dhan API v2 (zero delay)."""
    if not _is_configured():
        return {
            "configured": False,
            "message": "Dhan not configured. Set DHAN_ACCESS_TOKEN and DHAN_CLIENT_ID in .env",
            "setup": "Login to web.dhan.co → My Profile → API → Generate token (valid 30 days)",
        }

    sym = symbol.upper().replace(".NS", "").replace(".BO", "")
    security_id = NSE_SECURITY_MAP.get(sym)
    if not security_id:
        return {
            "error": f"Security ID not found for {sym}.",
            "tip": "Common Nifty50 stocks are pre-mapped. Add others to NSE_SECURITY_MAP in broker_dhan.py",
        }

    is_index = sym in ("NIFTY", "BANKNIFTY", "SENSEX")
    exchange_segment = SEGMENT_NSE_IDX if is_index else SEGMENT_NSE_EQ

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{DHAN_BASE}/marketfeed/quote",
                json={
                    "NSE_EQ": [security_id] if not is_index else [],
                    "IDX_I":  [security_id] if is_index else [],
                },
                headers=_get_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

            # Dhan returns data under the segment key
            segment_data = data.get("data", {}).get(exchange_segment, [])
            if segment_data:
                q = segment_data[0]
                ltp = q.get("last_price", 0)
                prev_close = q.get("prev_close", 0)
                change = round(ltp - prev_close, 2) if prev_close else 0
                change_pct = round(change / prev_close * 100, 2) if prev_close else 0

                return clean_nan({
                    "symbol":       sym,
                    "ltp":          ltp,
                    "open":         q.get("open_price"),
                    "high":         q.get("high_price"),
                    "low":          q.get("low_price"),
                    "prev_close":   prev_close,
                    "change":       change,
                    "change_pct":   change_pct,
                    "volume":       q.get("volume"),
                    "avg_price":    q.get("average_price"),
                    "lower_circuit":q.get("lower_ckt"),
                    "upper_circuit":q.get("upper_ckt"),
                    "buy_qty":      q.get("buy_quantity"),
                    "sell_qty":     q.get("sell_quantity"),
                    "52w_high":     q.get("wk52_high"),
                    "52w_low":      q.get("wk52_low"),
                    "data_source":  "Dhan API v2 (real-time, zero delay)",
                    "timestamp":    datetime.now().isoformat(),
                })

            return {"error": "No data from Dhan", "raw": data}

    except Exception as e:
        return {"error": f"Dhan quote failed: {e}"}


def get_candle_data_dhan(symbol: str, interval: str = "1d", from_date: str = None, to_date: str = None) -> dict:
    """
    Historical OHLCV candle data via Dhan API v2.
    Zero delay for intraday. Returns LightweightCharts-compatible format.

    interval: 1m, 5m, 15m, 25m, 60m/1h, 1d, 1wk, 1mo
    from_date / to_date: "YYYY-MM-DD"
    """
    if not _is_configured():
        return {"configured": False, "message": "Dhan not configured"}

    sym = symbol.upper().replace(".NS", "").replace(".BO", "")
    security_id = NSE_SECURITY_MAP.get(sym)
    if not security_id:
        return {"error": f"Security ID not found for {sym}. Add it to NSE_SECURITY_MAP in broker_dhan.py"}

    dhan_interval = DHAN_INTERVAL_MAP.get(interval.lower(), "D")
    is_intraday = dhan_interval not in ("D", "W", "M")

    now = datetime.now()
    if to_date is None:
        to_date = now.strftime("%Y-%m-%d")
    if from_date is None:
        days_map = {
            "1": 3, "5": 5, "15": 10, "25": 15,
            "60": 30, "D": 365, "W": 730, "M": 1825,
        }
        from_date = (now - timedelta(days=days_map.get(dhan_interval, 30))).strftime("%Y-%m-%d")

    is_index = sym in ("NIFTY", "BANKNIFTY", "SENSEX")
    exchange_segment = SEGMENT_NSE_IDX if is_index else SEGMENT_NSE_EQ
    instrument_type = "INDEX" if is_index else "EQUITY"

    endpoint = (
        f"{DHAN_BASE}/charts/intraday"
        if is_intraday
        else f"{DHAN_BASE}/charts/historical"
    )

    payload = {
        "securityId":   security_id,
        "exchangeSegment": exchange_segment,
        "instrument":   instrument_type,
        "interval":     dhan_interval,
        "fromDate":     from_date,
        "toDate":       to_date,
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(endpoint, json=payload, headers=_get_headers())
            resp.raise_for_status()
            data = resp.json()

            # Dhan returns open[], high[], low[], close[], volume[], timestamp[]
            opens  = data.get("open",      [])
            highs  = data.get("high",      [])
            lows   = data.get("low",       [])
            closes = data.get("close",     [])
            vols   = data.get("volume",    [])
            times  = data.get("timestamp", data.get("start_Time", []))

            if not closes:
                return {"error": "No candle data from Dhan", "raw": data.get("remarks", "")}

            records = []
            for i in range(len(closes)):
                try:
                    ts = times[i] if i < len(times) else None
                    if ts is None:
                        continue
                    if is_intraday:
                        time_val = int(ts)
                    else:
                        dt = datetime.fromtimestamp(int(ts))
                        time_val = dt.strftime("%Y-%m-%d")
                    records.append({
                        "date":   time_val,
                        "open":   round(float(opens[i]),  2),
                        "high":   round(float(highs[i]),  2),
                        "low":    round(float(lows[i]),   2),
                        "close":  round(float(closes[i]), 2),
                        "volume": int(vols[i]) if i < len(vols) else 0,
                    })
                except Exception:
                    continue

            return clean_nan({
                "symbol":      sym,
                "exchange":    "NSE",
                "interval":    interval,
                "data_points": len(records),
                "data":        records,
                "data_source": "Dhan API v2 (zero delay)",
            })

    except Exception as e:
        return {"error": f"Dhan candle fetch failed: {e}"}


def broker_status_dhan() -> dict:
    configured = _is_configured()
    return {
        "dhan_configured": configured,
        "access_token_set": bool(os.getenv("DHAN_ACCESS_TOKEN")),
        "client_id_set":    bool(os.getenv("DHAN_CLIENT_ID")),
        "status": "ready" if configured else "not_configured",
        "note": "Dhan access tokens are valid for 30 days (much easier than Upstox daily refresh).",
        "setup_instructions": {
            "step1": "Login to https://web.dhan.co → My Profile → API → Generate Access Token",
            "step2": "Add to .env:",
            "env_vars": {
                "DHAN_ACCESS_TOKEN": "your_access_token (valid 30 days)",
                "DHAN_CLIENT_ID":    "your_client_id",
            },
            "step3": "pip install finstack-mcp[broker]",
            "docs": "https://dhanhq.co/docs/latest/",
        },
    }
