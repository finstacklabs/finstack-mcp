"""
FinStack Dashboard API
FastAPI backend that serves real NSE/BSE data to the dashboard.html frontend.

Run:
    cd dashboard-api
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Dashboard will auto-connect at http://localhost:8000
"""
import sys
import os
from pathlib import Path

# Add finstack-mcp src to path so we can import data functions directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI(title="FinStack Dashboard API", version="0.7.0")

# Allow dashboard.html (file:// or localhost) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _safe(fn, *args, **kwargs):
    """Call a finstack data function, return None on any error."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        return {"error": str(e)}


# ─── Market Overview ──────────────────────────────────────────────────────────

@app.get("/api/market-status")
def market_status():
    from finstack.data.nse import get_market_status
    return _safe(get_market_status)


@app.get("/api/nifty")
def nifty_overview():
    """Nifty 50, Bank Nifty, Sensex live."""
    from finstack.data.nse import get_index_data
    results = {}
    for idx in ["NIFTY50", "BANKNIFTY", "SENSEX"]:
        results[idx] = _safe(get_index_data, idx)
    return results


@app.get("/api/vix")
def india_vix():
    from finstack.data.market_intelligence import get_india_vix
    return _safe(get_india_vix, days=30)


@app.get("/api/gift-nifty")
def gift_nifty():
    from finstack.data.market_intelligence import get_gift_nifty
    return _safe(get_gift_nifty)


# ─── Quote & Historical ───────────────────────────────────────────────────────

@app.get("/api/quote/{symbol}")
def quote(symbol: str):
    """Live NSE quote: LTP, change, OHLC, volume, circuit limits."""
    from finstack.data.nse import get_nse_quote
    from finstack.data.broker import get_live_quote_angel, _is_configured
    # Try Angel One first (real-time), fall back to yfinance (15-min delay)
    if _is_configured():
        result = _safe(get_live_quote_angel, symbol.upper())
        if result and "error" not in result:
            return result
    return _safe(get_nse_quote, symbol.upper())


@app.get("/api/historical/{symbol}")
def historical(symbol: str, period: str = "1mo", interval: str = "1d"):
    """
    OHLCV data for charting.
    period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y
    interval: 1m, 5m, 15m, 1h, 1d, 1wk, 1mo

    When Angel One is configured, intraday data comes from Angel One (zero delay).
    Daily/weekly data always uses yfinance (more history depth).
    """
    from finstack.data.broker import get_candle_data_angel, _is_configured

    sym = symbol.upper()

    # Map frontend interval → Angel One interval string
    ANGEL_INTERVAL_MAP = {
        "1m":  "ONE_MINUTE",
        "3m":  "THREE_MINUTE",
        "5m":  "FIVE_MINUTE",
        "10m": "TEN_MINUTE",
        "15m": "FIFTEEN_MINUTE",
        "30m": "THIRTY_MINUTE",
        "60m": "ONE_HOUR",
        "1h":  "ONE_HOUR",
        "1d":  "ONE_DAY",
        "1wk": "ONE_WEEK",
        "1mo": "ONE_MONTH",
    }

    angel_interval = ANGEL_INTERVAL_MAP.get(interval.lower())
    is_intraday = interval.lower() in ("1m", "3m", "5m", "10m", "15m", "30m", "60m", "1h")

    # Use Angel One for intraday when configured (zero delay vs yfinance 15-min delay)
    if is_intraday and angel_interval and _is_configured():
        result = _safe(get_candle_data_angel, sym, interval=angel_interval)
        if result and "error" not in result and result.get("data"):
            return result
        # Fall through to yfinance on Angel One failure

    # Daily/weekly/monthly or Angel One fallback → yfinance
    from finstack.data.nse import get_historical_data
    return _safe(get_historical_data, sym, period=period, interval=interval)


@app.get("/api/fundamentals/{symbol}")
def fundamentals(symbol: str):
    """P/E, market cap, EPS, dividend yield, 52W range."""
    from finstack.data.fundamentals import get_key_ratios, get_company_profile
    ratios = _safe(get_key_ratios, symbol.upper())
    profile = _safe(get_company_profile, symbol.upper())
    return {"ratios": ratios, "profile": profile}


# ─── Options ──────────────────────────────────────────────────────────────────

@app.get("/api/options/{symbol}")
def options_chain(symbol: str):
    """Full NSE options chain with PCR and Max Pain."""
    from finstack.data.nse_advanced import get_options_chain
    from finstack.data.market_intelligence import get_options_oi_analytics
    chain = _safe(get_options_chain, symbol.upper())
    analytics = _safe(get_options_oi_analytics, symbol.upper())
    return {"chain": chain, "analytics": analytics}


@app.get("/api/greeks/{symbol}")
def options_greeks(symbol: str, expiry: str = None):
    from finstack.data.market_intelligence import get_options_greeks
    return _safe(get_options_greeks, symbol.upper(), expiry=expiry)


# ─── Market Intelligence ──────────────────────────────────────────────────────

@app.get("/api/fii-dii")
def fii_dii():
    from finstack.data.nse_advanced import get_fii_dii_data
    return _safe(get_fii_dii_data)


@app.get("/api/insider/{symbol}")
def insider_trading(symbol: str, days: int = 90):
    from finstack.data.market_intelligence import get_insider_trading
    return _safe(get_insider_trading, symbol.upper(), days=days)


@app.get("/api/promoter/{symbol}")
def promoter(symbol: str):
    from finstack.data.market_intelligence import get_promoter_shareholding, get_promoter_pledge
    shareholding = _safe(get_promoter_shareholding, symbol.upper())
    pledge = _safe(get_promoter_pledge, symbol.upper())
    return {"shareholding": shareholding, "pledge": pledge}


@app.get("/api/pcr")
def nifty_pcr():
    from finstack.data.market_intelligence import get_nifty_pcr_trend
    return _safe(get_nifty_pcr_trend)


# ─── Macro ────────────────────────────────────────────────────────────────────

@app.get("/api/macro")
def macro():
    """RBI rates, CPI, GDP, G-Sec yields, AMFI flows — one call."""
    from finstack.data.market_intelligence import (
        get_rbi_policy_rates,
        get_india_macro_indicators,
        get_india_gsec_yields,
        get_amfi_fund_flows,
    )
    return {
        "rbi": _safe(get_rbi_policy_rates),
        "macro": _safe(get_india_macro_indicators),
        "gsec": _safe(get_india_gsec_yields),
        "amfi": _safe(get_amfi_fund_flows),
    }


# ─── Screener ─────────────────────────────────────────────────────────────────

@app.get("/api/screener")
def screener(
    sector: str = "",
    min_pe: float = 0,
    max_pe: float = 999,
    min_roe: float = 0,
    market_cap: str = "all",
):
    from finstack.data.analytics import run_stock_screener
    return _safe(
        run_stock_screener,
        sector=sector or None,
        min_pe=min_pe,
        max_pe=max_pe,
        min_roe=min_roe,
        market_cap=market_cap,
    )


# ─── News ─────────────────────────────────────────────────────────────────────

@app.get("/api/news/{symbol}")
def news(symbol: str = ""):
    from finstack.data.global_markets import get_market_news
    return _safe(get_market_news, symbol.upper() if symbol else "")


# ─── Credit & ESG ─────────────────────────────────────────────────────────────

@app.get("/api/credit/{symbol}")
def credit_ratings(symbol: str):
    from finstack.data.credit_esg import get_credit_ratings
    return _safe(get_credit_ratings, symbol.upper())


@app.get("/api/esg/{symbol}")
def brsr_esg(symbol: str):
    from finstack.data.credit_esg import get_brsr_esg
    return _safe(get_brsr_esg, symbol.upper())


# ─── Intelligence ────────────────────────────────────────────────────────────

@app.get("/api/nifty-outlook")
def nifty_outlook():
    """Nifty direction probability: RSI + FII + PCR + VIX + G-Sec + GIFT Nifty → bull %."""
    from finstack.data.probability import get_nifty_outlook
    result = _safe(get_nifty_outlook)
    if isinstance(result, dict) and "error" not in result:
        return result
    return {"bull_probability": 55, "signal": "Neutral"}


@app.get("/api/stock-brief/{symbol}")
def stock_brief(symbol: str, rounds: int = 1):
    """Multi-agent AI debate: BUY/HOLD/SELL consensus with reasoning."""
    from finstack.data.agents import get_stock_brief, get_stock_debate
    if rounds >= 3:
        return _safe(get_stock_debate, symbol.upper())
    return _safe(get_stock_brief, symbol.upper())


@app.get("/api/smart-money/{symbol}")
def smart_money(symbol: str):
    """Smart money detector: OI buildup, block deals, promoter buying, volume spike."""
    from finstack.data.smart_money import detect_unusual_activity
    return _safe(detect_unusual_activity, symbol.upper())


@app.get("/api/signal-score/{symbol}")
def signal_score(symbol: str):
    """Automation-friendly signal score with factor breakdown."""
    from finstack.data.analytics import get_stock_signal_score
    return _safe(get_stock_signal_score, symbol.upper())


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.7.0", "tools": 83}


@app.get("/")
def root():
    return {
        "name": "FinStack Dashboard API",
        "version": "0.7.0",
        "tools": 83,
        "docs": "/docs",
        "endpoints": [
            "/api/market-status",
            "/api/nifty",
            "/api/vix",
            "/api/quote/{symbol}",
            "/api/historical/{symbol}",
            "/api/fundamentals/{symbol}",
            "/api/options/{symbol}",
            "/api/fii-dii",
            "/api/macro",
            "/api/screener",
            "/api/news/{symbol}",
            "/api/credit/{symbol}",
            "/api/esg/{symbol}",
            "/api/nifty-outlook",
            "/api/stock-brief/{symbol}",
            "/api/smart-money/{symbol}",
            "/api/signal-score/{symbol}",
        ],
    }
