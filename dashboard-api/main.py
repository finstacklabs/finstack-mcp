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
import asyncio
from pathlib import Path

# Add finstack-mcp src to path so we can import data functions directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI(title="FinStack Dashboard API", version="0.9.0")

# ─── Telegram bot startup ─────────────────────────────────────────────────────

_tg_poll_task = None

@app.on_event("startup")
async def start_telegram_polling():
    """
    Use webhook mode when SELF_API_BASE is set (production on Railway).
    Fall back to long-polling for local development.
    """
    global _tg_poll_task
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("[startup] TELEGRAM_BOT_TOKEN not set — Telegram disabled")
        return

    self_url = os.getenv("SELF_API_BASE", "").strip()
    if self_url:
        # Production: register webhook so Telegram pushes to us
        webhook_url = f"{self_url}/api/telegram/webhook"
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"https://api.telegram.org/bot{token}/setWebhook",
                    json={"url": webhook_url, "allowed_updates": ["message"]},
                )
                result = r.json()
                if result.get("ok"):
                    print(f"[startup] Telegram webhook registered: {webhook_url}")
                else:
                    print(f"[startup] Webhook registration failed: {result} — falling back to polling")
                    _tg_poll_task = asyncio.create_task(_poll_forever_safe())
        except Exception as e:
            print(f"[startup] Webhook setup error: {e} — falling back to polling")
            _tg_poll_task = asyncio.create_task(_poll_forever_safe())
    else:
        # Local dev: use long-polling
        _tg_poll_task = asyncio.create_task(_poll_forever_safe())
        print("[startup] Telegram polling started (local dev)")


async def _poll_forever_safe():
    try:
        from telegram_bot import poll_forever
        await poll_forever()
    except Exception as e:
        print(f"[telegram] Poll task crashed: {e}")


@app.on_event("startup")
async def start_morning_brief_scheduler():
    """Schedule morning brief at 9:00 AM IST every day."""
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        return

    async def _scheduler():
        from telegram_bot import broadcast_morning_brief
        from datetime import datetime, timezone, timedelta
        IST = timezone(timedelta(hours=5, minutes=30))
        while True:
            now = datetime.now(IST)
            # Next 9:00 AM IST
            target = now.replace(hour=9, minute=0, second=0, microsecond=0)
            if now >= target:
                target = target + timedelta(days=1)
            wait_secs = (target - now).total_seconds()
            print(f"[scheduler] Morning brief in {wait_secs/3600:.1f}h")
            await asyncio.sleep(wait_secs)
            await broadcast_morning_brief()

    asyncio.create_task(_scheduler())
    print("[startup] Morning brief scheduler started (9:00 AM IST daily)")

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


@app.get("/api/search")
def symbol_search(q: str = ""):
    """Search NSE/BSE symbols via yfinance. Returns up to 15 results."""
    if not q or len(q) < 1:
        return {"results": []}
    try:
        import yfinance as yf
        search = yf.Search(q, max_results=15, news_count=0)
        quotes = getattr(search, "quotes", []) or []
        results = []
        for item in quotes:
            sym = item.get("symbol", "")
            # Prefer NSE (.NS) and BSE (.BO) symbols, also accept plain Indian symbols
            exch = item.get("exchange", "")
            type_ = item.get("quoteType", "")
            if type_ not in ("EQUITY", "ETF", "INDEX", "MUTUALFUND") and type_:
                continue
            results.append({
                "symbol": sym.replace(".NS", "").replace(".BO", "") if sym.endswith((".NS", ".BO")) else sym,
                "raw_symbol": sym,
                "name": item.get("longname") or item.get("shortname") or sym,
                "exchange": exch,
                "type": type_,
                "is_india": sym.endswith(".NS") or sym.endswith(".BO") or exch in ("NSI", "BSE"),
            })
        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}


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
    filter: str = "gainers",
    sector: str = "",
    min_pe: float = 0,
    max_pe: float = 999,
    min_roe: float = 0,
    market_cap: str = "all",
):
    from finstack.data.analytics import screen_stocks
    # Map UI filter names to screener params
    filter_map = {
        "gainers": dict(min_roe=0, market_cap="all"),
        "losers":  dict(min_roe=0, market_cap="all"),
        "volume":  dict(min_roe=0, market_cap="all"),
        "low_pe":  dict(min_pe=0, max_pe=15, market_cap="all"),
    }
    params = filter_map.get(filter, {})
    result = _safe(
        screen_stocks,
        sector=sector or None,
        min_pe=params.get("min_pe", min_pe),
        max_pe=params.get("max_pe", max_pe),
        min_roe=params.get("min_roe", min_roe),
        market_cap=params.get("market_cap", market_cap),
    )
    # Sort results by filter type
    if isinstance(result, dict) and "results" in result:
        rows = result["results"]
        if filter == "gainers":
            rows = sorted(rows, key=lambda r: r.get("change_pct", 0), reverse=True)
        elif filter == "losers":
            rows = sorted(rows, key=lambda r: r.get("change_pct", 0))
        elif filter == "volume":
            rows = sorted(rows, key=lambda r: r.get("volume", 0), reverse=True)
        elif filter == "low_pe":
            rows = [r for r in rows if r.get("pe") and r["pe"] > 0]
            rows = sorted(rows, key=lambda r: r.get("pe", 999))
        result["results"] = rows[:15]
    return result


# ─── F&O Signals (nifty-agent engine via finstack-mcp data) ──────────────────

@app.get("/api/fno-signals")
def fno_signals():
    """
    Nifty/BankNifty F&O signal engine.

    Runs 8 indicators + VIX regime + PCR using finstack-mcp data.
    Returns BUY CE / BUY PE signals with score, regime, reasons, and suggested strike.

    VIX regimes:
      Sweet spot (11-20) → score ≥ 5/8
      Elevated  (20-28) → score ≥ 6/8
      Fear      (28-40) → score ≥ 7/8
    """
    from datetime import datetime, timezone
    import pandas as pd
    import yfinance as yf

    results = []

    def _vix() -> float:
        try:
            hist = yf.Ticker("^INDIAVIX").history(period="2d")
            if not hist.empty:
                return round(float(hist["Close"].iloc[-1]), 2)
        except Exception:
            pass
        return 0.0

    def _pcr(yf_sym: str) -> float:
        """Calculate PCR from yfinance options OI for index tickers (^NSEI, ^NSEBANK)."""
        try:
            ticker = yf.Ticker(yf_sym)
            expiries = ticker.options
            if not expiries:
                return 0.0
            chain = ticker.option_chain(expiries[0])
            call_oi = chain.calls["openInterest"].fillna(0).sum()
            put_oi  = chain.puts["openInterest"].fillna(0).sum()
            return round(float(put_oi / call_oi), 2) if call_oi > 0 else 0.0
        except Exception:
            return 0.0

    def _indicators(yf_sym: str) -> dict:
        """
        Fetch 6mo daily OHLCV + 1d 5min intraday and return flat indicator dict.
        Keys: rsi, macd, macd_signal, vwap, bb_upper, bb_lower, sma20, price
        """
        try:
            ticker = yf.Ticker(yf_sym)
            hist = ticker.history(period="6mo", interval="1d")
            if hist.empty or len(hist) < 20:
                return {}
            close = hist["Close"]

            # RSI 14
            delta = close.diff()
            gain  = delta.where(delta > 0, 0).rolling(14).mean()
            loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs    = gain / loss.replace(0, float("nan"))
            rsi   = float((100 - 100 / (1 + rs)).iloc[-1])

            # MACD (12,26,9)
            ema12       = close.ewm(span=12, adjust=False).mean()
            ema26       = close.ewm(span=26, adjust=False).mean()
            macd_line   = float((ema12 - ema26).iloc[-1])
            macd_signal = float((ema12 - ema26).ewm(span=9, adjust=False).mean().iloc[-1])

            # Bollinger Bands (20,2)
            sma20    = close.rolling(20).mean()
            std20    = close.rolling(20).std()
            bb_upper = float((sma20 + std20 * 2).iloc[-1])
            bb_lower = float((sma20 - std20 * 2).iloc[-1])
            sma20_v  = float(sma20.iloc[-1])

            price = float(close.iloc[-1])

            # Intraday VWAP — use today's 5m candles
            vwap = None
            try:
                intra = ticker.history(period="1d", interval="5m")
                if not intra.empty:
                    tp  = (intra["High"] + intra["Low"] + intra["Close"]) / 3
                    cum_vol = intra["Volume"].cumsum()
                    if cum_vol.iloc[-1] > 0:
                        vwap = float((tp * intra["Volume"]).cumsum().iloc[-1] / cum_vol.iloc[-1])
            except Exception:
                pass

            return {
                "rsi": round(rsi, 2),
                "macd": round(macd_line, 2),
                "macd_signal": round(macd_signal, 2),
                "bb_upper": round(bb_upper, 2),
                "bb_lower": round(bb_lower, 2),
                "sma20": round(sma20_v, 2),
                "price": round(price, 2),
                "vwap": round(vwap, 2) if vwap else None,
            }
        except Exception:
            return {}

    def _spot(yf_sym: str) -> float:
        try:
            info = yf.Ticker(yf_sym).fast_info
            return round(float(getattr(info, "last_price", 0) or 0), 2)
        except Exception:
            return 0.0

    def _vix_regime(vix: float) -> tuple[str, int, float]:
        if vix <= 0:   return "unknown",  6, 2.5
        if vix < 11:   return "dead",    99, 0
        if vix <= 20:  return "sweet",    5, 1.8
        if vix <= 28:  return "elevated", 6, 2.5
        if vix <= 40:  return "fear",     7, 3.0
        return "panic", 99, 0

    def _atm(spot: float, step: int) -> int:
        return int(round(spot / step) * step)

    vix = _vix()
    regime, min_score, min_rr = _vix_regime(vix)

    if regime in ("dead", "panic"):
        return {
            "signals": [],
            "vix": vix,
            "regime": regime,
            "market_status": f"VIX {vix} — {regime} zone. No trades.",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    for symbol, yf_sym, step in [
        ("NIFTY",     "^NSEI",    50),
        ("BANKNIFTY", "^NSEBANK", 100),
    ]:
        ind   = _indicators(yf_sym)
        spot  = _spot(yf_sym) or ind.get("price", 0)
        pcr   = _pcr(yf_sym)

        price     = ind.get("price") or spot
        rsi       = ind.get("rsi")
        macd      = ind.get("macd")
        macd_sig  = ind.get("macd_signal")
        vwap      = ind.get("vwap")
        bb_upper  = ind.get("bb_upper")
        bb_lower  = ind.get("bb_lower")
        sma20     = ind.get("sma20")

        # ── Bull scoring (max 8) ──────────────────────────────────────────────
        bull_r: list[str] = []
        bull = 0
        if rsi and rsi < 45:
            bull += 1; bull_r.append(f"RSI {rsi:.1f} — recovering from oversold")
        if macd is not None and macd_sig is not None and macd > macd_sig:
            bull += 1; bull_r.append(f"MACD bullish ({macd:.1f} > signal {macd_sig:.1f})")
        if vwap and price and price > vwap:
            bull += 1; bull_r.append(f"Price {price:.0f} above VWAP {vwap:.0f}")
        if 0 < pcr <= 0.8:
            bull += 1; bull_r.append(f"PCR {pcr:.2f} — bullish sentiment")
        if bb_lower and price and price < bb_lower * 1.005:
            bull += 1; bull_r.append(f"Near Bollinger lower band {bb_lower:.0f} — bounce zone")
        if sma20 and price and price > sma20:
            bull += 1; bull_r.append(f"Price above SMA20 {sma20:.0f}")
        if vix > 20:
            bull += 1; bull_r.append(f"VIX {vix:.1f} elevated — contrarian CE opportunity")
        if rsi and macd is not None and macd_sig is not None and rsi < 50 and macd > macd_sig:
            bull += 1; bull_r.append("RSI + MACD both confirming bullish bias")

        # ── Bear scoring (max 8) ──────────────────────────────────────────────
        bear_r: list[str] = []
        bear = 0
        if rsi and rsi > 60:
            bear += 1; bear_r.append(f"RSI {rsi:.1f} — overbought")
        if macd is not None and macd_sig is not None and macd < macd_sig:
            bear += 1; bear_r.append(f"MACD bearish ({macd:.1f} < signal {macd_sig:.1f})")
        if vwap and price and price < vwap:
            bear += 1; bear_r.append(f"Price {price:.0f} below VWAP {vwap:.0f}")
        if pcr >= 1.25:
            bear += 1; bear_r.append(f"PCR {pcr:.2f} — high put buying, bearish")
        if bb_upper and price and price > bb_upper * 0.995:
            bear += 1; bear_r.append(f"Near Bollinger upper band {bb_upper:.0f} — reversal risk")
        if sma20 and price and price < sma20:
            bear += 1; bear_r.append(f"Price below SMA20 {sma20:.0f} — downtrend")
        if vix > 25:
            bear += 1; bear_r.append(f"VIX {vix:.1f} — elevated fear, PE premium inflated")
        if rsi and macd is not None and macd_sig is not None and rsi > 55 and macd < macd_sig:
            bear += 1; bear_r.append("RSI + MACD both confirming bearish bias")

        # ── Direction ─────────────────────────────────────────────────────────
        if bull >= min_score and bull > bear:
            direction = "BUY_CE"
            score = bull
            reasons = bull_r
        elif bear >= min_score and bear > bull:
            direction = "BUY_PE"
            score = bear
            reasons = bear_r
        else:
            results.append({
                "symbol": symbol, "direction": "NO_SIGNAL",
                "score": max(bull, bear), "min_score": min_score,
                "regime": regime, "vix": vix, "spot": spot, "pcr": pcr,
                "reasons": [],
                "message": f"No signal — bull={bull} bear={bear} need={min_score}",
            })
            continue

        atm_strike = _atm(spot, step)
        opt_type   = "CE" if direction == "BUY_CE" else "PE"
        trading_sym = f"{symbol}{atm_strike}{opt_type}"

        results.append({
            "symbol": symbol,
            "direction": direction,
            "option_type": opt_type,
            "score": score,
            "max_score": 8,
            "min_score": min_score,
            "confidence_pct": round(score / 8 * 100),
            "regime": regime,
            "vix": vix,
            "min_rr": min_rr,
            "spot": spot,
            "pcr": pcr,
            "atm_strike": atm_strike,
            "trading_symbol": trading_sym,
            "reasons": reasons,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        })

    return {
        "signals": results,
        "vix": vix,
        "regime": regime,
        "market_status": f"Live · regime={regime} · need {min_score}/8",
        "min_score_needed": min_score,
        "min_rr_needed": min_rr,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


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


# ─── Telegram ────────────────────────────────────────────────────────────────

@app.post("/api/telegram/webhook")
async def telegram_webhook(update: dict):
    """
    Telegram pushes updates here in webhook mode.
    Returns inline reply so Railway never needs outbound calls to api.telegram.org.
    """
    from telegram_bot import handle_update
    reply = await handle_update(update)
    if reply:
        return reply  # Telegram reads this and sends the message on our behalf
    return {"ok": True}


@app.get("/api/telegram/status")
async def telegram_status():
    """Is Telegram bot configured and running?"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return {"enabled": False, "reason": "TELEGRAM_BOT_TOKEN not set"}
    try:
        from telegram_bot import tg_get
        info = await tg_get("getMe")
        bot = info.get("result", {})
        return {
            "enabled": True,
            "bot_username": bot.get("username"),
            "bot_name": bot.get("first_name"),
            "bot_url": f"https://t.me/{bot.get('username')}",
        }
    except Exception as e:
        return {"enabled": False, "error": str(e)}


@app.post("/api/telegram/send-alert")
async def send_alert(payload: dict):
    """
    Called by Arthex when a price alert fires.
    Body: { symbol, condition, price, current, chat_ids? }
    """
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        return {"sent": 0, "reason": "bot not configured"}
    from telegram_bot import send_alert_to_subscribers
    chat_ids = payload.get("chat_ids")
    await send_alert_to_subscribers(
        symbol=payload.get("symbol", ""),
        condition=payload.get("condition", ""),
        price=float(payload.get("price", 0)),
        current=float(payload.get("current", 0)),
        chat_ids=chat_ids,
    )
    return {"sent": len(chat_ids) if chat_ids else "all"}


@app.post("/api/telegram/send-battle")
async def send_battle(payload: dict):
    """
    Called after an Agent Battle completes.
    Body: { chat_id, symbol, signal, strength, avg_score, note }
    """
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        return {"sent": False, "reason": "bot not configured"}
    from telegram_bot import send_battle_to_chat
    await send_battle_to_chat(
        chat_id=str(payload["chat_id"]),
        symbol=payload.get("symbol", ""),
        signal=payload.get("signal", ""),
        strength=payload.get("strength", ""),
        avg_score=float(payload.get("avg_score", 0)),
        note=payload.get("note", ""),
    )
    return {"sent": True}


@app.post("/api/telegram/broadcast-brief")
async def trigger_brief():
    """Manually trigger morning brief broadcast (for testing)."""
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        return {"sent": 0, "reason": "bot not configured"}
    from telegram_bot import broadcast_morning_brief
    await broadcast_morning_brief()
    return {"ok": True}


# ─── Payments (Razorpay) ─────────────────────────────────────────────────────
#
# Flow:
#   1. Frontend calls POST /api/payment/create-order  → gets order_id
#   2. Razorpay checkout opens with order_id
#   3. User pays → Razorpay calls handler with { razorpay_payment_id, razorpay_order_id, razorpay_signature }
#   4. Frontend sends those 3 fields to POST /api/payment/verify
#   5. Backend verifies HMAC signature → stores pro status in Supabase → returns ok
#
# Env vars needed (Railway):
#   RAZORPAY_KEY_ID      — from Razorpay dashboard (starts with rzp_live_ or rzp_test_)
#   RAZORPAY_KEY_SECRET  — from Razorpay dashboard
#   SUPABASE_URL         — your Supabase project URL
#   SUPABASE_SERVICE_KEY — service role key (for server-side writes)

_RZP_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "")
_RZP_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
_SB_URL         = os.getenv("SUPABASE_URL", "")
_SB_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

PRO_AMOUNT_PAISE = 29900   # ₹299/month


@app.post("/api/payment/create-order")
async def payment_create_order(body: dict):
    """
    Create a Razorpay order. Frontend must send { chat_id } to link payment to subscriber.
    Returns { order_id, key_id, amount } for the Razorpay checkout.
    """
    if not _RZP_KEY_ID or not _RZP_KEY_SECRET:
        raise HTTPException(503, "Razorpay not configured on server")

    import razorpay
    client = razorpay.Client(auth=(_RZP_KEY_ID, _RZP_KEY_SECRET))
    order = client.order.create({
        "amount": PRO_AMOUNT_PAISE,
        "currency": "INR",
        "receipt": f"finstack_{body.get('chat_id', 'anon')}",
        "notes": {"chat_id": str(body.get("chat_id", "")), "email": str(body.get("email", ""))},
    })
    return {"order_id": order["id"], "key_id": _RZP_KEY_ID, "amount": PRO_AMOUNT_PAISE}


@app.post("/api/payment/verify")
async def payment_verify(body: dict):
    """
    Verify Razorpay payment signature and grant Pro access.
    Frontend sends { razorpay_payment_id, razorpay_order_id, razorpay_signature, chat_id, email }.
    """
    if not _RZP_KEY_SECRET:
        raise HTTPException(503, "Razorpay not configured on server")

    import hmac, hashlib, razorpay

    payment_id = body.get("razorpay_payment_id", "")
    order_id   = body.get("razorpay_order_id", "")
    signature  = body.get("razorpay_signature", "")

    # Verify HMAC-SHA256 signature
    expected = hmac.new(
        _RZP_KEY_SECRET.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(400, "Payment signature verification failed")

    # Store Pro status in Supabase (best-effort — don't fail payment if Supabase is down)
    chat_id = str(body.get("chat_id", ""))
    email   = str(body.get("email", ""))
    if _SB_URL and _SB_SERVICE_KEY and (chat_id or email):
        try:
            import httpx as _httpx
            sb_headers = {
                "apikey": _SB_SERVICE_KEY,
                "Authorization": f"Bearer {_SB_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            }
            async with _httpx.AsyncClient(timeout=5) as hc:
                await hc.post(
                    f"{_SB_URL}/rest/v1/pro_subscribers",
                    headers=sb_headers,
                    json={
                        "chat_id": chat_id or None,
                        "email": email or None,
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "active": True,
                    },
                )
        except Exception:
            pass  # Supabase failure does not block payment confirmation

    return {"ok": True, "payment_id": payment_id, "message": "Pro access granted"}


@app.get("/api/payment/status")
async def payment_status(chat_id: str = "", email: str = ""):
    """Check if a user has active Pro subscription."""
    if not _SB_URL or not _SB_SERVICE_KEY:
        return {"is_pro": False, "reason": "payment system not configured"}
    if not chat_id and not email:
        return {"is_pro": False}

    try:
        import httpx as _httpx
        sb_headers = {
            "apikey": _SB_SERVICE_KEY,
            "Authorization": f"Bearer {_SB_SERVICE_KEY}",
        }
        params = {"active": "eq.true", "select": "chat_id,email,payment_id"}
        if chat_id:
            params["chat_id"] = f"eq.{chat_id}"
        elif email:
            params["email"] = f"eq.{email}"

        async with _httpx.AsyncClient(timeout=5) as hc:
            r = await hc.get(
                f"{_SB_URL}/rest/v1/pro_subscribers",
                headers=sb_headers,
                params=params,
            )
        rows = r.json() if r.status_code == 200 else []
        return {"is_pro": len(rows) > 0}
    except Exception:
        return {"is_pro": False, "reason": "lookup failed"}


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    tg_enabled = bool(os.getenv("TELEGRAM_BOT_TOKEN"))
    return {"status": "ok", "version": "0.9.0", "tools": 90, "telegram": tg_enabled}


@app.get("/")
def root():
    return {
        "name": "FinStack Dashboard API",
        "version": "0.9.0",
        "tools": 90,
        "docs": "/docs",
        "telegram_bot": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
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
            "/api/telegram/status",
            "/api/telegram/send-alert",
            "/api/telegram/broadcast-brief",
        ],
    }
