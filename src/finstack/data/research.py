"""
High-value research workflows for FinStack MCP.

Adds product-level tools on top of existing market data primitives:
- Watchlist batch scan
- Unified stock timeline
- Automation-friendly stock signal score
- Sector and peer context
- Lightweight evaluation / proof layer for the price-action core
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import yfinance as yf

from finstack.data.agents import get_stock_brief
from finstack.data.analytics import compare_stocks, compute_technical_indicators, get_sector_performance
from finstack.data.earnings import predict_earnings
from finstack.data.fundamentals import get_key_ratios
from finstack.data.global_markets import get_market_news
from finstack.data.insider_pattern import get_insider_signal
from finstack.data.nse import get_nse_quote
from finstack.data.nse_advanced import get_bulk_deals, get_quarterly_results
from finstack.data.promoter_watch import get_pledge_alert
from finstack.data.sentiment import get_social_sentiment
from finstack.data.smart_money import detect_unusual_activity
from finstack.utils.cache import general_cache, cached
from finstack.utils.helpers import clean_nan, to_nse_symbol, validate_symbol

logger = logging.getLogger("finstack.data.research")

SECTOR_PEER_MAP: dict[str, list[str]] = {
    "BANKS": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK"],
    "IT": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"],
    "ENERGY": ["RELIANCE", "ONGC", "BPCL", "IOC", "GAIL"],
    "OIL & GAS": ["RELIANCE", "ONGC", "BPCL", "IOC", "GAIL"],
    "AUTO": ["MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "EICHERMOT"],
    "PHARMA": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "LUPIN"],
    "FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "DABUR", "BRITANNIA"],
    "METALS & MINING": ["TATASTEEL", "JSWSTEEL", "HINDALCO", "COALINDIA", "VEDL"],
    "METAL": ["TATASTEEL", "JSWSTEEL", "HINDALCO", "COALINDIA", "VEDL"],
    "CEMENT": ["ULTRACEMCO", "SHREECEM", "AMBUJACEM", "ACC", "DALBHARAT"],
    "FINANCIAL SERVICES": ["BAJFINANCE", "SBICARD", "CHOLAFIN", "SHRIRAMFIN", "HDFCAMC"],
    "TELECOM": ["BHARTIARTL", "IDEA", "TATACOMM", "HFCL", "TEJASNET"],
}


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # pragma: no cover - defensive aggregator
        logger.debug("Research helper error in %s: %s", getattr(fn, "__name__", "fn"), exc)
        return None


def _normalize_symbol(symbol: str) -> str:
    return validate_symbol(symbol).upper().replace(".NS", "").replace(".BO", "")


def _parse_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _bucket_from_sector(sector: str | None, industry: str | None) -> str:
    text = " ".join(part for part in [sector or "", industry or ""] if part).upper()
    for key in SECTOR_PEER_MAP:
        if key in text:
            return key
    return ""


def _get_peer_symbols(symbol: str, sector: str | None, industry: str | None) -> list[str]:
    bucket = _bucket_from_sector(sector, industry)
    peers = SECTOR_PEER_MAP.get(bucket, [])
    deduped = [peer for peer in peers if peer != symbol]
    return deduped[:4]


def _signal_to_points(signal: str, positive: int, neutral: int = 0, negative: int | None = None) -> int:
    negative = -positive if negative is None else negative
    signal = (signal or "").upper()
    if signal == "BUY":
        return positive
    if signal == "SELL":
        return negative
    return neutral


def _score_to_signal(score: int) -> tuple[str, str]:
    if score >= 70:
        return "BUY", "high"
    if score >= 56:
        return "BUY", "moderate"
    if score <= 30:
        return "SELL", "high"
    if score <= 44:
        return "SELL", "moderate"
    return "HOLD", "balanced"


def _price_history(symbol: str, period: str = "6mo") -> pd.DataFrame:
    return yf.Ticker(to_nse_symbol(symbol)).history(period=period, interval="1d")


def _history_return_pct(hist: pd.DataFrame, trading_days: int) -> float | None:
    if hist.empty or len(hist) <= trading_days:
        return None
    start = float(hist["Close"].iloc[-trading_days - 1])
    end = float(hist["Close"].iloc[-1])
    if start == 0:
        return None
    return round((end - start) / start * 100, 2)


def _build_price_action_snapshot(
    stock_hist: pd.DataFrame,
    index_hist: pd.DataFrame | None = None,
    *,
    holding_days: int = 20,
) -> dict[str, Any]:
    if stock_hist.empty or len(stock_hist) < 60:
        return {
            "score": 50,
            "signal": "HOLD",
            "strength": "low",
            "factors": [],
        }

    close = stock_hist["Close"]
    volume = stock_hist["Volume"].fillna(0)
    price = float(close.iloc[-1])

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal_line = macd.ewm(span=9, adjust=False).mean()
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))

    score = 50
    reasons: list[str] = []

    if pd.notna(sma20.iloc[-1]) and price > float(sma20.iloc[-1]):
        score += 6
        reasons.append("Price above 20-day trend")
    else:
        score -= 4
        reasons.append("Price below 20-day trend")

    if pd.notna(sma50.iloc[-1]) and pd.notna(sma20.iloc[-1]) and float(sma20.iloc[-1]) > float(sma50.iloc[-1]):
        score += 6
        reasons.append("20-day moving average above 50-day")
    elif pd.notna(sma50.iloc[-1]) and pd.notna(sma20.iloc[-1]):
        score -= 5
        reasons.append("20-day moving average below 50-day")

    if pd.notna(macd.iloc[-1]) and pd.notna(signal_line.iloc[-1]) and float(macd.iloc[-1]) > float(signal_line.iloc[-1]):
        score += 5
        reasons.append("MACD is bullish")
    else:
        score -= 4
        reasons.append("MACD is bearish/flat")

    rsi_val = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None
    if rsi_val is not None:
        if 45 <= rsi_val <= 68:
            score += 5
            reasons.append(f"RSI healthy at {rsi_val:.1f}")
        elif rsi_val >= 75:
            score -= 6
            reasons.append(f"RSI stretched at {rsi_val:.1f}")
        elif rsi_val <= 35:
            score -= 3
            reasons.append(f"RSI weak at {rsi_val:.1f}")

    avg_vol = float(volume.iloc[-21:-1].mean()) if len(volume) >= 21 else None
    if avg_vol and avg_vol > 0:
        vol_ratio = float(volume.iloc[-1]) / avg_vol
        if vol_ratio >= 1.8:
            score += 4
            reasons.append(f"Volume spike {vol_ratio:.1f}x average")

    if index_hist is not None and not index_hist.empty and len(index_hist) > max(holding_days, 22):
        stock_ret = _history_return_pct(stock_hist, 20)
        index_ret = _history_return_pct(index_hist, 20)
        if stock_ret is not None and index_ret is not None:
            relative = round(stock_ret - index_ret, 2)
            if relative > 3:
                score += 6
                reasons.append(f"Outperforming Nifty by {relative:.1f}%")
            elif relative < -3:
                score -= 6
                reasons.append(f"Underperforming Nifty by {abs(relative):.1f}%")

    score = max(0, min(100, round(score)))
    signal, strength = _score_to_signal(score)
    return {
        "score": score,
        "signal": signal,
        "strength": strength,
        "factors": reasons,
    }


@cached(general_cache, ttl=900)
def get_sector_peer_context(symbol: str) -> dict:
    """Show sector strength and peer positioning around a stock."""
    symbol = _normalize_symbol(symbol)

    quote = _safe(get_nse_quote, symbol) or {}
    ratios = _safe(get_key_ratios, symbol) or {}
    sector_data = _safe(get_sector_performance) or {}
    hist = _safe(_price_history, symbol, "3mo")

    sector = quote.get("sector") or ratios.get("sector")
    industry = quote.get("industry")
    peers = _get_peer_symbols(symbol, sector, industry)
    comparison = _safe(compare_stocks, [symbol] + peers) or {}
    comp_rows = comparison.get("comparison", [])

    peer_avg_change = None
    peer_avg_pe = None
    peer_rank = None
    valuation_vs_peers = "unknown"
    price_return_1m = _history_return_pct(hist, 20) if isinstance(hist, pd.DataFrame) else None

    if comp_rows:
        sorted_change = sorted(comp_rows, key=lambda row: _parse_float(row.get("change_pct")) or -999, reverse=True)
        peer_rank = next((idx + 1 for idx, row in enumerate(sorted_change) if row.get("symbol") == symbol), None)
        peer_only = [row for row in comp_rows if row.get("symbol") != symbol]
        peer_changes = [_parse_float(row.get("change_pct")) for row in peer_only]
        peer_pes = [_parse_float(row.get("pe_ratio")) for row in peer_only if _parse_float(row.get("pe_ratio")) is not None]
        peer_changes = [value for value in peer_changes if value is not None]
        if peer_changes:
            peer_avg_change = round(sum(peer_changes) / len(peer_changes), 2)
        if peer_pes:
            peer_avg_pe = round(sum(peer_pes) / len(peer_pes), 2)
            own_pe = _parse_float(next((row.get("pe_ratio") for row in comp_rows if row.get("symbol") == symbol), None))
            if own_pe is not None:
                if own_pe < peer_avg_pe * 0.9:
                    valuation_vs_peers = "discount"
                elif own_pe > peer_avg_pe * 1.1:
                    valuation_vs_peers = "premium"
                else:
                    valuation_vs_peers = "inline"

    sector_rows = sector_data.get("sectors", [])
    sector_match = None
    if sector and sector_rows:
        sector_match = next((row for row in sector_rows if sector.lower().split()[0] in row.get("sector", "").lower()), None)

    signal = "neutral"
    notes = []
    if sector_match:
        notes.append(f"{sector_match['sector']} is moving {sector_match['change_pct']}% today")
    if peer_rank == 1:
        signal = "leader"
        notes.append("Stock is leading its peer basket today")
    elif peer_rank and peer_only and peer_rank > len(comp_rows) // 2 + 1:
        signal = "laggard"
        notes.append("Stock is lagging peers on recent performance")
    if valuation_vs_peers == "discount":
        notes.append("Valuation sits below peer average")
    elif valuation_vs_peers == "premium":
        notes.append("Valuation sits above peer average")

    return clean_nan({
        "symbol": symbol,
        "sector": sector,
        "industry": industry,
        "peer_symbols": peers,
        "peer_context": comp_rows,
        "peer_rank_today": peer_rank,
        "peer_average_change_pct": peer_avg_change,
        "peer_average_pe": peer_avg_pe,
        "valuation_vs_peers": valuation_vs_peers,
        "price_return_1m_pct": price_return_1m,
        "sector_performance": sector_match,
        "signal": signal,
        "notes": notes,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    })


@cached(general_cache, ttl=600)
def get_stock_signal_score(symbol: str) -> dict:
    """Automation-friendly stock ranking score built from multiple FinStack signals."""
    symbol = _normalize_symbol(symbol)

    brief = _safe(get_stock_brief, symbol) or {}
    smart_money = _safe(detect_unusual_activity, symbol) or {}
    sentiment = _safe(get_social_sentiment, symbol) or {}
    pledge = _safe(get_pledge_alert, symbol) or {}
    insider = _safe(get_insider_signal, symbol) or {}
    peer_context = _safe(get_sector_peer_context, symbol) or {}
    technicals = _safe(compute_technical_indicators, symbol, "6mo", ["RSI", "MACD", "SMA"]) or {}
    earnings = _safe(predict_earnings, symbol) or {}

    score = 50
    components: list[dict[str, Any]] = []

    def add_component(name: str, delta: int, evidence: str) -> None:
        nonlocal score
        score += delta
        components.append({"component": name, "impact": delta, "evidence": evidence})

    consensus = (brief.get("consensus") or {}).get("signal")
    strength = (brief.get("consensus") or {}).get("strength", "")
    if consensus:
        base = 14 if strength == "strong" else 10
        add_component("agent_consensus", _signal_to_points(consensus, base, 0), f"Agent consensus is {consensus} ({strength})")

    alert_level = (smart_money.get("alert_level") or "").lower()
    if alert_level == "high":
        add_component("smart_money", 12, smart_money.get("verdict", "Multiple unusual signals"))
    elif alert_level == "moderate":
        add_component("smart_money", 7, smart_money.get("verdict", "Some unusual accumulation signals"))
    elif alert_level == "low":
        add_component("smart_money", 3, smart_money.get("verdict", "One unusual signal detected"))

    sentiment_signal = sentiment.get("signal")
    confidence = sentiment.get("confidence")
    if sentiment_signal:
        strength_bonus = 2 if confidence == "high" else 0
        delta = _signal_to_points(sentiment_signal, 6 + strength_bonus, 0)
        add_component("social_sentiment", delta, f"Social/news sentiment is {sentiment_signal} ({confidence})")

    pledge_risk = (pledge.get("risk_level") or "").lower()
    if pledge_risk == "critical":
        add_component("promoter_pledge", -18, pledge.get("alert", "Critical pledge risk"))
    elif pledge_risk == "danger":
        add_component("promoter_pledge", -12, pledge.get("alert", "High pledge risk"))
    elif pledge_risk == "watch":
        add_component("promoter_pledge", -6, pledge.get("alert", "Elevated pledge risk"))
    elif pledge_risk == "safe":
        add_component("promoter_pledge", 2, pledge.get("alert", "Low pledge risk"))

    insider_signal = insider.get("signal")
    if insider_signal == "BUY":
        add_component("insider_activity", 7, insider.get("interpretation", "Insiders accumulating"))
    elif insider_signal == "SELL":
        add_component("insider_activity", -7, insider.get("interpretation", "Insiders distributing"))

    rsi_value = (((technicals.get("indicators") or {}).get("RSI") or {}).get("value"))
    macd_signal = (((technicals.get("indicators") or {}).get("MACD") or {}).get("signal") or "")
    sma_signals = (((technicals.get("indicators") or {}).get("SMA") or {}).get("price_vs_sma") or [])
    if isinstance(rsi_value, (int, float)):
        if 45 <= float(rsi_value) <= 68:
            add_component("technical_rsi", 4, f"RSI sits at {float(rsi_value):.1f}")
        elif float(rsi_value) >= 75:
            add_component("technical_rsi", -5, f"RSI stretched at {float(rsi_value):.1f}")
    if "Bullish" in macd_signal:
        add_component("technical_macd", 5, macd_signal)
    elif "Bearish" in macd_signal:
        add_component("technical_macd", -5, macd_signal)
    if any("bullish" in str(item).lower() or "golden cross" in str(item).lower() for item in sma_signals):
        add_component("technical_trend", 5, ", ".join(str(item) for item in sma_signals[:2]))
    elif any("bearish" in str(item).lower() for item in sma_signals):
        add_component("technical_trend", -4, ", ".join(str(item) for item in sma_signals[:2]))

    peer_signal = peer_context.get("signal")
    if peer_signal == "leader":
        add_component("peer_context", 6, "Stock is leading peers / sector")
    elif peer_signal == "laggard":
        add_component("peer_context", -6, "Stock is lagging peers / sector")
    if peer_context.get("valuation_vs_peers") == "discount":
        add_component("peer_valuation", 3, "Valuation below peer average")
    elif peer_context.get("valuation_vs_peers") == "premium":
        add_component("peer_valuation", -3, "Valuation above peer average")

    beat_prob = _parse_float(earnings.get("beat_probability_pct"))
    if beat_prob is not None:
        if beat_prob >= 65:
            add_component("earnings_setup", 4, f"Earnings beat probability {beat_prob:.0f}%")
        elif beat_prob <= 35:
            add_component("earnings_setup", -4, f"Earnings beat probability only {beat_prob:.0f}%")

    score = max(0, min(100, round(score)))
    signal, strength = _score_to_signal(score)
    bullish = sum(1 for item in components if item["impact"] > 0)
    bearish = sum(1 for item in components if item["impact"] < 0)

    top_supports = [item["evidence"] for item in sorted((i for i in components if i["impact"] > 0), key=lambda i: i["impact"], reverse=True)[:3]]
    top_risks = [item["evidence"] for item in sorted((i for i in components if i["impact"] < 0), key=lambda i: i["impact"])[:3]]

    return clean_nan({
        "symbol": symbol,
        "signal_score": score,
        "signal": signal,
        "strength": strength,
        "automation_rank": f"{signal}_{strength}".lower(),
        "factor_balance": {
            "bullish_components": bullish,
            "bearish_components": bearish,
        },
        "top_supports": top_supports,
        "top_risks": top_risks,
        "components": components,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "disclaimer": "Signal score is a decision-support ranking layer, not a guaranteed return forecast.",
    })


@cached(general_cache, ttl=600)
def scan_watchlist(symbols: list[str]) -> dict:
    """Batch-rank a watchlist using FinStack signal score and risk context."""
    cleaned = []
    for symbol in symbols:
        try:
            cleaned.append(_normalize_symbol(symbol))
        except Exception:
            continue

    cleaned = list(dict.fromkeys(cleaned))[:25]
    results = []
    for symbol in cleaned:
        scorecard = get_stock_signal_score(symbol)
        results.append({
            "symbol": symbol,
            "signal": scorecard.get("signal"),
            "signal_score": scorecard.get("signal_score"),
            "strength": scorecard.get("strength"),
            "automation_rank": scorecard.get("automation_rank"),
            "top_supports": scorecard.get("top_supports", []),
            "top_risks": scorecard.get("top_risks", []),
        })

    ranked = sorted(results, key=lambda row: row.get("signal_score", 0), reverse=True)
    return {
        "scanned": len(cleaned),
        "ranked_watchlist": ranked,
        "top_buys": [row for row in ranked if row.get("signal") == "BUY"][:5],
        "top_risks": sorted(ranked, key=lambda row: row.get("signal_score", 0))[:5],
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


@cached(general_cache, ttl=600)
def get_stock_timeline(symbol: str, max_events: int = 12) -> dict:
    """Merge recent news, results, insider, smart-money, sentiment, and pledge into one timeline."""
    symbol = _normalize_symbol(symbol)
    events: list[dict[str, Any]] = []

    news = _safe(get_market_news, symbol) or {}
    for item in (news.get("news") or [])[:4]:
        events.append({
            "date": item.get("published") or "",
            "type": "news",
            "headline": item.get("title") or "Market news item",
            "detail": item.get("publisher") or "",
            "importance": "medium",
        })

    quarter = _safe(get_quarterly_results, symbol) or {}
    latest = (quarter.get("quarters") or [{}])[0]
    if latest:
        rev_growth = latest.get("total_revenue_qoq_growth") or latest.get("revenue_qoq_growth")
        profit_growth = latest.get("net_income_qoq_growth") or latest.get("profit_qoq_growth")
        quarter_summary = []
        if rev_growth is not None:
            quarter_summary.append(f"Revenue QoQ {rev_growth:+.1f}%")
        if profit_growth is not None:
            quarter_summary.append(f"Profit QoQ {profit_growth:+.1f}%")
        if quarter_summary:
            events.append({
                "date": latest.get("quarter") or quarter.get("latest_quarter") or "",
                "type": "results",
                "headline": "Latest quarterly results",
                "detail": " · ".join(quarter_summary),
                "importance": "high",
            })

    insider = _safe(get_insider_signal, symbol) or {}
    if insider.get("signal"):
        insider_date = ""
        if insider.get("recent_buys"):
            insider_date = insider["recent_buys"][0].get("date", "")
        elif insider.get("recent_sells"):
            insider_date = insider["recent_sells"][0].get("date", "")
        events.append({
            "date": insider_date,
            "type": "insider",
            "headline": f"Insider signal: {insider.get('signal')}",
            "detail": insider.get("interpretation", ""),
            "importance": "high" if insider.get("signal") in {"BUY", "SELL"} else "medium",
        })

    bulk = _safe(get_bulk_deals) or {}
    raw_deals = bulk.get("data", []) if isinstance(bulk, dict) else (bulk if isinstance(bulk, list) else [])
    symbol_deals = []
    for deal in raw_deals:
        if (deal.get("symbol") or deal.get("SYMBOL") or "").upper() == symbol:
            symbol_deals.append(deal)
    for deal in symbol_deals[:2]:
        side = deal.get("buySell") or deal.get("BD_BUY_SELL") or "TRADE"
        qty = deal.get("tradedQty") or deal.get("BD_QTY_TRD") or ""
        events.append({
            "date": deal.get("date") or deal.get("BD_DT_DATE") or "",
            "type": "bulk_deal",
            "headline": f"Bulk deal: {side}",
            "detail": f"Qty {qty}",
            "importance": "high",
        })

    sentiment = _safe(get_social_sentiment, symbol) or {}
    if sentiment.get("signal"):
        events.append({
            "date": sentiment.get("generated_at") or sentiment.get("timestamp") or "",
            "type": "sentiment",
            "headline": f"Social sentiment: {sentiment.get('signal')}",
            "detail": f"{sentiment.get('bullish_pct', '?')}% bullish · confidence {sentiment.get('confidence', 'unknown')}",
            "importance": "medium",
        })

    pledge = _safe(get_pledge_alert, symbol) or {}
    if pledge.get("risk_level"):
        events.append({
            "date": pledge.get("generated_at") or "",
            "type": "pledge",
            "headline": f"Promoter pledge: {pledge.get('risk_level')}",
            "detail": pledge.get("alert", ""),
            "importance": "high" if pledge.get("risk_level") in {"danger", "critical"} else "medium",
        })

    smart_money = _safe(detect_unusual_activity, symbol) or {}
    if smart_money.get("alerts"):
        for alert in smart_money.get("alerts", [])[:2]:
            events.append({
                "date": smart_money.get("scanned_at") or "",
                "type": "smart_money",
                "headline": "Smart money signal",
                "detail": alert,
                "importance": "high",
            })

    def sort_key(item: dict[str, Any]) -> tuple[int, str]:
        date = str(item.get("date") or "")
        return (0 if date else 1, date)

    events = sorted(events, key=sort_key, reverse=True)[:max_events]
    return {
        "symbol": symbol,
        "timeline": events,
        "count": len(events),
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


@cached(general_cache, ttl=1800)
def evaluate_signal_quality(symbol: str, lookback_months: int = 6, holding_days: int = 20) -> dict:
    """
    Lightweight evaluation layer for the signal engine's price-action core.

    This does NOT replay every live factor (news, insider, pledge) historically.
    It evaluates the price/volume/trend core on rolling historical checkpoints
    to give an honest proof layer before making accuracy claims.
    """
    symbol = _normalize_symbol(symbol)
    stock_hist = _safe(_price_history, symbol, f"{max(lookback_months, 3)}mo")
    index_hist = _safe(lambda: yf.Ticker("^NSEI").history(period=f"{max(lookback_months, 3)}mo", interval="1d"))

    if not isinstance(stock_hist, pd.DataFrame) or stock_hist.empty or len(stock_hist) < 90:
        return {
            "symbol": symbol,
            "error": "Not enough historical data to evaluate signal quality.",
        }

    checkpoints = []
    step = max(10, holding_days)
    latest_idx = len(stock_hist) - holding_days - 1
    for idx in range(60, latest_idx, step):
        sub_stock = stock_hist.iloc[: idx + 1].copy()
        sub_index = index_hist.iloc[: idx + 1].copy() if isinstance(index_hist, pd.DataFrame) and not index_hist.empty else None
        snapshot = _build_price_action_snapshot(sub_stock, sub_index, holding_days=holding_days)
        entry_price = float(stock_hist["Close"].iloc[idx])
        future_price = float(stock_hist["Close"].iloc[idx + holding_days])
        future_return = round((future_price - entry_price) / entry_price * 100, 2)

        signal = snapshot["signal"]
        if signal == "BUY":
            hit = future_return > 2
        elif signal == "SELL":
            hit = future_return < -2
        else:
            hit = abs(future_return) <= 5

        checkpoints.append({
            "date": str(stock_hist.index[idx].date()),
            "signal": signal,
            "score": snapshot["score"],
            "future_return_pct": future_return,
            "hit": hit,
        })

    if not checkpoints:
        return {
            "symbol": symbol,
            "error": "Could not build enough checkpoints for evaluation.",
        }

    hits = sum(1 for item in checkpoints if item["hit"])
    buys = [item for item in checkpoints if item["signal"] == "BUY"]
    sells = [item for item in checkpoints if item["signal"] == "SELL"]
    holds = [item for item in checkpoints if item["signal"] == "HOLD"]

    def avg_return(rows: list[dict[str, Any]]) -> float | None:
        if not rows:
            return None
        return round(sum(float(item["future_return_pct"]) for item in rows) / len(rows), 2)

    return {
        "symbol": symbol,
        "method": "price_action_core_backtest",
        "lookback_months": lookback_months,
        "holding_days": holding_days,
        "checkpoint_count": len(checkpoints),
        "hit_rate_pct": round(hits / len(checkpoints) * 100, 1),
        "avg_future_return_pct": avg_return(checkpoints),
        "by_signal": {
            "buy_count": len(buys),
            "buy_avg_return_pct": avg_return(buys),
            "sell_count": len(sells),
            "sell_avg_return_pct": avg_return(sells),
            "hold_count": len(holds),
            "hold_avg_return_pct": avg_return(holds),
        },
        "sample_checkpoints": checkpoints[-5:],
        "note": (
            "This evaluates the signal score's price-action core only. "
            "It is a proof layer for discipline and honesty, not a claim that the full live system has this exact accuracy."
        ),
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
