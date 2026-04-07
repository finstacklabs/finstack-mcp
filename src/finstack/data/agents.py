"""
Multi-agent stock brief for FinStack MCP.

4 AI personas debate a stock using real Indian market data:
  • FII Desk        — institutional flows, promoter holding, shareholding pattern
  • Algo Trader     — RSI, MACD, VWAP, volume anomaly
  • Value Investor  — P/E, ROE, debt ratios, credit rating
  • Retail Pulse    — news tone, 52W position, VIX level, social buzz

Two modes:
  get_stock_brief(symbol)          — classic 1-round parallel analysis
  get_stock_debate(symbol)         — 3-round sequential debate where agents
                                     react to each other, rebut, and converge

Output: structured debate → consensus signal (BUY/HOLD/SELL) + reasoning chain.
The debate JSON is also consumable by the AgentBattle canvas visualisation.
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
    from finstack.data.market_intelligence import get_promoter_shareholding
    from finstack.data.nse_advanced import get_fii_dii_data

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


# ── Agent 5: Macro Analyst ────────────────────────────────────────────────────

def _macro_analyst_analysis(symbol: str) -> dict:  # noqa: ARG001
    """Macro environment: RBI rates, CPI inflation, G-Sec yield curve."""
    from finstack.data.market_intelligence import (
        get_rbi_policy_rates,
        get_india_macro_indicators,
        get_india_gsec_yields,
    )

    rbi_data   = _safe(get_rbi_policy_rates)
    macro_data = _safe(get_india_macro_indicators)
    gsec_data  = _safe(get_india_gsec_yields)

    repo_rate = None
    inflation = None
    gsec_10y  = None

    if rbi_data and isinstance(rbi_data, dict):
        repo_rate = rbi_data.get("repo_rate") or rbi_data.get("policy_repo_rate")

    if macro_data and isinstance(macro_data, dict):
        indicators = macro_data.get("indicators", {})
        if isinstance(indicators, dict):
            cpi = indicators.get("cpi_inflation") or indicators.get("inflation_rate")
            if cpi is not None:
                try:
                    inflation = float(str(cpi).replace("%", "").strip())
                except ValueError:
                    pass

    if gsec_data and isinstance(gsec_data, dict):
        yields = gsec_data.get("yields", {})
        if isinstance(yields, dict):
            gsec_10y = yields.get("10y") or yields.get("10_year")

    reasoning = []
    score = 0

    if repo_rate is not None:
        if repo_rate <= 5.5:
            reasoning.append(f"RBI repo {repo_rate}% — accommodative, cheap money environment")
            score += 1
        elif repo_rate >= 6.5:
            reasoning.append(f"RBI repo {repo_rate}% — tight monetary policy, credit costs elevated")
            score -= 0.5
        else:
            reasoning.append(f"RBI repo {repo_rate}% — neutral stance, rate pause likely")

    if inflation is not None:
        if inflation < 4.5:
            reasoning.append(f"CPI {inflation:.1f}% — within RBI 4% target band, supportive for equities")
            score += 0.5
        elif inflation > 6.0:
            reasoning.append(f"CPI {inflation:.1f}% — above tolerance band, rate hike risk")
            score -= 0.5
        else:
            reasoning.append(f"CPI {inflation:.1f}% — manageable, near RBI comfort zone")

    if gsec_10y is not None:
        if gsec_10y < 6.5:
            reasoning.append(f"10Y G-Sec {gsec_10y:.2f}% — low risk-free rate, equities attractive by spread")
            score += 0.5
        elif gsec_10y > 7.5:
            reasoning.append(f"10Y G-Sec {gsec_10y:.2f}% — high bond yield competing with equity earnings yield")
            score -= 0.5
        else:
            reasoning.append(f"10Y G-Sec {gsec_10y:.2f}% — neutral, watch for yield direction shift")

    if not reasoning:
        reasoning.append("Macro data unavailable — neutral macro environment assumed")

    signal = "BUY" if score >= 1 else ("SELL" if score <= -1 else "HOLD")
    rate_str = f"Repo {repo_rate}%" if repo_rate else ""
    cpi_str  = f"CPI {inflation:.1f}%" if inflation else ""
    parts    = [p for p in [rate_str, cpi_str] if p]

    return {
        "agent": "Macro Analyst",
        "signal": signal,
        "score": score,
        "data": {
            "repo_rate": repo_rate,
            "cpi_inflation": inflation,
            "gsec_10y_yield": gsec_10y,
        },
        "reasoning": reasoning,
        "one_liner": (
            f"Macro {'supportive' if signal == 'BUY' else ('restrictive' if signal == 'SELL' else 'neutral')}"
            f" — {' · '.join(parts)}" if parts else "Macro environment neutral"
        ),
    }


# ── Agent 6: Options Flow ─────────────────────────────────────────────────────

def _options_flow_analysis(symbol: str) -> dict:
    """Options market: PCR, max pain, OI skew — smart-money positioning."""
    from finstack.data.nse_advanced import get_options_chain

    options_data = _safe(get_options_chain, symbol)

    pcr      = None
    max_pain = None
    oi_signal = "neutral"

    if options_data and isinstance(options_data, dict):
        pcr      = options_data.get("pcr") or options_data.get("put_call_ratio")
        max_pain = options_data.get("max_pain")
        oi_data  = options_data.get("oi_analysis", {})
        if isinstance(oi_data, dict):
            ce_oi = float(oi_data.get("total_call_oi") or 0)
            pe_oi = float(oi_data.get("total_put_oi") or 0)
            if pe_oi > ce_oi * 1.3:
                oi_signal = "bullish"   # heavy put buying = institutional hedging = long bias
            elif ce_oi > pe_oi * 1.3:
                oi_signal = "bearish"   # heavy call buying = retail speculation = caution

    reasoning = []
    score = 0

    if pcr is not None:
        if pcr > 1.3:
            reasoning.append(f"PCR {pcr:.2f} — elevated put buying, contrarian bullish signal")
            score += 1
        elif pcr < 0.7:
            reasoning.append(f"PCR {pcr:.2f} — low put coverage, complacency — watch for reversal")
            score -= 0.5
        else:
            reasoning.append(f"PCR {pcr:.2f} — balanced options positioning, no directional edge")

    if oi_signal == "bullish":
        reasoning.append("Put OI > Call OI — institutional hedging implies underlying long positions")
        score += 0.5
    elif oi_signal == "bearish":
        reasoning.append("Call OI > Put OI — speculative call buying, distribution risk elevated")
        score -= 0.5

    if max_pain is not None:
        reasoning.append(f"Max pain ₹{max_pain:,.0f} — options writers favour price convergence here")

    if not reasoning:
        reasoning.append("Options data unavailable for this symbol — signal neutral")

    signal = "BUY" if score >= 1 else ("SELL" if score <= -1 else "HOLD")

    return {
        "agent": "Options Flow",
        "signal": signal,
        "score": score,
        "data": {
            "pcr": pcr,
            "max_pain": max_pain,
            "oi_signal": oi_signal,
        },
        "reasoning": reasoning,
        "one_liner": (
            f"Options {'bullish' if signal == 'BUY' else ('bearish' if signal == 'SELL' else 'neutral')}"
            f" — PCR {pcr:.2f}" if pcr else "Options flow neutral"
        ),
    }


AGENT_ANALYZERS = [
    _fii_desk_analysis,
    _algo_trader_analysis,
    _value_investor_analysis,
    _retail_pulse_analysis,
    _macro_analyst_analysis,
    _options_flow_analysis,
]


# ── Consensus engine ──────────────────────────────────────────────────────────

def _build_consensus(agents: list[dict]) -> dict:
    signals = [a["signal"] for a in agents]
    scores  = [a["score"]  for a in agents]
    n       = len(agents)

    avg_score = sum(scores) / n
    buys  = signals.count("BUY")
    sells = signals.count("SELL")
    holds = signals.count("HOLD")

    # Majority = more than half (works for 4 or 6 agents)
    majority = n // 2 + 1

    if buys >= majority or (buys >= majority - 1 and avg_score >= 0.8):
        consensus = "BUY"
        strength  = "strong" if buys == n else "moderate"
    elif sells >= majority or (sells >= majority - 1 and avg_score <= -0.8):
        consensus = "SELL"
        strength  = "strong" if sells == n else "moderate"
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


# ── Sequential debate logic ───────────────────────────────────────────────────

def _round2_rebuttal(agent: dict, others: list[dict]) -> dict:
    """
    Round 2: agent reads all other Round 1 verdicts and either:
    - Holds position (strengthens argument)
    - Upgrades (if majority disagrees but data partially supports)
    - Downgrades (if strong counter-evidence from peers)
    """
    my_signal   = agent["signal"]
    my_score    = agent["score"]
    other_sigs  = [o["signal"] for o in others]
    other_scores = [o["score"] for o in others]
    avg_others  = sum(other_scores) / len(other_scores) if other_scores else 0

    rebuttal_text = []
    new_score = my_score
    new_signal = my_signal

    buys_others  = other_sigs.count("BUY")
    sells_others = other_sigs.count("SELL")

    # If 3 others all agree on opposite — soften stance
    if my_signal == "BUY" and sells_others >= 2:
        new_score = my_score * 0.6
        rebuttal_text.append(
            f"Noting {sells_others} peers are bearish. My data still shows "
            f"{agent['one_liner']} — but acknowledging macro headwinds. "
            f"Moderating conviction."
        )
    elif my_signal == "SELL" and buys_others >= 2:
        new_score = my_score * 0.6
        rebuttal_text.append(
            f"Majority bullish signals noted. My concern remains: "
            f"{agent['one_liner']}. Reducing conviction but maintaining SELL."
        )
    elif my_signal == "HOLD" and (buys_others >= 2 or sells_others >= 2):
        # HOLD agent gets influenced by strong consensus
        if buys_others >= 2 and avg_others > 0.5:
            new_score = min(my_score + 0.5, 1.0)
            rebuttal_text.append(
                f"Strong BUY consensus from peers. My analysis was neutral, "
                f"but {agent['one_liner']}. Upgrading to BUY on peer convergence."
            )
        elif sells_others >= 2 and avg_others < -0.5:
            new_score = max(my_score - 0.5, -1.0)
            rebuttal_text.append(
                f"Majority SELL signals. {agent['one_liner']}. "
                f"Downgrading to SELL — risks outweigh upside."
            )
        else:
            rebuttal_text.append(
                f"Mixed signals from peers. Maintaining HOLD. "
                f"{agent['one_liner']} supports a wait-and-watch stance."
            )
    else:
        # Holding ground — peer majority agrees or data is clear
        rebuttal_text.append(
            f"Peers noted. Standing firm: {agent['one_liner']}. "
            f"{'Bullish' if my_signal == 'BUY' else 'Bearish'} thesis intact."
        )

    new_signal = "BUY" if new_score >= 1 else ("SELL" if new_score <= -1 else "HOLD")

    return {
        "agent":     agent["agent"],
        "signal":    new_signal,
        "score":     round(new_score, 2),
        "rebuttal":  " ".join(rebuttal_text),
        "changed":   new_signal != my_signal,
        "one_liner": agent["one_liner"],
    }


def _round3_final(r1: dict, r2: dict, all_r2: list[dict]) -> dict:
    """
    Round 3: lock in final verdict. Brief closing statement.
    """
    changed_count = sum(1 for a in all_r2 if a["changed"])
    peers_final   = [a["signal"] for a in all_r2 if a["agent"] != r2["agent"]]
    consensus_dir = "BUY" if peers_final.count("BUY") > peers_final.count("SELL") else (
                    "SELL" if peers_final.count("SELL") > peers_final.count("BUY") else "HOLD")

    if r2["changed"]:
        closing = (
            f"After hearing the debate, I revised from {r1['signal']} to {r2['signal']}. "
            f"The peer arguments moved me. Final call: {r2['signal']}."
        )
    elif r2["signal"] == consensus_dir:
        closing = (
            f"Debate confirmed my view. {changed_count} agent(s) changed position. "
            f"Consensus converging on {r2['signal']}. Conviction: HIGH."
        )
    else:
        closing = (
            f"I remain the dissenter. Peers moved to {consensus_dir} but my data "
            f"says {r2['signal']}. Watch this divergence — it's a signal in itself."
        )

    return {
        "agent":   r2["agent"],
        "signal":  r2["signal"],
        "score":   r2["score"],
        "closing": closing,
    }


# ── Public entry point ────────────────────────────────────────────────────────

def get_stock_brief(symbol: str) -> dict:
    """
    Multi-agent stock brief: 6 AI personas debate a stock using real data.

    Each agent independently analyses the stock from their perspective,
    produces a BUY/HOLD/SELL signal, and the consensus engine aggregates.

    Args:
        symbol: NSE stock symbol (e.g. RELIANCE, HDFC, INFY)

    Returns:
        Full structured brief with per-agent analysis + consensus signal.
    """
    symbol = symbol.upper().replace(".NS", "").replace(".BO", "")
    logger.info("Running multi-agent brief for %s", symbol)

    # Run all agents (data errors are caught inside each)
    agents = [analyzer(symbol) for analyzer in AGENT_ANALYZERS]
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

    result = {
        "symbol": symbol,
        "consensus": consensus,
        "debate": debate,
        "agents_detail": agents,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "disclaimer": "This is AI-generated analysis using public data. Not SEBI-registered advice.",
    }

    # Auto-log signal for outcome tracking (fire-and-forget, never blocks)
    try:
        from finstack.data.signal_tracker import log_signal
        log_signal(
            symbol=symbol,
            signal=consensus["signal"],
            source="brief",
            score=consensus.get("avg_score"),
            agent_votes=consensus.get("votes"),
        )
    except Exception:
        pass

    return result


def get_stock_debate(symbol: str) -> dict:
    """
    3-round sequential debate: agents read each other's arguments and rebut.

    Round 1 — Independent analysis (same as get_stock_brief)
    Round 2 — Each agent reads all other Round 1 verdicts → rebuts or upgrades
    Round 3 — Final lock-in with closing statement

    Returns full debate transcript consumable by the AgentBattle visualisation.

    Args:
        symbol: NSE stock symbol (e.g. RELIANCE, HDFC, INFY)
    """
    symbol = symbol.upper().replace(".NS", "").replace(".BO", "")
    logger.info("Running 3-round sequential debate for %s", symbol)

    # ── ROUND 1: Independent analysis ────────────────────────────────────────
    r1_agents = [analyzer(symbol) for analyzer in AGENT_ANALYZERS]

    round1 = []
    for a in r1_agents:
        round1.append({
            "agent":    a["agent"],
            "signal":   a["signal"],
            "score":    a["score"],
            "argument": " ".join(a["reasoning"]),
            "one_liner": a["one_liner"],
        })

    # ── ROUND 2: Rebuttals ────────────────────────────────────────────────────
    round2 = []
    for i, agent in enumerate(r1_agents):
        others = [r1_agents[j] for j in range(len(r1_agents)) if j != i]
        r2 = _round2_rebuttal(agent, others)
        round2.append(r2)

    # ── ROUND 3: Final verdicts ───────────────────────────────────────────────
    round3 = []
    for i, r2 in enumerate(round2):
        r3 = _round3_final(round1[i], r2, round2)
        round3.append(r3)

    # ── Final consensus from Round 3 ──────────────────────────────────────────
    final_consensus = _build_consensus(round3)

    # Count how many agents changed their mind across debate
    changed = sum(1 for i in range(len(round1)) if round1[i]["signal"] != round3[i]["signal"])

    # Build edges for visualisation (who influenced whom in Round 2)
    debate_edges = []
    for i, r2 in enumerate(round2):
        if r2["changed"]:
            # Find who caused the change (strongest opposing voice)
            for j, other in enumerate(round1):
                if j != i and other["signal"] != round1[i]["signal"]:
                    debate_edges.append({
                        "from":   other["agent"],
                        "to":     round1[i]["agent"],
                        "type":   "influenced",
                        "round":  2,
                        "text":   f"{other['agent']} moved {round1[i]['agent']} from {round1[i]['signal']} → {r2['signal']}",
                    })
                    break
        else:
            # Held ground — show as "challenged"
            for j, other in enumerate(round1):
                if j != i and other["signal"] != round1[i]["signal"]:
                    debate_edges.append({
                        "from":  other["agent"],
                        "to":    round1[i]["agent"],
                        "type":  "challenged",
                        "round": 2,
                        "text":  f"{other['agent']} challenged {round1[i]['agent']} but failed to move them",
                    })
                    break

    result = {
        "symbol": symbol,
        "mode":   "sequential_debate",
        "rounds": {
            "round1": round1,
            "round2": round2,
            "round3": round3,
        },
        "debate_edges":    debate_edges,
        "minds_changed":   changed,
        "final_consensus": {
            "signal":   final_consensus["signal"],
            "strength": final_consensus["strength"],
            "votes":    final_consensus["votes"],
            "avg_score": final_consensus["avg_score"],
            "note": f"{changed} agent(s) changed position during debate. "
                    f"{'Strong conviction.' if final_consensus['strength'] == 'strong' else 'Watch for volatility.'}"
        },
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "disclaimer": "AI-generated analysis using public data. Not SEBI-registered investment advice.",
    }

    # Auto-log signal for outcome tracking
    try:
        from finstack.data.signal_tracker import log_signal
        log_signal(
            symbol=symbol,
            signal=final_consensus["signal"],
            source="debate",
            score=final_consensus.get("avg_score"),
            agent_votes=final_consensus.get("votes"),
        )
    except Exception:
        pass

    return result
