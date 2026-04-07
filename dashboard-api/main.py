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

    Runs 8 indicators + VIX regime + PCR + OI analysis using finstack-mcp data.
    Returns BUY CE / BUY PE signals with score, regime, reasons, and suggested strike.

    VIX regimes:
      Sweet spot (11-20) → score ≥ 5/10
      Elevated  (20-28) → score ≥ 7/10
      Fear      (28-40) → score ≥ 8/10
    """
    from datetime import datetime, timezone
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

    def _pcr(symbol: str) -> float:
        try:
            from finstack.data.nse_advanced import get_options_chain
            chain = get_options_chain(symbol)
            if chain and isinstance(chain, dict):
                return float(chain.get("pcr") or chain.get("put_call_ratio") or 0)
        except Exception:
            pass
        return 0.0

    def _technicals(yf_symbol: str) -> dict:
        try:
            from finstack.data.analytics import compute_technical_indicators
            return compute_technical_indicators(yf_symbol) or {}
        except Exception:
            return {}

    def _spot(yf_symbol: str) -> float:
        try:
            info = yf.Ticker(yf_symbol).fast_info
            return round(float(getattr(info, "last_price", 0) or 0), 2)
        except Exception:
            return 0.0

    def _vix_regime(vix: float) -> tuple[str, int, float]:
        """Returns (regime_name, min_score, min_rr)"""
        if vix <= 0:
            return "unknown", 7, 2.5
        if vix < 11:
            return "dead", 99, 0       # will be blocked
        if vix <= 20:
            return "sweet", 5, 1.8
        if vix <= 28:
            return "elevated", 7, 2.5
        if vix <= 40:
            return "fear", 8, 3.0
        return "panic", 99, 0          # will be blocked

    def _atm_strike(spot: float, step: int) -> int:
        return round(spot / step) * step

    vix = _vix()
    regime, min_score, min_rr = _vix_regime(vix)

    # Block dead/panic regimes
    if regime in ("dead", "panic"):
        return {
            "signals": [],
            "vix": vix,
            "regime": regime,
            "message": f"VIX {vix} — {regime} zone. No trades recommended.",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    for symbol, yf_sym, step in [
        ("NIFTY",     "^NSEI",    50),
        ("BANKNIFTY", "^NSEBANK", 100),
    ]:
        tech  = _technicals(yf_sym)
        spot  = _spot(yf_sym) or tech.get("current_price", 0)
        pcr   = _pcr(symbol)

        reasons, blocks = [], []
        score = 0
        direction = None

        rsi = tech.get("rsi_14") or tech.get("rsi")

        # ── Bull scoring ──────────────────────────────────────────────────────
        bull = 0
        if rsi and rsi < 45:
            bull += 1; reasons.append(f"RSI {rsi:.1f} — oversold/recovering")
        macd_line = tech.get("macd_line")
        macd_sig  = tech.get("macd_signal")
        if macd_line and macd_sig and macd_line > macd_sig:
            bull += 1; reasons.append("MACD bullish crossover")
        vwap = tech.get("vwap")
        price = tech.get("current_price") or spot
        if vwap and price and price > vwap:
            bull += 1; reasons.append(f"Price above VWAP {vwap:.0f}")
        if 0 < pcr <= 0.8:
            bull += 1; reasons.append(f"PCR {pcr:.2f} — bullish sentiment")
        bb_upper = tech.get("bb_upper")
        bb_lower = tech.get("bb_lower")
        if bb_lower and price and price < bb_lower * 1.01:
            bull += 1; reasons.append("Near Bollinger lower band — bounce zone")
        sma20 = tech.get("sma_20")
        if sma20 and price and price > sma20:
            bull += 1; reasons.append(f"Price above SMA20 {sma20:.0f}")
        if vix > 20:
            bull += 1; reasons.append(f"High VIX {vix:.1f} = contrarian buy on dip")

        # ── Bear scoring ──────────────────────────────────────────────────────
        bear = 0
        bear_reasons: list = []
        if rsi and rsi > 60:
            bear += 1; bear_reasons.append(f"RSI {rsi:.1f} — overbought")
        if macd_line and macd_sig and macd_line < macd_sig:
            bear += 1; bear_reasons.append("MACD bearish crossover")
        if vwap and price and price < vwap:
            bear += 1; bear_reasons.append(f"Price below VWAP {vwap:.0f}")
        if pcr >= 1.25:
            bear += 1; bear_reasons.append(f"PCR {pcr:.2f} — bearish sentiment")
        if bb_upper and price and price > bb_upper * 0.99:
            bear += 1; bear_reasons.append("Near Bollinger upper band — reversal zone")
        if sma20 and price and price < sma20:
            bear += 1; bear_reasons.append(f"Price below SMA20 {sma20:.0f}")

        # ── Determine direction ───────────────────────────────────────────────
        if bull >= min_score and bull > bear:
            direction = "BUY_CE"
            score = bull
        elif bear >= min_score and bear > bull:
            direction = "BUY_PE"
            score = bear
            reasons = bear_reasons

        if not direction:
            results.append({
                "symbol": symbol,
                "direction": None,
                "score": max(bull, bear),
                "min_score": min_score,
                "regime": regime,
                "vix": vix,
                "spot": spot,
                "pcr": pcr,
                "message": f"No signal — bull={bull} bear={bear} need={min_score}",
            })
            continue

        atm = _atm_strike(spot, step)
        option_type = "CE" if direction == "BUY_CE" else "PE"
        suggested_strike = atm  # ATM for best balance
        tradingsymbol = f"{symbol}{suggested_strike}{option_type}"

        results.append({
            "symbol": symbol,
            "direction": direction,
            "option_type": option_type,
            "score": score,
            "max_score": 7,
            "min_score": min_score,
            "confidence_pct": round(score / 7 * 100),
            "regime": regime,
            "vix": vix,
            "min_rr": min_rr,
            "spot": spot,
            "pcr": pcr,
            "atm_strike": atm,
            "suggested_strike": suggested_strike,
            "suggested_symbol": tradingsymbol,
            "reasons": reasons,
            "blocks": blocks,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        })

    return {
        "signals": results,
        "vix": vix,
        "regime": regime,
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
