"""
FinStack NSE Data Fetcher

Fetches Indian stock market data from multiple free sources:
1. yfinance (primary) - .NS suffix for NSE, .BO for BSE
2. Direct NSE JSON endpoints (supplementary) - for live market data
3. Fallback mechanisms for reliability

All methods return clean dicts ready for MCP tool responses.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
import yfinance as yf
import pandas as pd

from finstack.utils.cache import cached, quotes_cache, fundamentals_cache, historical_cache
from finstack.utils.helpers import (
    validate_symbol, to_nse_symbol, to_bse_symbol,
    validate_period, validate_interval,
    clean_nan, safe_get, format_market_cap, format_percentage,
)

logger = logging.getLogger("finstack.data.nse")

# NSE direct endpoints (no auth needed, but may rate-limit)
NSE_BASE = "https://www.nseindia.com"
NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

# Index symbol mappings
INDEX_MAP = {
    "NIFTY": "^NSEI",
    "NIFTY50": "^NSEI",
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANKNIFTY": "^NSEBANK",
    "BANK NIFTY": "^NSEBANK",
    "NIFTYIT": "^CNXIT",
    "NIFTY IT": "^CNXIT",
    "NIFTYPHARMA": "^CNXPHARMA",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTYFMCG": "^CNXFMCG",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY REALTY": "^CNXREALTY",
    "NIFTY ENERGY": "^CNXENERGY",
}


def _resolve_index(name: str) -> str:
    """Resolve an index name to its Yahoo Finance symbol."""
    return INDEX_MAP.get(name.upper().strip(), name)


# ===== QUOTE DATA =====

@cached(quotes_cache, ttl=300)
def get_nse_quote(symbol: str) -> dict:
    """
    Get real-time NSE quote for a stock.

    Returns:
        dict with keys: symbol, name, price, change, change_pct, open, high, low,
        prev_close, volume, avg_volume, market_cap, fifty_two_week_high,
        fifty_two_week_low, pe_ratio, pb_ratio, dividend_yield, sector, industry
    """
    symbol = validate_symbol(symbol)
    yf_symbol = to_nse_symbol(symbol)

    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            # Try without .NS suffix (might already be correct)
            if not yf_symbol.endswith(".NS"):
                yf_symbol = f"{symbol}.NS"
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            return {
                "error": True,
                "message": f"No data found for '{symbol}'. Check if the symbol is correct.",
                "suggestion": "Use NSE symbols like RELIANCE, TCS, INFY, HDFCBANK"
            }

        result = {
            "symbol": symbol.replace(".NS", ""),
            "exchange": "NSE",
            "name": safe_get(info, "longName") or safe_get(info, "shortName", default=symbol),
            "price": safe_get(info, "regularMarketPrice"),
            "change": safe_get(info, "regularMarketChange"),
            "change_pct": safe_get(info, "regularMarketChangePercent"),
            "currency": safe_get(info, "currency", default="INR"),
            "open": safe_get(info, "regularMarketOpen"),
            "high": safe_get(info, "regularMarketDayHigh"),
            "low": safe_get(info, "regularMarketDayLow"),
            "prev_close": safe_get(info, "regularMarketPreviousClose"),
            "volume": safe_get(info, "regularMarketVolume"),
            "avg_volume": safe_get(info, "averageDailyVolume10Day"),
            "market_cap": safe_get(info, "marketCap"),
            "market_cap_formatted": format_market_cap(safe_get(info, "marketCap")),
            "fifty_two_week_high": safe_get(info, "fiftyTwoWeekHigh"),
            "fifty_two_week_low": safe_get(info, "fiftyTwoWeekLow"),
            "pe_ratio": safe_get(info, "trailingPE"),
            "forward_pe": safe_get(info, "forwardPE"),
            "pb_ratio": safe_get(info, "priceToBook"),
            "dividend_yield": safe_get(info, "dividendYield"),
            "dividend_yield_pct": format_percentage(
                (safe_get(info, "dividendYield") or 0) * 100
            ),
            "sector": safe_get(info, "sector"),
            "industry": safe_get(info, "industry"),
            "timestamp": datetime.now().isoformat(),
        }

        return clean_nan(result)

    except Exception as e:
        logger.error(f"Error fetching NSE quote for {symbol}: {e}")
        return {
            "error": True,
            "message": f"Failed to fetch data for '{symbol}': {str(e)}",
            "suggestion": "Try again in a moment. NSE data may be temporarily unavailable."
        }


@cached(quotes_cache, ttl=300)
def get_bse_quote(symbol: str) -> dict:
    """Get real-time BSE quote for a stock."""
    symbol = validate_symbol(symbol)
    yf_symbol = to_bse_symbol(symbol)

    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            return {
                "error": True,
                "message": f"No BSE data found for '{symbol}'.",
                "suggestion": "BSE symbols: use the stock name (RELIANCE) or BSE code (500325)"
            }

        result = {
            "symbol": symbol.replace(".BO", ""),
            "exchange": "BSE",
            "name": safe_get(info, "longName") or safe_get(info, "shortName", default=symbol),
            "price": safe_get(info, "regularMarketPrice"),
            "change": safe_get(info, "regularMarketChange"),
            "change_pct": safe_get(info, "regularMarketChangePercent"),
            "currency": safe_get(info, "currency", default="INR"),
            "open": safe_get(info, "regularMarketOpen"),
            "high": safe_get(info, "regularMarketDayHigh"),
            "low": safe_get(info, "regularMarketDayLow"),
            "prev_close": safe_get(info, "regularMarketPreviousClose"),
            "volume": safe_get(info, "regularMarketVolume"),
            "market_cap": safe_get(info, "marketCap"),
            "market_cap_formatted": format_market_cap(safe_get(info, "marketCap")),
            "fifty_two_week_high": safe_get(info, "fiftyTwoWeekHigh"),
            "fifty_two_week_low": safe_get(info, "fiftyTwoWeekLow"),
            "pe_ratio": safe_get(info, "trailingPE"),
            "sector": safe_get(info, "sector"),
            "industry": safe_get(info, "industry"),
            "timestamp": datetime.now().isoformat(),
        }

        return clean_nan(result)

    except Exception as e:
        logger.error(f"Error fetching BSE quote for {symbol}: {e}")
        return {
            "error": True,
            "message": f"Failed to fetch BSE data for '{symbol}': {str(e)}",
        }


# ===== INDEX DATA =====

@cached(quotes_cache, ttl=300)
def get_index_data(index_name: str = "NIFTY50") -> dict:
    """
    Get current index values for major Indian indices.

    Args:
        index_name: NIFTY50, SENSEX, BANKNIFTY, NIFTYIT, NIFTYPHARMA, etc.
                    Or "ALL" to get all major indices.

    Returns:
        dict with index values, change, and component info
    """
    if index_name.upper() == "ALL":
        indices = ["NIFTY50", "SENSEX", "BANKNIFTY", "NIFTYIT"]
        results = {}
        for idx in indices:
            results[idx] = get_index_data(idx)
        return {"indices": results, "timestamp": datetime.now().isoformat()}

    yf_symbol = _resolve_index(index_name)

    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            return {
                "error": True,
                "message": f"No data found for index '{index_name}'.",
                "suggestion": f"Valid indices: {', '.join(INDEX_MAP.keys())}"
            }

        result = {
            "index": index_name.upper(),
            "yf_symbol": yf_symbol,
            "value": safe_get(info, "regularMarketPrice"),
            "change": safe_get(info, "regularMarketChange"),
            "change_pct": safe_get(info, "regularMarketChangePercent"),
            "open": safe_get(info, "regularMarketOpen"),
            "high": safe_get(info, "regularMarketDayHigh"),
            "low": safe_get(info, "regularMarketDayLow"),
            "prev_close": safe_get(info, "regularMarketPreviousClose"),
            "fifty_two_week_high": safe_get(info, "fiftyTwoWeekHigh"),
            "fifty_two_week_low": safe_get(info, "fiftyTwoWeekLow"),
            "timestamp": datetime.now().isoformat(),
        }

        return clean_nan(result)

    except Exception as e:
        logger.error(f"Error fetching index {index_name}: {e}")
        return {"error": True, "message": f"Failed to fetch index '{index_name}': {str(e)}"}


# ===== HISTORICAL DATA =====

@cached(historical_cache, ttl=86400)
def get_historical_data(
    symbol: str,
    period: str = "1mo",
    interval: str = "1d",
) -> dict:
    """
    Get historical OHLCV data for an NSE stock.

    Args:
        symbol: NSE stock symbol (e.g., RELIANCE, TCS)
        period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        interval: 1m, 5m, 15m, 30m, 1h, 1d, 5d, 1wk, 1mo

    Returns:
        dict with OHLCV data array and metadata
    """
    symbol = validate_symbol(symbol)
    period = validate_period(period)
    interval = validate_interval(interval)
    yf_symbol = to_nse_symbol(symbol)

    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period=period, interval=interval)

        if hist.empty:
            return {
                "error": True,
                "message": f"No historical data for '{symbol}' with period={period}",
                "suggestion": "Try a different period or check if the symbol is correct."
            }

        # Convert DataFrame to list of dicts
        records = []
        for idx, row in hist.iterrows():
            records.append({
                "date": idx.strftime("%Y-%m-%d") if interval in ("1d", "5d", "1wk", "1mo", "3mo")
                        else idx.strftime("%Y-%m-%d %H:%M"),
                "open": round(row.get("Open", 0), 2),
                "high": round(row.get("High", 0), 2),
                "low": round(row.get("Low", 0), 2),
                "close": round(row.get("Close", 0), 2),
                "volume": int(row.get("Volume", 0)),
            })

        # Calculate summary stats
        closes = hist["Close"]
        result = {
            "symbol": symbol.replace(".NS", ""),
            "exchange": "NSE",
            "period": period,
            "interval": interval,
            "data_points": len(records),
            "start_date": records[0]["date"] if records else None,
            "end_date": records[-1]["date"] if records else None,
            "summary": {
                "latest_close": round(float(closes.iloc[-1]), 2) if len(closes) > 0 else None,
                "period_high": round(float(closes.max()), 2),
                "period_low": round(float(closes.min()), 2),
                "period_return_pct": round(
                    float((closes.iloc[-1] / closes.iloc[0] - 1) * 100), 2
                ) if len(closes) > 1 else None,
                "avg_volume": int(hist["Volume"].mean()) if "Volume" in hist else None,
            },
            "data": records,
        }

        return clean_nan(result)

    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}")
        return {"error": True, "message": f"Failed to fetch history for '{symbol}': {str(e)}"}


# ===== MARKET MOVERS =====

@cached(quotes_cache, ttl=300)
def get_market_movers(mover_type: str = "gainers") -> dict:
    """
    Get top gainers, losers, or most active stocks on NSE.

    Uses yfinance screener or NSE direct API.

    Args:
        mover_type: 'gainers', 'losers', or 'active'

    Returns:
        dict with list of stocks and their performance
    """
    # Top Nifty 50 components to check
    nifty50_symbols = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
        "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
        "TITAN.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "WIPRO.NS", "HCLTECH.NS",
        "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TATASTEEL.NS", "ADANIENT.NS",
        "ADANIPORTS.NS", "BAJAJFINSV.NS", "TECHM.NS", "NESTLEIND.NS", "ULTRACEMCO.NS",
    ]

    try:
        results = []
        # Batch download for efficiency
        data = yf.download(
            nifty50_symbols,
            period="2d",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
        )

        for sym in nifty50_symbols:
            try:
                ticker_data = data[sym] if sym in data.columns.get_level_values(0) else None
                if ticker_data is None or ticker_data.empty or len(ticker_data) < 2:
                    continue

                prev_close = float(ticker_data["Close"].iloc[-2])
                current_close = float(ticker_data["Close"].iloc[-1])
                volume = int(ticker_data["Volume"].iloc[-1])

                if prev_close == 0:
                    continue

                change = current_close - prev_close
                change_pct = (change / prev_close) * 100

                results.append({
                    "symbol": sym.replace(".NS", ""),
                    "price": round(current_close, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "volume": volume,
                })
            except Exception:
                continue

        if not results:
            return {
                "error": True,
                "message": "Could not fetch market mover data. Market may be closed.",
            }

        # Sort based on type
        if mover_type == "gainers":
            results.sort(key=lambda x: x["change_pct"], reverse=True)
            results = results[:10]
        elif mover_type == "losers":
            results.sort(key=lambda x: x["change_pct"])
            results = results[:10]
        elif mover_type == "active":
            results.sort(key=lambda x: x["volume"], reverse=True)
            results = results[:10]
        else:
            return {
                "error": True,
                "message": f"Invalid mover_type '{mover_type}'.",
                "suggestion": "Use 'gainers', 'losers', or 'active'"
            }

        return {
            "type": mover_type,
            "count": len(results),
            "exchange": "NSE",
            "note": "Based on Nifty 50 components",
            "stocks": results,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error fetching market movers: {e}")
        return {"error": True, "message": f"Failed to fetch {mover_type}: {str(e)}"}


# ===== MARKET STATUS =====

def get_market_status() -> dict:
    """
    Check if NSE/BSE markets are currently open.

    Returns market status, trading hours, and next open/close time.
    """
    now = datetime.now()

    # NSE trading hours: 9:15 AM - 3:30 PM IST, Monday-Friday
    # Pre-open: 9:00 AM - 9:15 AM
    # We assume the server runs in IST or we convert

    weekday = now.weekday()  # 0=Monday, 6=Sunday
    hour = now.hour
    minute = now.minute
    current_minutes = hour * 60 + minute

    # Market hours in minutes from midnight (IST)
    pre_open_start = 9 * 60       # 9:00 AM
    market_open = 9 * 60 + 15     # 9:15 AM
    market_close = 15 * 60 + 30   # 3:30 PM
    post_close = 16 * 60          # 4:00 PM

    is_weekday = weekday < 5

    if not is_weekday:
        status = "CLOSED"
        reason = "Weekend"
    elif current_minutes < pre_open_start:
        status = "CLOSED"
        reason = "Before market hours"
    elif current_minutes < market_open:
        status = "PRE_OPEN"
        reason = "Pre-open session (9:00 AM - 9:15 AM)"
    elif current_minutes < market_close:
        status = "OPEN"
        reason = "Regular trading session"
    elif current_minutes < post_close:
        status = "POST_CLOSE"
        reason = "Post-closing session"
    else:
        status = "CLOSED"
        reason = "After market hours"

    return {
        "nse_status": status,
        "bse_status": status,  # BSE follows same hours
        "reason": reason,
        "trading_hours": {
            "pre_open": "9:00 AM - 9:15 AM IST",
            "regular": "9:15 AM - 3:30 PM IST",
            "post_close": "3:30 PM - 4:00 PM IST",
        },
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "IST (assumed)",
        "note": "Holiday calendar not included — check NSE website for holidays.",
    }
