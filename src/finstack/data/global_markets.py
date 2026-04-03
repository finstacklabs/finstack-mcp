"""
FinStack Global Markets Data Fetcher

Fetches global stock, crypto, and forex data from free sources:
1. yfinance - US/EU/Asia stocks + crypto + forex
2. CoinGecko free API - detailed crypto data
3. SEC EDGAR - US company filings

All methods return clean dicts ready for MCP tool responses.
"""

import logging
from datetime import datetime

import httpx
import yfinance as yf

from finstack.utils.cache import cached, quotes_cache, fundamentals_cache, historical_cache
from finstack.utils.helpers import (
    validate_symbol, validate_period, validate_interval,
    clean_nan, safe_get, format_market_cap,
)
from finstack.config import config

logger = logging.getLogger("finstack.data.global")


# ===== GLOBAL STOCK QUOTES =====

@cached(quotes_cache, ttl=300)
def get_global_quote(symbol: str) -> dict:
    """
    Get real-time quote for any global stock.
    Supports US (AAPL), UK (.L), Japan (.T), Hong Kong (.HK), etc.
    """
    symbol = validate_symbol(symbol)

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            return {
                "error": True,
                "message": f"No data found for '{symbol}'.",
                "suggestion": (
                    "Try formats: AAPL (US), AAPL.L (London), 7203.T (Tokyo), "
                    "0700.HK (Hong Kong), RELIANCE.NS (India NSE)"
                ),
            }

        exchange = safe_get(info, "exchange", default="Unknown")
        currency = safe_get(info, "currency", default="USD")

        result = {
            "symbol": symbol,
            "name": safe_get(info, "longName") or safe_get(info, "shortName", default=symbol),
            "exchange": exchange,
            "currency": currency,
            "price": safe_get(info, "regularMarketPrice"),
            "change": safe_get(info, "regularMarketChange"),
            "change_pct": safe_get(info, "regularMarketChangePercent"),
            "open": safe_get(info, "regularMarketOpen"),
            "high": safe_get(info, "regularMarketDayHigh"),
            "low": safe_get(info, "regularMarketDayLow"),
            "prev_close": safe_get(info, "regularMarketPreviousClose"),
            "volume": safe_get(info, "regularMarketVolume"),
            "avg_volume": safe_get(info, "averageDailyVolume10Day"),
            "market_cap": safe_get(info, "marketCap"),
            "market_cap_formatted": format_market_cap(safe_get(info, "marketCap")),
            "pe_ratio": safe_get(info, "trailingPE"),
            "forward_pe": safe_get(info, "forwardPE"),
            "eps": safe_get(info, "trailingEps"),
            "dividend_yield": safe_get(info, "dividendYield"),
            "beta": safe_get(info, "beta"),
            "fifty_two_week_high": safe_get(info, "fiftyTwoWeekHigh"),
            "fifty_two_week_low": safe_get(info, "fiftyTwoWeekLow"),
            "sector": safe_get(info, "sector"),
            "industry": safe_get(info, "industry"),
            "country": safe_get(info, "country"),
            "website": safe_get(info, "website"),
            "timestamp": datetime.now().isoformat(),
        }

        return clean_nan(result)

    except Exception as e:
        logger.error(f"Error fetching global quote for {symbol}: {e}")
        return {"error": True, "message": f"Failed to fetch '{symbol}': {str(e)}"}


@cached(historical_cache, ttl=86400)
def get_global_historical(
    symbol: str, period: str = "1mo", interval: str = "1d"
) -> dict:
    """Get historical OHLCV data for any global stock."""
    symbol = validate_symbol(symbol)
    period = validate_period(period)
    interval = validate_interval(interval)

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)

        if hist.empty:
            return {
                "error": True,
                "message": f"No historical data for '{symbol}' (period={period})",
            }

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

        closes = hist["Close"]
        result = {
            "symbol": symbol,
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
            },
            "data": records,
        }
        return clean_nan(result)

    except Exception as e:
        logger.error(f"Error fetching historical for {symbol}: {e}")
        return {"error": True, "message": str(e)}


# ===== CRYPTO =====

@cached(quotes_cache, ttl=120)
def get_crypto_price(symbol: str) -> dict:
    """
    Get live crypto price.
    Accepts: BTC, ETH, SOL, or full yfinance symbols like BTC-USD.
    """
    # Normalize crypto symbols
    symbol = symbol.strip().upper()
    if not symbol.endswith("-USD") and not symbol.endswith("-INR"):
        yf_symbol = f"{symbol}-USD"
    else:
        yf_symbol = symbol

    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            return {
                "error": True,
                "message": f"No crypto data for '{symbol}'.",
                "suggestion": "Try: BTC, ETH, SOL, XRP, DOGE, ADA, DOT, MATIC",
            }

        result = {
            "symbol": symbol.replace("-USD", ""),
            "name": safe_get(info, "name") or safe_get(info, "shortName", default=symbol),
            "price_usd": safe_get(info, "regularMarketPrice"),
            "change_24h": safe_get(info, "regularMarketChange"),
            "change_pct_24h": safe_get(info, "regularMarketChangePercent"),
            "market_cap": safe_get(info, "marketCap"),
            "market_cap_formatted": format_market_cap(safe_get(info, "marketCap")),
            "volume_24h": safe_get(info, "volume24Hr") or safe_get(info, "regularMarketVolume"),
            "circulating_supply": safe_get(info, "circulatingSupply"),
            "high_24h": safe_get(info, "regularMarketDayHigh"),
            "low_24h": safe_get(info, "regularMarketDayLow"),
            "all_time_high": safe_get(info, "fiftyTwoWeekHigh"),
            "timestamp": datetime.now().isoformat(),
        }
        return clean_nan(result)

    except Exception as e:
        logger.error(f"Error fetching crypto {symbol}: {e}")
        return {"error": True, "message": str(e)}


@cached(historical_cache, ttl=3600)
def get_crypto_historical(
    symbol: str, period: str = "1mo", interval: str = "1d"
) -> dict:
    """Get historical crypto price data."""
    symbol = symbol.strip().upper()
    if not symbol.endswith("-USD"):
        symbol = f"{symbol}-USD"
    return get_global_historical(symbol, period, interval)


# ===== FOREX =====

@cached(quotes_cache, ttl=300)
def get_forex_rate(from_currency: str, to_currency: str = "INR") -> dict:
    """
    Get live forex exchange rate.
    Uses yfinance forex pairs (e.g., USDINR=X).
    """
    from_currency = from_currency.strip().upper()
    to_currency = to_currency.strip().upper()
    yf_symbol = f"{from_currency}{to_currency}=X"

    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            return {
                "error": True,
                "message": f"No forex data for {from_currency}/{to_currency}.",
                "suggestion": "Try: USD/INR, EUR/INR, GBP/INR, USD/EUR, EUR/USD",
            }

        result = {
            "pair": f"{from_currency}/{to_currency}",
            "rate": safe_get(info, "regularMarketPrice"),
            "change": safe_get(info, "regularMarketChange"),
            "change_pct": safe_get(info, "regularMarketChangePercent"),
            "day_high": safe_get(info, "regularMarketDayHigh"),
            "day_low": safe_get(info, "regularMarketDayLow"),
            "prev_close": safe_get(info, "regularMarketPreviousClose"),
            "fifty_two_week_high": safe_get(info, "fiftyTwoWeekHigh"),
            "fifty_two_week_low": safe_get(info, "fiftyTwoWeekLow"),
            "timestamp": datetime.now().isoformat(),
        }
        return clean_nan(result)

    except Exception as e:
        logger.error(f"Error fetching forex {from_currency}/{to_currency}: {e}")
        return {"error": True, "message": str(e)}


# ===== NEWS =====

@cached(quotes_cache, ttl=600)
def get_market_news(symbol: str = "") -> dict:
    """
    Get latest market news for a stock or general market.
    Uses yfinance news feed.
    """
    try:
        if symbol:
            symbol = validate_symbol(symbol)
            ticker = yf.Ticker(symbol)
            news_items = ticker.news or []
        else:
            # General market news via index
            ticker = yf.Ticker("^NSEI")
            news_items = ticker.news or []

        if not news_items:
            return {
                "symbol": symbol or "MARKET",
                "news": [],
                "message": "No recent news available.",
            }

        formatted_news = []
        for item in news_items[:10]:  # Limit to 10 articles
            content = item.get("content", {}) if isinstance(item, dict) else {}
            formatted_news.append({
                "title": content.get("title") or item.get("title", ""),
                "publisher": content.get("provider", {}).get("displayName", "")
                             if isinstance(content.get("provider"), dict)
                             else item.get("publisher", ""),
                "link": content.get("canonicalUrl", {}).get("url", "")
                        if isinstance(content.get("canonicalUrl"), dict)
                        else item.get("link", ""),
                "published": content.get("pubDate", "") or item.get("providerPublishTime", ""),
                "type": item.get("type", "article"),
            })

        return {
            "symbol": symbol or "MARKET",
            "count": len(formatted_news),
            "news": formatted_news,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        return {"error": True, "message": str(e)}


# ===== SEC FILINGS =====

@cached(fundamentals_cache, ttl=3600)
def get_sec_filings(symbol: str, filing_type: str = "10-K", count: int = 5) -> dict:
    """
    Get SEC filings for a US company.
    Uses SEC EDGAR free API (no key needed, just user-agent).
    """
    symbol = validate_symbol(symbol).replace(".NS", "").replace(".BO", "")

    try:
        # First, get the CIK number for the company
        headers = {"User-Agent": config.sec_user_agent}

        # Use the company tickers endpoint
        tickers_url = "https://www.sec.gov/files/company_tickers.json"

        with httpx.Client(headers=headers, timeout=15) as client:
            # Get CIK from tickers
            resp = client.get(tickers_url)
            if resp.status_code != 200:
                return {
                    "error": True,
                    "message": "Could not access SEC EDGAR. Try again later.",
                }

            tickers_data = resp.json()
            cik = None
            company_name = None

            for _, entry in tickers_data.items():
                if entry.get("ticker", "").upper() == symbol.upper():
                    cik = str(entry["cik_str"]).zfill(10)
                    company_name = entry.get("title", symbol)
                    break

            if not cik:
                return {
                    "error": True,
                    "message": f"Company '{symbol}' not found in SEC EDGAR.",
                    "suggestion": "SEC filings only available for US-listed companies.",
                }

            # Get filings
            filings_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            resp = client.get(filings_url)

            if resp.status_code != 200:
                return {"error": True, "message": "Failed to fetch SEC filings."}

            filings_data = resp.json()

        recent = filings_data.get("filings", {}).get("recent", {})

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])

        results = []
        for i in range(len(forms)):
            if filing_type == "ALL" or forms[i] == filing_type:
                accession_clean = accessions[i].replace("-", "")
                results.append({
                    "form": forms[i],
                    "filing_date": dates[i],
                    "description": descriptions[i] if i < len(descriptions) else "",
                    "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{primary_docs[i]}"
                           if i < len(primary_docs) else "",
                })
                if len(results) >= count:
                    break

        return {
            "symbol": symbol,
            "company": company_name,
            "cik": cik,
            "filing_type": filing_type,
            "count": len(results),
            "filings": results,
            "sec_page": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error fetching SEC filings for {symbol}: {e}")
        return {"error": True, "message": str(e)}
