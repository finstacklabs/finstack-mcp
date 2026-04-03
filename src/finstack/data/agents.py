"""
Multi-agent stock brief for FinStack MCP.

4 AI personas debate a stock using real Indian market data:
  • FII Desk        — institutional flows, promoter holding, shareholding pattern
  • Algo Trader     — RSI, MACD, VWAP, volume anomaly
  • Value Investor  — P/E, ROE, debt ratios, credit rating
  • Retail Pulse    — news tone, 52W position, VIX level, social buzz

Output: structured 4-agent debate → consensus signal (BUY/HOLD/SELL) + reasoning.

No external AI API needed — each "agent" is a deterministic rule engine that
reads real finstack data and produces structured analysis. Claude (the host LLM)
can then roleplay the debate using the structured inputs if desired.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("finstack.agents")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.debug("Agent data fetch error: %s", e)
        return None


def _signal_score(signal: str) -> int:
    """BUY=1, HOLD=0, SELL=-1."""
    return {"BUY": 1, "HOLD": 0, "SELL": -1}.get(signal.upper(), 0)


# ── Agent 1: FII Desk ─────────────────────────────────────────────────────────

def _fii_desk_analysis(symbol: str) -> dict:
    """Institutional flow + shareholding analysis."""
    from finstack.data.market_intelligence import get_fii_dii_data, get_promoter_shareholding

    fii_dii = _safe(get_fii_dii_data)
    promoter = _safe(get_promoter_shareholding, symbol)

    # Parse FII net flow
    fii_net_5d = 0.0
    if fii_dii and isinstance(fii_dii, list):
        nets = [d.get("fii_net_cr", 0) for d in fii_dii[:5] if isinstance(d, dict)]
        fii_net_5d = sum(nets)

    # Parse promoter holding
    promoter_pct = None
    fii_holding_pct = None
    if promoter and isinstance(promoter, dict):
        sh = promoter.get("shareholding", {})
        promoter_pct  = sh.get("promoter_pct")
        fii_holding_pct = sh.get("fii_pct")

    # Build signal
    reasoning = []
    score = 0

    if fii_net_5d > 1000:
        reasoning.append(f"FII net buying ₹{fii_net_5d:,.0f}Cr over 5 days — strong institutional interest")
        score += 1
    elif fii_net_5d < -1000:
        reasoning.append(f"FII net selling ₹{abs(fii_net_5d):,.0f}Cr over 5 days — institutional exit in progress")
        score -= 1
    else:
        reasoning.append(f"FII flows neutral (₹{fii_net_5d:,.0f}Cr net 5d)")

    if promoter_pct and promoter_pct >= 50:
        reasoning.append(f"Promoter holding {promoter_pct:.1f}% — strong founder conviction")
        score += 0.5
    elif promoter_pct and promoter_pct < 30:
        reasoning.append(f"Promoter holding only {promoter_pct:.1f}% — low skin-in-the-game")
        score -= 0.5

    if fii_holding_pct and fii_holding_pct >= 25:
        reasoning.append(f"FII holding {fii_holding_pct:.1f}% — globally in demand")
        score += 0.5

    signal = "BUY" if score >= 1 else ("SELL" if score <= -1 else "HOLD")

    return {
        "agent": "FII Desk",
        "signal": signal,
        "score": score,
        "data": {
            "fii_net_5d_cr": fii_net_5d,
            "promoter_pct": promoter_pct,
            "fii_holding_pct": fii_holding_pct,
        },
        "reasoning": reasoning,
        "one_liner": f"{'Accumulating' if signal=='BUY' else ('Distributing' if signal=='SELL' else 'Neutral')} — "
                     f"FII 5d flow ₹{fii_net_5d:,.0f}Cr",
    }


# ── Agent 2: Algo Trader ──────────────────────────────────────────────────────

def _algo_trader_analysis(symbol: str) -> dict:
    """Technical indicators: RSI, MACD, VWAP, volume."""
    from finstack.data.analytics import compute_technical_indicators

    tech = _safe(compute_technical_indicators, f"{symbol}.NS")

    rsi = None
    macd_signal = None
    price_vs_vwap = None
    vol_ratio = None

    if tech and isinstance(tech, dict):
        rsi = tech.get("rsi_14")
        macd_line = tech.get("macd_line")
        macd_sig   = tech.get("macd_signal")
        if macd_line is not None and macd_sig is not None:
            macd_signal = "bullish" if macd_line > macd_sig else "bearish"
        vwap  = tech.get("vwap")
        price = tech.get("current_price")
        if vwap and price:
            price_vs_vwap = "above" if price > vwap else "below"
        avg_vol = tech.get("avg_volume_20d")
        cur_vol = tech.get("current_volume")
        if avg_vol and cur_vol and avg_vol > 0:
            vol_ratio = round(cur_vol / avg_vol, 2)

    reasoning = []
    score = 0

    if rsi:
        if rsi < 35:
            reasoning.append(f"RSI {rsi:.1f} — oversold, potential bounce")
            score += 1
        elif rsi > 65:
            reasoning.append(f"RSI {rsi:.1f} — overbought, momentum may fade")
            score -= 0.5
        else:
            reasoning.append(f"RSI {rsi:.1f} — neutral momentum zone")

    if macd_signal == "bullish":
        reasoning.append("MACD above signal line — uptrend momentum")
        score += 0.5
    elif macd_signal == "bearish":
        reasoning.append("MACD below signal line — downtrend momentum")
        score -= 0.5

    if price_vs_vwap == "above":
        reasoning.append("Price above VWAP — intraday bulls in control")
        score += 0.5
    elif price_vs_vwap == "below":
        reasoning.append("Price below VWAP — intraday selling pressure")
        score -= 0.5

    if vol_ratio and vol_ratio >= 2.0:
        reasoning.append(f"Volume {vol_ratio}x average — unusual activity, follow direction")
        score += 0.5 if score > 0 else -0.5

    signal = "BUY" if score >= 1 else ("SELL" if score <= -1 else "HOLD")

    return {
        "agent": "Algo Trader",
        "signal": signal,
        "score": score,
        "data": {
            "rsi_14": rsi,
            "macd_signal": macd_signal,
            "price_vs_vwap": price_vs_vwap,
            "volume_ratio": vol_ratio,
        },
        "reasoning": reasoning,
        "one_liner": f"Technicals {'bullish' if signal=='BUY' else ('bearish' if signal=='SELL' else 'mixed')} — RSI {rsi:.1f}" if rsi else "Technical data unavailable",
    }


# ── Agent 3: Value Investor ───────────────────────────────────────────────────

def _value_investor_analysis(symbol: str) -> dict:
    """Fundamental ratios + credit rating analysis."""
    from finstack.data.fundamentals import get_key_ratios
    from finstack.data.credit_esg import get_credit_ratings

    ratios  = _safe(get_key_ratios, f"{symbol}.NS")
    credit  = _safe(get_credit_ratings, symbol)

    pe = roe = debt_equity = None
    credit_rating = None

    if ratios and isinstance(ratios, dict):
        pe           = ratios.get("pe_ratio") or ratios.get("trailingPE")
        roe          = ratios.get("roe") or ratios.get("returnOnEquity")
        debt_equity  = ratios.get("debt_to_equity") or ratios.get("debtToEquity")
        if roe and roe < 1:  # convert from decimal if needed
            roe = roe * 100

    if credit and isinstance(credit, dict):
        ratings = credit.get("ratings", [])
        if ratings:
            credit_rating = ratings[0].get("rating") if isinstance(ratings[0], dict) else str(ratings[0])

    reasoning = []
    score = 0

    if pe:
        if pe < 15:
            reasoning.append(f"P/E {pe:.1f}x — attractive valuation vs market average")
            score += 1
        elif pe > 40:
            reasoning.append(f"P/E {pe:.1f}x — expensive, needs high growth to justify")
            score -= 0.5
        else:
            reasoning.append(f"P/E {pe:.1f}x — fair valued")

    if roe:
        if roe > 20:
            reasoning.append(f"ROE {roe:.1f}% — excellent capital efficiency")
            score += 1
        elif roe < 10:
            reasoning.append(f"ROE {roe:.1f}% — weak returns on equity")
            score -= 0.5

    if debt_equity is not None:
        if debt_equity > 2:
            reasoning.append(f"D/E {debt_equity:.1f}x — high leverage, watch refinancing risk")
            score -= 0.5
        elif debt_equity < 0.5:
            reasoning.append(f"D/E {debt_equity:.1f}x — low debt, financially strong")
            score += 0.5

    if credit_rating:
        if credit_rating.startswith("AAA") or credit_rating.startswith("AA+"):
            reasoning.append(f"Credit rating {credit_rating} — highest quality debt")
            score += 0.5
        elif any(credit_rating.startswith(x) for x in ["BB", "B", "C"]):
            reasoning.append(f"Credit rating {credit_rating} — below investment grade, elevated risk")
            score -= 1

    signal = "BUY" if score >= 1 else ("SELL" if score <= -1 else "HOLD")

    return {
        "agent": "Value Investor",
        "signal": signal,
        "score": score,
        "data": {
            "pe_ratio": pe,
            "roe_pct": roe,
            "debt_equity": debt_equity,
            "credit_rating": credit_rating,
        },
        "reasoning": reasoning,
        "one_liner": f"Fundamentals {'attractive' if signal=='BUY' else ('weak' if signal=='SELL' else 'fair')} — P/E {pe:.1f}x, ROE {roe:.1f}%" if pe and roe else "Fundamental data unavailable",
    }


# ── Agent 4: Retail Pulse ─────────────────────────────────────────────────────

def _retail_pulse_analysis(symbol: str) -> dict:
    """News tone + 52W position + VIX sentiment."""
    from finstack.data.market_intelligence import get_india_vix
    from finstack.data.global_markets import get_market_news

    vix_data  = _safe(get_india_vix)
    news_data = _safe(get_market_news, symbol, max_results=10)

    vix_value = None
    news_tone = "neutral"
    pos_52w   = None

    if vix_data and isinstance(vix_data, dict):
        vix_value = vix_data.get("vix") or vix_data.get("current")

    # Quick news tone from headlines
    if news_data and isinstance(news_data, list):
        bullish_words = {"beat", "surge", "rally", "growth", "record", "profit", "buy", "upgrade"}
        bearish_words = {"miss", "fall", "crash", "loss", "cut", "sell", "downgrade", "concern", "risk"}
        b, s = 0, 0
        for item in news_data:
            title = (item.get("title") or item.get("headline") or "").lower()
            b += sum(1 for w in bullish_words if w in title)
            s += sum(1 for w in bearish_words if w in title)
        news_tone = "bullish" if b > s else ("bearish" if s > b else "neutral")

    # 52W position from yfinance
    try:
        import yfinance as yf
        info = yf.Ticker(f"{symbol}.NS").fast_info
        high52 = getattr(info, "year_high", None)
        low52  = getattr(info, "year_low", None)
        last   = getattr(info, "last_price", None)
        if high52 and low52 and last and (high52 - low52) > 0:
            pos_52w = round((last - low52) / (high52 - low52) * 100, 1)
    except Exception:
        pass

    reasoning = []
    score = 0

    if news_tone == "bullish":
        reasoning.append("News headlines skew positive — strong media narrative")
        score += 0.5
    elif news_tone == "bearish":
        reasoning.append("News headlines skew negative — media headwinds")
        score -= 0.5
    else:
        reasoning.append("News tone neutral — no strong catalyst")

    if vix_value:
        if vix_value < 14:
            reasoning.append(f"India VIX {vix_value:.1f} — low fear, risk-on environment")
            score += 0.5
        elif vix_value > 22:
            reasoning.append(f"India VIX {vix_value:.1f} — elevated fear, protect capital")
            score -= 0.5

    if pos_52w is not None:
        if pos_52w >= 80:
            reasoning.append(f"Near 52W high ({pos_52w:.0f}% of range) — strong momentum but watch for resistance")
        elif pos_52w <= 20:
            reasoning.append(f"Near 52W low ({pos_52w:.0f}% of range) — beaten down, contrarian opportunity")
            score += 0.5

    signal = "BUY" if score >= 1 else ("SELL" if score <= -1 else "HOLD")

    return {
        "agent": "Retail Pulse",
        "signal": signal,
        "score": score,
        "data": {
            "news_tone": news_tone,
            "india_vix": vix_value,
            "position_in_52w_range_pct": pos_52w,
        },
        "reasoning": reasoning,
        "one_liner": f"Sentiment {news_tone} · VIX {vix_value:.1f} · {pos_52w:.0f}% of 52W range" if vix_value and pos_52w else f"Sentiment {news_tone}",
    }


# ── Consensus engine ──────────────────────────────────────────────────────────

def _build_consensus(agents: list[dict]) -> dict:
    signals = [a["signal"] for a in agents]
    scores  = [a["score"]  for a in agents]

    avg_score = sum(scores) / len(scores)
    buys  = signals.count("BUY")
    sells = signals.count("SELL")
    holds = signals.count("HOLD")

    if buys >= 3 or (buys >= 2 and avg_score >= 0.8):
        consensus = "BUY"
        strength  = "strong" if buys == 4 else "moderate"
    elif sells >= 3 or (sells >= 2 and avg_score <= -0.8):
        consensus = "SELL"
        strength  = "strong" if sells == 4 else "moderate"
    else:
        consensus = "HOLD"
        strength  = "neutral"

    disagreement = (buys > 0 and sells > 0)

    return {
        "signal": consensus,
        "strength": strength,
        "votes": {"BUY": buys, "HOLD": holds, "SELL": sells},
        "avg_score": round(avg_score, 2),
        "disagreement": disagreement,
        "note": "Agents disagree — wait for a clearer setup before acting." if disagreement else "",
    }


# ── Public entry point ────────────────────────────────────────────────────────

def get_stock_brief(symbol: str) -> dict:
    """
    Multi-agent stock brief: 4 AI personas debate a stock using real data.

    Each agent independently analyses the stock from their perspective,
    produces a BUY/HOLD/SELL signal, and the consensus engine aggregates.

    Args:
        symbol: NSE stock symbol (e.g. RELIANCE, HDFC, INFY)

    Returns:
        Full structured brief with per-agent analysis + consensus signal.
    """
    symbol = symbol.upper().replace(".NS", "").replace(".BO", "")
    logger.info("Running multi-agent brief for %s", symbol)

    # Run all 4 agents (data errors are caught inside each)
    fii_agent   = _fii_desk_analysis(symbol)
    algo_agent  = _algo_trader_analysis(symbol)
    value_agent = _value_investor_analysis(symbol)
    retail_agent = _retail_pulse_analysis(symbol)

    agents = [fii_agent, algo_agent, value_agent, retail_agent]
    consensus = _build_consensus(agents)

    # Build debate summary
    debate = []
    for a in agents:
        debate.append({
            "agent": a["agent"],
            "verdict": a["signal"],
            "argument": " ".join(a["reasoning"]),
            "one_liner": a["one_liner"],
        })

    return {
        "symbol": symbol,
        "consensus": consensus,
        "debate": debate,
        "agents_detail": agents,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "disclaimer": "This is AI-generated analysis using public data. Not SEBI-registered advice.",
    }
