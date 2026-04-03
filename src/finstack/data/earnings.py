"""
Earnings preview AI for FinStack MCP.

Before quarterly results: combines EPS trend + FII positioning + analyst estimates
+ sector momentum → Beat probability %, key risks, what to watch.

Viral hook: post one public prediction before each Nifty 50 result.
If correct → screenshot → tweet → repeat.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("finstack.earnings")


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.debug("Earnings data error: %s", e)
        return None


def _get_eps_trend(symbol: str) -> dict:
    """Last 4 quarters EPS + QoQ growth trend."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.NS")
        earnings = ticker.quarterly_earnings
        if earnings is None or earnings.empty:
            return {}
        rows = earnings.tail(4)
        eps_list = rows.get("Earnings", rows.iloc[:, 0]).tolist()

        # QoQ EPS growth
        qoq_growth = None
        if len(eps_list) >= 2 and eps_list[-2] and eps_list[-2] != 0:
            qoq_growth = round((eps_list[-1] - eps_list[-2]) / abs(eps_list[-2]) * 100, 1)

        # Trend: improving or declining
        if len(eps_list) >= 3:
            improving = sum(1 for i in range(1, len(eps_list)) if eps_list[i] > eps_list[i-1])
            trend = "improving" if improving >= 2 else ("declining" if improving == 0 else "mixed")
        else:
            trend = "insufficient data"

        return {
            "eps_last_4q": [round(float(e), 2) for e in eps_list],
            "qoq_eps_growth_pct": qoq_growth,
            "trend": trend,
        }
    except Exception as e:
        logger.debug("EPS trend error: %s", e)
        return {}


def _get_analyst_estimates(symbol: str) -> dict:
    """Analyst consensus EPS estimate for next quarter."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.info or {}
        return {
            "analyst_count": info.get("numberOfAnalystOpinions"),
            "recommendation": info.get("recommendationKey"),  # "buy", "hold" etc.
            "target_price": info.get("targetMeanPrice"),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "upside_pct": round(
                (info.get("targetMeanPrice", 0) - info.get("currentPrice", 1)) /
                info.get("currentPrice", 1) * 100, 1
            ) if info.get("targetMeanPrice") and info.get("currentPrice") else None,
        }
    except Exception as e:
        logger.debug("Analyst estimates error: %s", e)
        return {}


def _get_fii_positioning(symbol: str) -> dict:
    """FII holding % change — are institutions building or reducing before results?"""
    from finstack.data.market_intelligence import get_promoter_shareholding
    data = _safe(get_promoter_shareholding, symbol)
    if not data or not isinstance(data, dict):
        return {}
    sh = data.get("shareholding", {})
    history = data.get("history") or []

    fii_current = sh.get("fii_pct")
    fii_change = None
    if len(history) >= 2:
        prev = history[1].get("fii_pct") or history[1].get("fii")
        curr = history[0].get("fii_pct") or history[0].get("fii")
        if prev and curr:
            fii_change = round(curr - prev, 2)

    return {
        "fii_holding_pct": fii_current,
        "fii_qoq_change": fii_change,
        "signal": (
            "FII increasing stake before results — positive" if fii_change and fii_change > 0.5
            else "FII reducing stake — cautious" if fii_change and fii_change < -0.5
            else "FII holding stable"
        ),
    }


def _get_sector_momentum(symbol: str) -> dict:
    """Is the sector outperforming or underperforming Nifty in last 30 days?"""
    try:
        import yfinance as yf
        # Get stock performance
        stock = yf.Ticker(f"{symbol}.NS").history(period="1mo")
        nifty = yf.Ticker("^NSEI").history(period="1mo")

        if stock.empty or nifty.empty:
            return {}

        stock_ret = (stock["Close"].iloc[-1] / stock["Close"].iloc[0] - 1) * 100
        nifty_ret = (nifty["Close"].iloc[-1] / nifty["Close"].iloc[0] - 1) * 100
        alpha = round(stock_ret - nifty_ret, 1)

        return {
            "stock_return_1mo_pct": round(stock_ret, 1),
            "nifty_return_1mo_pct": round(nifty_ret, 1),
            "alpha_vs_nifty": alpha,
            "momentum": "outperforming" if alpha > 2 else ("underperforming" if alpha < -2 else "inline"),
        }
    except Exception as e:
        logger.debug("Sector momentum error: %s", e)
        return {}


def _get_next_earnings_date(symbol: str) -> str | None:
    """Next earnings date from yFinance calendar."""
    try:
        import yfinance as yf
        cal = yf.Ticker(f"{symbol}.NS").calendar
        if cal is None:
            return None
        if hasattr(cal, "get"):
            date = cal.get("Earnings Date")
            if date:
                return str(date[0])[:10] if isinstance(date, list) else str(date)[:10]
        return None
    except Exception:
        return None


def predict_earnings(symbol: str) -> dict:
    """
    AI earnings preview for an NSE stock.

    Combines:
      - Last 4 quarters EPS trend (improving/declining/mixed)
      - Analyst consensus estimate + target price
      - FII positioning change QoQ (building/reducing before results)
      - Stock alpha vs Nifty last 30 days (sector momentum)

    Output: Beat probability %, key risks, what to watch, next earnings date.

    Args:
        symbol: NSE stock symbol (e.g. TCS, INFY, RELIANCE)
    """
    symbol = symbol.upper().replace(".NS", "").replace(".BO", "")
    logger.info("Earnings preview for %s", symbol)

    eps_data      = _get_eps_trend(symbol)
    analyst_data  = _get_analyst_estimates(symbol)
    fii_data      = _get_fii_positioning(symbol)
    momentum_data = _get_sector_momentum(symbol)
    next_date     = _get_next_earnings_date(symbol)

    # ── Score: beat probability ───────────────────────────────────────────────
    score = 50  # base 50%

    # EPS trend
    if eps_data.get("trend") == "improving":
        score += 12
    elif eps_data.get("trend") == "declining":
        score -= 12

    qoq = eps_data.get("qoq_eps_growth_pct")
    if qoq and qoq > 10:
        score += 8
    elif qoq and qoq < -5:
        score -= 8

    # Analyst consensus
    rec = analyst_data.get("recommendation", "")
    if rec in ("buy", "strongBuy"):
        score += 8
    elif rec in ("sell", "strongSell"):
        score -= 8

    upside = analyst_data.get("upside_pct")
    if upside and upside > 15:
        score += 5
    elif upside and upside < 0:
        score -= 5

    # FII positioning
    fii_change = fii_data.get("fii_qoq_change")
    if fii_change and fii_change > 0.5:
        score += 10
    elif fii_change and fii_change < -0.5:
        score -= 10

    # Momentum
    alpha = momentum_data.get("alpha_vs_nifty")
    if alpha and alpha > 3:
        score += 7
    elif alpha and alpha < -3:
        score -= 7

    beat_probability = max(15, min(85, round(score)))

    # ── Key risks ────────────────────────────────────────────────────────────
    risks = []
    if eps_data.get("trend") == "declining":
        risks.append("EPS trend declining over last 3 quarters")
    if fii_change and fii_change < -1:
        risks.append(f"FII reduced holding by {abs(fii_change):.1f}% — smart money reducing exposure")
    if momentum_data.get("momentum") == "underperforming":
        risks.append(f"Stock underperforming Nifty by {abs(alpha):.1f}% — weak pre-results momentum")
    if analyst_data.get("recommendation") in ("sell", "strongSell"):
        risks.append("Analyst consensus is Sell — low expectations")
    if not risks:
        risks.append("No major red flags identified")

    # ── What to watch ────────────────────────────────────────────────────────
    watch = []
    watch.append("Revenue growth QoQ — market rewards top-line beats more than EPS")
    watch.append("Management guidance for next quarter — forward commentary matters more than reported numbers")
    if fii_data.get("fii_holding_pct") and fii_data["fii_holding_pct"] > 20:
        watch.append("FII holding changes post-results — they move fast on guidance misses")
    if momentum_data.get("alpha_vs_nifty") and abs(momentum_data["alpha_vs_nifty"]) > 5:
        watch.append("Price reaction on day 2 — large pre-results moves often reverse after results")

    # ── Signal ───────────────────────────────────────────────────────────────
    if beat_probability >= 65:
        signal = "BEAT LIKELY"
    elif beat_probability >= 50:
        signal = "SLIGHT BEAT EXPECTED"
    elif beat_probability >= 35:
        signal = "IN-LINE OR MISS"
    else:
        signal = "MISS LIKELY"

    return {
        "symbol": symbol,
        "next_earnings_date": next_date or "check NSE calendar",
        "beat_probability_pct": beat_probability,
        "signal": signal,
        "key_risks": risks,
        "what_to_watch": watch,
        "data": {
            "eps_trend": eps_data,
            "analyst": analyst_data,
            "fii_positioning": fii_data,
            "sector_momentum": momentum_data,
        },
        "one_liner": (
            f"{beat_probability}% beat probability — "
            f"EPS trend {eps_data.get('trend', 'unknown')}, "
            f"analyst {analyst_data.get('recommendation', 'n/a')}, "
            f"FII {fii_data.get('signal', 'n/a')}"
        ),
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "disclaimer": "Not SEBI-registered advice. For informational purposes only.",
    }
