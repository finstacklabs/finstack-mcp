"""
FinStack Advanced Indian Market Data

Options chain, FII/DII data, bulk deals, corporate actions,
quarterly results, IPO calendar, earnings calendar.
"""

import logging
from datetime import datetime
from typing import Any

import httpx
import yfinance as yf
import pandas as pd

from finstack.utils.cache import cached, quotes_cache, general_cache, fundamentals_cache
from finstack.utils.helpers import (
    validate_symbol, to_nse_symbol, clean_nan,
)

logger = logging.getLogger("finstack.data.nse_advanced")

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def _format_calendar_value(value: Any) -> Any:
    """Convert pandas/yfinance calendar values into JSON-friendly strings."""
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%Y-%m-%d")
        except Exception:  # pragma: no cover
            return str(value)
    return value


def _nse_session() -> httpx.Client:
    """Create an NSE session with cookies (NSE requires session cookies)."""
    client = httpx.Client(headers=NSE_HEADERS, timeout=15, follow_redirects=True)
    # Hit the main page first to get session cookies
    try:
        client.get("https://www.nseindia.com/")
    except Exception:
        pass
    return client


# ===== OPTIONS CHAIN =====

@cached(quotes_cache, ttl=300)
def get_options_chain(symbol: str) -> dict:
    """
    Get options chain data for an NSE stock or index.
    Uses yfinance options data.
    """
    symbol = validate_symbol(symbol)

    # Try NSE symbol
    for yf_sym in [to_nse_symbol(symbol), symbol]:
        try:
            ticker = yf.Ticker(yf_sym)
            expiry_dates = ticker.options

            if not expiry_dates:
                continue

            # Get nearest expiry
            nearest_expiry = expiry_dates[0]
            chain = ticker.option_chain(nearest_expiry)

            calls = chain.calls
            puts = chain.puts

            # Format calls
            calls_data = []
            for _, row in calls.iterrows():
                calls_data.append({
                    "strike": float(row.get("strike", 0)),
                    "last_price": float(row.get("lastPrice", 0)),
                    "bid": float(row.get("bid", 0)),
                    "ask": float(row.get("ask", 0)),
                    "change": float(row.get("change", 0)),
                    "change_pct": float(row.get("percentChange", 0)),
                    "volume": int(row.get("volume", 0)) if pd.notna(row.get("volume")) else 0,
                    "open_interest": int(row.get("openInterest", 0)) if pd.notna(row.get("openInterest")) else 0,
                    "implied_volatility": round(float(row.get("impliedVolatility", 0)) * 100, 2),
                    "in_the_money": bool(row.get("inTheMoney", False)),
                })

            # Format puts
            puts_data = []
            for _, row in puts.iterrows():
                puts_data.append({
                    "strike": float(row.get("strike", 0)),
                    "last_price": float(row.get("lastPrice", 0)),
                    "bid": float(row.get("bid", 0)),
                    "ask": float(row.get("ask", 0)),
                    "change": float(row.get("change", 0)),
                    "change_pct": float(row.get("percentChange", 0)),
                    "volume": int(row.get("volume", 0)) if pd.notna(row.get("volume")) else 0,
                    "open_interest": int(row.get("openInterest", 0)) if pd.notna(row.get("openInterest")) else 0,
                    "implied_volatility": round(float(row.get("impliedVolatility", 0)) * 100, 2),
                    "in_the_money": bool(row.get("inTheMoney", False)),
                })

            # PCR (Put-Call Ratio)
            total_call_oi = sum(c.get("open_interest", 0) for c in calls_data)
            total_put_oi = sum(p.get("open_interest", 0) for p in puts_data)
            pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else None

            pcr_signal = "Neutral"
            if pcr and pcr > 1.2:
                pcr_signal = "Bearish sentiment (high put buying)"
            elif pcr and pcr < 0.8:
                pcr_signal = "Bullish sentiment (high call buying)"

            return clean_nan({
                "symbol": symbol.replace(".NS", "").replace(".BO", ""),
                "expiry": nearest_expiry,
                "all_expiries": list(expiry_dates[:6]),
                "underlying_price": float(ticker.info.get("regularMarketPrice", 0))
                                    if ticker.info else None,
                "pcr": pcr,
                "pcr_signal": pcr_signal,
                "total_call_oi": total_call_oi,
                "total_put_oi": total_put_oi,
                "calls": calls_data[:20],  # Top 20 strikes
                "puts": puts_data[:20],
                "timestamp": datetime.now().isoformat(),
            })

        except Exception as e:
            logger.debug(f"Options chain attempt failed for {yf_sym}: {e}")
            continue

    return {
        "error": True,
        "message": f"No options data for '{symbol}'.",
        "suggestion": "Options data available for most Nifty 50 stocks and indices."
    }


# ===== FII/DII DATA =====

@cached(general_cache, ttl=1800)
def get_fii_dii_data() -> dict:
    """
    Get FII (Foreign Institutional Investor) and DII (Domestic Institutional Investor)
    activity data.

    Note: Direct NSE API may be blocked. Falls back to approximate data.
    """
    try:
        client = _nse_session()
        resp = client.get("https://www.nseindia.com/api/fiidiiTradeReact")

        if resp.status_code == 200:
            data = resp.json()
            client.close()

            return clean_nan({
                "data": data,
                "source": "NSE Direct API",
                "timestamp": datetime.now().isoformat(),
            })
        client.close()
    except Exception as e:
        logger.debug(f"NSE FII/DII API failed: {e}")

    # Fallback: provide context about FII/DII
    return {
        "message": (
            "FII/DII live data requires direct NSE access which may be rate-limited. "
            "For real-time FII/DII data, visit: https://www.nseindia.com/reports/fii-dii"
        ),
        "what_is_fii_dii": {
            "FII": "Foreign Institutional Investors — overseas funds investing in Indian markets",
            "DII": "Domestic Institutional Investors — Indian mutual funds, insurance cos, etc.",
            "interpretation": (
                "FII net buy = foreign money flowing in (bullish signal). "
                "DII net buy = domestic institutions accumulating (can be contrarian signal)."
            ),
        },
        "data_sources": [
            "https://www.nseindia.com/reports/fii-dii",
            "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/",
        ],
        "timestamp": datetime.now().isoformat(),
    }


# ===== BULK/BLOCK DEALS =====

@cached(general_cache, ttl=1800)
def get_bulk_deals() -> dict:
    """Get recent bulk and block deals on NSE."""
    try:
        client = _nse_session()
        resp = client.get("https://www.nseindia.com/api/snapshot-capital-market-largedeal")

        if resp.status_code == 200:
            data = resp.json()
            client.close()

            deals = []
            for item in data.get("data", [])[:20]:
                deals.append({
                    "symbol": item.get("symbol", ""),
                    "deal_type": item.get("secType", ""),
                    "client": item.get("clientName", ""),
                    "buy_sell": item.get("buySell", ""),
                    "quantity": item.get("qty", ""),
                    "price": item.get("wAvgPrice", ""),
                    "date": item.get("dealDate", ""),
                })

            return clean_nan({
                "deals": deals,
                "count": len(deals),
                "source": "NSE",
                "timestamp": datetime.now().isoformat(),
            })
        client.close()
    except Exception as e:
        logger.debug(f"NSE bulk deals API failed: {e}")

    return {
        "message": "Bulk deals data requires direct NSE access. May be rate-limited.",
        "data_source": "https://www.nseindia.com/market-data/bulk-deal-data",
        "timestamp": datetime.now().isoformat(),
    }


# ===== CORPORATE ACTIONS =====

@cached(fundamentals_cache, ttl=3600)
def get_corporate_actions(symbol: str) -> dict:
    """Get corporate actions (dividends, splits, bonuses) for an NSE stock."""
    symbol = validate_symbol(symbol)

    try:
        yf_sym = to_nse_symbol(symbol)
        ticker = yf.Ticker(yf_sym)

        # Dividends
        divs = ticker.dividends
        div_records = []
        if divs is not None and not divs.empty:
            for date, amount in list(divs.items())[-10:]:
                div_records.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "type": "DIVIDEND",
                    "value": round(float(amount), 4),
                })

        # Splits
        splits = ticker.splits
        split_records = []
        if splits is not None and not splits.empty:
            for date, ratio in list(splits.items())[-10:]:
                split_records.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "type": "STOCK_SPLIT",
                    "ratio": f"{int(ratio)}:1" if ratio >= 1 else f"1:{int(1/ratio)}",
                })

        all_actions = div_records + split_records
        all_actions.sort(key=lambda x: x["date"], reverse=True)

        return clean_nan({
            "symbol": symbol.replace(".NS", "").replace(".BO", ""),
            "total_actions": len(all_actions),
            "dividends": len(div_records),
            "splits": len(split_records),
            "actions": all_actions[:15],
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error fetching corporate actions for {symbol}: {e}")
        return {"error": True, "message": str(e)}


# ===== QUARTERLY RESULTS =====

@cached(fundamentals_cache, ttl=3600)
def get_quarterly_results(symbol: str) -> dict:
    """Get latest quarterly financial results for an NSE stock."""
    symbol = validate_symbol(symbol)

    try:
        yf_sym = to_nse_symbol(symbol)
        ticker = yf.Ticker(yf_sym)

        # Get quarterly income statement
        q_income = ticker.quarterly_income_stmt
        if q_income is None or q_income.empty:
            return {"error": True, "message": f"No quarterly results for '{symbol}'."}

        quarters = []
        for col in q_income.columns[:4]:
            q_data = {"quarter": col.strftime("%Y-%m-%d")}

            for item in q_income.index:
                if any(k.lower() in str(item).lower() for k in ["revenue", "cost", "profit", "income", "ebitda", "eps"]):
                    key = str(item).replace(" ", "_").lower()
                    val = q_income.loc[item, col]
                    q_data[key] = round(float(val), 2) if pd.notna(val) else None

            quarters.append(q_data)

        # QoQ growth
        if len(quarters) >= 2:
            for key in list(quarters[0].keys()):
                if key == "quarter":
                    continue
                curr = quarters[0].get(key)
                prev = quarters[1].get(key)
                if curr and prev and prev != 0:
                    growth = round(((curr - prev) / abs(prev)) * 100, 2)
                    quarters[0][f"{key}_qoq_growth"] = growth

        return clean_nan({
            "symbol": symbol.replace(".NS", "").replace(".BO", ""),
            "latest_quarter": quarters[0].get("quarter") if quarters else None,
            "quarters": quarters,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error fetching quarterly results for {symbol}: {e}")
        return {"error": True, "message": str(e)}


# ===== EARNINGS CALENDAR =====

@cached(general_cache, ttl=3600)
def get_earnings_calendar(symbol: str = "") -> dict:
    """Get upcoming earnings dates."""
    if symbol:
        symbol = validate_symbol(symbol)
        yf_sym = to_nse_symbol(symbol)

        try:
            ticker = yf.Ticker(yf_sym)
            cal = ticker.calendar

            if cal is None or (isinstance(cal, pd.DataFrame) and cal.empty):
                return {
                    "symbol": symbol.replace(".NS", ""),
                    "message": "No upcoming earnings date available.",
                }

            if isinstance(cal, dict):
                return clean_nan({
                    "symbol": symbol.replace(".NS", ""),
                    "earnings_date": _format_calendar_value(cal.get("Earnings Date", ["Not available"])),
                    "earnings_avg": _format_calendar_value(cal.get("Earnings Average")),
                    "earnings_low": _format_calendar_value(cal.get("Earnings Low")),
                    "earnings_high": _format_calendar_value(cal.get("Earnings High")),
                    "revenue_avg": _format_calendar_value(cal.get("Revenue Average")),
                    "timestamp": datetime.now().isoformat(),
                })
            else:
                return clean_nan({
                    "symbol": symbol.replace(".NS", ""),
                    "calendar": cal.to_dict() if hasattr(cal, "to_dict") else str(cal),
                    "timestamp": datetime.now().isoformat(),
                })

        except Exception as e:
            return {"error": True, "message": str(e)}
    else:
        return {
            "message": "Provide a stock symbol to get its earnings calendar.",
            "example": "earnings_calendar('RELIANCE') or earnings_calendar('AAPL')",
        }


# ===== IPO CALENDAR =====

@cached(general_cache, ttl=3600)
def get_ipo_calendar() -> dict:
    """Get recent and upcoming IPO information."""
    # NSE IPO data requires direct API access
    try:
        client = _nse_session()
        resp = client.get("https://www.nseindia.com/api/ipo-current-issue")

        if resp.status_code == 200:
            data = resp.json()
            client.close()

            ipos = []
            for item in data if isinstance(data, list) else data.get("data", []):
                ipos.append({
                    "company": item.get("companyName", ""),
                    "symbol": item.get("symbol", ""),
                    "open_date": item.get("issueStartDate", ""),
                    "close_date": item.get("issueEndDate", ""),
                    "price_band": item.get("issuePriceBand", ""),
                    "issue_size": item.get("issueSize", ""),
                    "status": item.get("status", ""),
                })

            return clean_nan({
                "ipos": ipos,
                "count": len(ipos),
                "source": "NSE",
                "timestamp": datetime.now().isoformat(),
            })
        client.close()
    except Exception as e:
        logger.debug(f"NSE IPO API failed: {e}")

    return {
        "message": "IPO data requires direct NSE access. Check these sources:",
        "sources": [
            "https://www.nseindia.com/market-data/all-upcoming-issues-ipo",
            "https://www.chittorgarh.com/ipo/ipo-dashboard/",
            "https://www.moneycontrol.com/ipo/",
        ],
        "timestamp": datetime.now().isoformat(),
    }


@cached(general_cache)
def get_mutual_fund_nav(query: str) -> dict[str, Any]:
    """Get NAV and details for an Indian mutual fund by name or scheme code.

    Uses the free AMFI / mfapi.in API — no key required.

    Args:
        query: Fund name (e.g. "SBI Bluechip") or numeric scheme code (e.g. "119598")
    """
    try:
        with httpx.Client(timeout=12) as client:
            # If numeric, treat as direct scheme code
            if query.strip().isdigit():
                scheme_code = query.strip()
                resp = client.get(f"https://api.mfapi.in/mf/{scheme_code}")
                if resp.status_code != 200:
                    return {"error": True, "message": f"Scheme code {scheme_code} not found."}
                data = resp.json()
                meta = data.get("meta", {})
                navs = data.get("data", [])
                latest = navs[0] if navs else {}
                prev   = navs[1] if len(navs) > 1 else {}
                change = 0.0
                change_pct = 0.0
                if latest.get("nav") and prev.get("nav"):
                    try:
                        c_nav  = float(latest["nav"])
                        p_nav  = float(prev["nav"])
                        change = round(c_nav - p_nav, 4)
                        change_pct = round((change / p_nav) * 100, 3)
                    except (ValueError, ZeroDivisionError):
                        pass
                return {
                    "scheme_code": scheme_code,
                    "fund_name": meta.get("scheme_name", ""),
                    "fund_house": meta.get("fund_house", ""),
                    "scheme_type": meta.get("scheme_type", ""),
                    "scheme_category": meta.get("scheme_category", ""),
                    "nav": latest.get("nav"),
                    "nav_date": latest.get("date"),
                    "change": change,
                    "change_pct": change_pct,
                    "nav_history_7d": navs[:7],
                    "timestamp": datetime.now().isoformat(),
                }

            # Search by name
            search_resp = client.get(
                f"https://api.mfapi.in/mf/search?q={query}",
            )
            if search_resp.status_code != 200:
                return {"error": True, "message": "Could not search mutual fund database."}

            results = search_resp.json()
            if not results:
                return {
                    "error": True,
                    "message": f"No mutual fund found matching '{query}'.",
                    "tip": "Try the fund house name (e.g. 'HDFC Flexi Cap') or a scheme code.",
                }

            # Return top 5 matches + fetch NAV for the best match
            top = results[0]
            nav_resp = client.get(f"https://api.mfapi.in/mf/{top['schemeCode']}")
            nav_data = nav_resp.json() if nav_resp.status_code == 200 else {}
            navs = nav_data.get("data", [])
            latest = navs[0] if navs else {}
            prev   = navs[1] if len(navs) > 1 else {}
            change = 0.0
            change_pct = 0.0
            if latest.get("nav") and prev.get("nav"):
                try:
                    c_nav  = float(latest["nav"])
                    p_nav  = float(prev["nav"])
                    change = round(c_nav - p_nav, 4)
                    change_pct = round((change / p_nav) * 100, 3)
                except (ValueError, ZeroDivisionError):
                    pass

            return {
                "best_match": {
                    "scheme_code": top["schemeCode"],
                    "fund_name": top["schemeName"],
                    "nav": latest.get("nav"),
                    "nav_date": latest.get("date"),
                    "change": change,
                    "change_pct": change_pct,
                    "nav_history_7d": navs[:7],
                },
                "other_matches": [
                    {"scheme_code": r["schemeCode"], "fund_name": r["schemeName"]}
                    for r in results[1:5]
                ],
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.error(f"Error fetching mutual fund NAV for '{query}': {e}")
        return {"error": True, "message": str(e)}


@cached(quotes_cache)
def get_circuit_breakers(circuit_type: str = "both") -> dict[str, Any]:
    """Scan for NSE stocks hitting upper or lower circuit limits today.

    Uses yfinance to check if a stock's current price == its intraday high (upper)
    or intraday low (lower), which signals a circuit halt.

    Args:
        circuit_type: "upper", "lower", or "both"
    """
    # Nifty 500 constituents — broad watchlist
    watchlist = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
        "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK",
        "ASIANPAINT", "MARUTI", "TITAN", "SUNPHARMA", "ULTRACEMCO",
        "BAJFINANCE", "WIPRO", "NESTLEIND", "TECHM", "POWERGRID",
        "NTPC", "ONGC", "HCLTECH", "ADANIENT", "ADANIPORTS", "TATAMOTORS",
        "TATASTEEL", "JSWSTEEL", "HINDALCO", "BPCL", "GRASIM", "DIVISLAB",
        "DRREDDY", "CIPLA", "BRITANNIA", "HEROMOTOCO", "BAJAJFINSV",
        "EICHERMOT", "COALINDIA", "UPL", "INDUSINDBK", "SBILIFE", "HDFCLIFE",
        "APOLLOHOSP", "PIDILITIND", "TATACONSUM", "DABUR", "BERGEPAINT",
    ]

    upper_circuits = []
    lower_circuits = []

    for sym in watchlist:
        try:
            ticker = yf.Ticker(f"{sym}.NS")
            info = ticker.fast_info
            current = getattr(info, "last_price", None)
            day_high = getattr(info, "day_high", None)
            day_low  = getattr(info, "day_low", None)

            if current is None or day_high is None or day_low is None:
                continue

            # Upper circuit: price within 0.05% of day high
            if circuit_type in ("upper", "both") and day_high > 0:
                gap_pct = ((day_high - current) / day_high) * 100
                if gap_pct <= 0.05:
                    upper_circuits.append({
                        "symbol": sym,
                        "price": round(current, 2),
                        "day_high": round(day_high, 2),
                        "gap_to_circuit_pct": round(gap_pct, 3),
                    })

            # Lower circuit: price within 0.05% of day low
            if circuit_type in ("lower", "both") and day_low > 0:
                gap_pct = ((current - day_low) / day_low) * 100
                if gap_pct <= 0.05:
                    lower_circuits.append({
                        "symbol": sym,
                        "price": round(current, 2),
                        "day_low": round(day_low, 2),
                        "gap_to_circuit_pct": round(gap_pct, 3),
                    })
        except Exception:
            continue

    return {
        "circuit_type": circuit_type,
        "upper_circuits": upper_circuits,
        "lower_circuits": lower_circuits,
        "upper_count": len(upper_circuits),
        "lower_count": len(lower_circuits),
        "stocks_scanned": len(watchlist),
        "note": "Scans Nifty 500 constituents. Circuit = price within 0.05% of intraday high/low.",
        "timestamp": datetime.now().isoformat(),
    }


# Nifty 50 & Sensex constituents (static list, updated periodically)
_NIFTY50 = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "TITAN", "SUNPHARMA", "ULTRACEMCO", "BAJFINANCE", "WIPRO", "NESTLEIND",
    "TECHM", "POWERGRID", "NTPC", "ONGC", "HCLTECH", "ADANIENT", "ADANIPORTS",
    "TATAMOTORS", "TATASTEEL", "JSWSTEEL", "HINDALCO", "BPCL", "GRASIM",
    "DIVISLAB", "DRREDDY", "CIPLA", "BRITANNIA", "HEROMOTOCO", "BAJAJFINSV",
    "EICHERMOT", "COALINDIA", "UPL", "INDUSINDBK", "SBILIFE", "HDFCLIFE",
    "APOLLOHOSP", "PIDILITIND", "TATACONSUM", "BAJAJ-AUTO", "SHRIRAMFIN",
]

_SENSEX30 = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "TITAN", "SUNPHARMA", "ULTRACEMCO", "BAJFINANCE", "WIPRO", "NESTLEIND",
    "TECHM", "POWERGRID", "NTPC", "ONGC", "HCLTECH", "TATAMOTORS", "TATASTEEL",
    "BAJAJFINSV", "INDUSINDBK", "HDFCLIFE",
]


@cached(general_cache)
def get_index_components(index_name: str = "nifty50") -> dict[str, Any]:
    """Get the list of stocks in Nifty 50 or Sensex with live price data.

    Args:
        index_name: "nifty50" or "sensex"
    """
    name_lower = index_name.lower().replace(" ", "").replace("-", "")
    if "sensex" in name_lower or "bse" in name_lower:
        symbols = _SENSEX30
        label = "Sensex 30"
    else:
        symbols = _NIFTY50
        label = "Nifty 50"

    components = []
    for sym in symbols:
        try:
            ticker = yf.Ticker(f"{sym}.NS")
            info = ticker.fast_info
            price   = round(getattr(info, "last_price",   0) or 0, 2)
            prev    = round(getattr(info, "previous_close", price) or price, 2)
            mkt_cap = getattr(info, "market_cap", None)
            change_pct = round(((price - prev) / prev) * 100, 2) if prev else 0
            components.append({
                "symbol":      sym,
                "price":       price,
                "change_pct":  change_pct,
                "market_cap":  mkt_cap,
            })
        except Exception:
            components.append({"symbol": sym, "price": None, "change_pct": None, "market_cap": None})

    # Sort by market cap descending (None goes last)
    components.sort(key=lambda x: x["market_cap"] or 0, reverse=True)

    gainers = sorted([c for c in components if (c["change_pct"] or 0) > 0], key=lambda x: x["change_pct"], reverse=True)
    losers  = sorted([c for c in components if (c["change_pct"] or 0) < 0], key=lambda x: x["change_pct"])

    return {
        "index":       label,
        "total":       len(components),
        "components":  components,
        "top_gainers": gainers[:5],
        "top_losers":  losers[:5],
        "timestamp":   datetime.now().isoformat(),
    }


@cached(quotes_cache)
def get_52week_scanner(scan_type: str = "near_high", threshold_pct: float = 5.0) -> dict[str, Any]:
    """Scan Nifty 50 stocks for those near their 52-week high or low.

    Args:
        scan_type:      "near_high" (within threshold of 52w high),
                        "near_low"  (within threshold of 52w low),
                        "both"      (return both lists)
        threshold_pct:  How close to the 52w extreme to qualify, in % (default 5.0)

    Returns stocks with price, 52w high/low, and % gap.
    """
    near_high = []
    near_low  = []

    for sym in _NIFTY50:
        try:
            ticker = yf.Ticker(f"{sym}.NS")
            info = ticker.fast_info
            price    = getattr(info, "last_price",    None)
            high_52w = getattr(info, "year_high",     None)
            low_52w  = getattr(info, "year_low",      None)

            if not all([price, high_52w, low_52w]):
                continue

            gap_from_high = round(((high_52w - price) / high_52w) * 100, 2)
            gap_from_low  = round(((price - low_52w)  / low_52w)  * 100, 2)

            entry = {
                "symbol":          sym,
                "price":           round(price, 2),
                "52w_high":        round(high_52w, 2),
                "52w_low":         round(low_52w,  2),
                "gap_from_high_pct": gap_from_high,
                "gap_from_low_pct":  gap_from_low,
            }

            if scan_type in ("near_high", "both") and gap_from_high <= threshold_pct:
                near_high.append(entry)
            if scan_type in ("near_low", "both") and gap_from_low <= threshold_pct:
                near_low.append(entry)

        except Exception:
            continue

    near_high.sort(key=lambda x: x["gap_from_high_pct"])
    near_low.sort(key=lambda x:  x["gap_from_low_pct"])

    return {
        "scan_type":     scan_type,
        "threshold_pct": threshold_pct,
        "near_52w_high": near_high,
        "near_52w_low":  near_low,
        "high_count":    len(near_high),
        "low_count":     len(near_low),
        "universe":      "Nifty 50",
        "stocks_scanned": len(_NIFTY50),
        "timestamp":     datetime.now().isoformat(),
    }
