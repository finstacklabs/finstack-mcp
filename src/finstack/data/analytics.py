"""
FinStack Analytics Engine

Technical indicators, stock screening, portfolio analysis, backtesting.
All computed locally using pandas + numpy — zero API cost.
"""

import logging
from datetime import datetime

import yfinance as yf
import pandas as pd

from finstack.utils.cache import cached, historical_cache, general_cache
from finstack.utils.helpers import (
    validate_symbol, to_nse_symbol, clean_nan, safe_get, format_market_cap,
)

logger = logging.getLogger("finstack.data.analytics")


# ===== TECHNICAL INDICATORS =====

@cached(general_cache, ttl=600)
def compute_technical_indicators(
    symbol: str,
    period: str = "6mo",
    indicators: list[str] | None = None,
) -> dict:
    """
    Compute technical indicators for a stock.

    Supports: RSI, MACD, SMA (20/50/200), EMA (12/26), Bollinger Bands,
    VWAP, ATR, Stochastic, ADX, OBV.
    """
    symbol = validate_symbol(symbol)

    # Try NSE first, then raw
    for yf_sym in [to_nse_symbol(symbol), symbol]:
        try:
            ticker = yf.Ticker(yf_sym)
            hist = ticker.history(period=period, interval="1d")
            if not hist.empty:
                break
        except Exception:
            continue
    else:
        return {"error": True, "message": f"No data for '{symbol}'."}

    if len(hist) < 20:
        return {
            "error": True,
            "message": f"Not enough data points ({len(hist)}) for technical analysis. Need at least 20.",
            "suggestion": "Try a longer period like '6mo' or '1y'."
        }

    close = hist["Close"]
    high = hist["High"]
    low = hist["Low"]
    volume = hist["Volume"]

    # Default to all indicators
    if not indicators:
        indicators = ["RSI", "MACD", "SMA", "EMA", "BBANDS", "ATR", "STOCH", "ADX", "OBV"]

    result = {
        "symbol": symbol.replace(".NS", "").replace(".BO", ""),
        "period": period,
        "data_points": len(hist),
        "latest_price": round(float(close.iloc[-1]), 2),
        "indicators": {},
    }

    for ind in [i.upper() for i in indicators]:
        try:
            if ind == "RSI":
                # RSI 14-period
                delta = close.diff()
                gain = delta.where(delta > 0, 0).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss.replace(0, float("nan"))
                rsi = 100 - (100 / (1 + rs))
                current_rsi = round(float(rsi.iloc[-1]), 2) if pd.notna(rsi.iloc[-1]) else None

                signal = "Neutral"
                if current_rsi and current_rsi > 70:
                    signal = "Overbought (consider selling)"
                elif current_rsi and current_rsi < 30:
                    signal = "Oversold (consider buying)"

                result["indicators"]["RSI"] = {
                    "value": current_rsi,
                    "period": 14,
                    "signal": signal,
                    "history_5d": [round(float(v), 2) for v in rsi.iloc[-5:] if pd.notna(v)],
                }

            elif ind == "MACD":
                ema12 = close.ewm(span=12, adjust=False).mean()
                ema26 = close.ewm(span=26, adjust=False).mean()
                macd_line = ema12 - ema26
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                histogram = macd_line - signal_line

                current_macd = round(float(macd_line.iloc[-1]), 2) if pd.notna(macd_line.iloc[-1]) else None
                current_signal = round(float(signal_line.iloc[-1]), 2) if pd.notna(signal_line.iloc[-1]) else None
                current_hist = round(float(histogram.iloc[-1]), 2) if pd.notna(histogram.iloc[-1]) else None

                signal = "Neutral"
                if current_macd and current_signal:
                    if current_macd > current_signal:
                        signal = "Bullish (MACD above signal)"
                    else:
                        signal = "Bearish (MACD below signal)"

                result["indicators"]["MACD"] = {
                    "macd": current_macd,
                    "signal_line": current_signal,
                    "histogram": current_hist,
                    "signal": signal,
                }

            elif ind == "SMA":
                sma20 = close.rolling(window=20).mean()
                sma50 = close.rolling(window=50).mean()
                sma200 = close.rolling(window=200).mean()

                current_price = float(close.iloc[-1])
                sma20_val = round(float(sma20.iloc[-1]), 2) if pd.notna(sma20.iloc[-1]) else None
                sma50_val = round(float(sma50.iloc[-1]), 2) if pd.notna(sma50.iloc[-1]) else None
                sma200_val = round(float(sma200.iloc[-1]), 2) if pd.notna(sma200.iloc[-1]) else None

                signals = []
                if sma20_val and current_price > sma20_val:
                    signals.append("Above SMA20 (short-term bullish)")
                if sma50_val and sma20_val and sma20_val > sma50_val:
                    signals.append("SMA20 > SMA50 (golden cross trend)")
                if sma200_val and current_price < sma200_val:
                    signals.append("Below SMA200 (long-term bearish)")

                result["indicators"]["SMA"] = {
                    "sma_20": sma20_val,
                    "sma_50": sma50_val,
                    "sma_200": sma200_val,
                    "price_vs_sma": signals if signals else ["Neutral"],
                }

            elif ind == "EMA":
                ema12 = close.ewm(span=12, adjust=False).mean()
                ema26 = close.ewm(span=26, adjust=False).mean()

                result["indicators"]["EMA"] = {
                    "ema_12": round(float(ema12.iloc[-1]), 2) if pd.notna(ema12.iloc[-1]) else None,
                    "ema_26": round(float(ema26.iloc[-1]), 2) if pd.notna(ema26.iloc[-1]) else None,
                }

            elif ind == "BBANDS":
                sma20 = close.rolling(window=20).mean()
                std20 = close.rolling(window=20).std()
                upper = sma20 + (std20 * 2)
                lower = sma20 - (std20 * 2)

                current_price = float(close.iloc[-1])
                upper_val = round(float(upper.iloc[-1]), 2) if pd.notna(upper.iloc[-1]) else None
                lower_val = round(float(lower.iloc[-1]), 2) if pd.notna(lower.iloc[-1]) else None
                mid_val = round(float(sma20.iloc[-1]), 2) if pd.notna(sma20.iloc[-1]) else None

                signal = "Neutral"
                if upper_val and current_price > upper_val:
                    signal = "Above upper band (potentially overbought)"
                elif lower_val and current_price < lower_val:
                    signal = "Below lower band (potentially oversold)"

                result["indicators"]["BOLLINGER_BANDS"] = {
                    "upper": upper_val,
                    "middle": mid_val,
                    "lower": lower_val,
                    "bandwidth": round(float((upper.iloc[-1] - lower.iloc[-1]) / sma20.iloc[-1] * 100), 2)
                               if pd.notna(upper.iloc[-1]) and pd.notna(sma20.iloc[-1]) else None,
                    "signal": signal,
                }

            elif ind == "ATR":
                tr1 = high - low
                tr2 = abs(high - close.shift())
                tr3 = abs(low - close.shift())
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = tr.rolling(window=14).mean()

                result["indicators"]["ATR"] = {
                    "value": round(float(atr.iloc[-1]), 2) if pd.notna(atr.iloc[-1]) else None,
                    "period": 14,
                    "as_pct_of_price": round(float(atr.iloc[-1] / close.iloc[-1] * 100), 2)
                                       if pd.notna(atr.iloc[-1]) else None,
                }

            elif ind == "STOCH":
                low14 = low.rolling(window=14).min()
                high14 = high.rolling(window=14).max()
                k = ((close - low14) / (high14 - low14)) * 100
                d = k.rolling(window=3).mean()

                k_val = round(float(k.iloc[-1]), 2) if pd.notna(k.iloc[-1]) else None
                d_val = round(float(d.iloc[-1]), 2) if pd.notna(d.iloc[-1]) else None

                signal = "Neutral"
                if k_val and k_val > 80:
                    signal = "Overbought"
                elif k_val and k_val < 20:
                    signal = "Oversold"

                result["indicators"]["STOCHASTIC"] = {
                    "k": k_val,
                    "d": d_val,
                    "signal": signal,
                }

            elif ind == "ADX":
                plus_dm = high.diff()
                minus_dm = -low.diff()
                plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
                minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

                tr1 = high - low
                tr2 = abs(high - close.shift())
                tr3 = abs(low - close.shift())
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

                atr14 = tr.rolling(window=14).mean()
                plus_di = (plus_dm.rolling(window=14).mean() / atr14) * 100
                minus_di = (minus_dm.rolling(window=14).mean() / atr14) * 100
                dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
                adx = dx.rolling(window=14).mean()

                adx_val = round(float(adx.iloc[-1]), 2) if pd.notna(adx.iloc[-1]) else None

                signal = "No clear trend"
                if adx_val:
                    if adx_val > 50:
                        signal = "Very strong trend"
                    elif adx_val > 25:
                        signal = "Strong trend"
                    else:
                        signal = "Weak/no trend"

                result["indicators"]["ADX"] = {
                    "value": adx_val,
                    "plus_di": round(float(plus_di.iloc[-1]), 2) if pd.notna(plus_di.iloc[-1]) else None,
                    "minus_di": round(float(minus_di.iloc[-1]), 2) if pd.notna(minus_di.iloc[-1]) else None,
                    "signal": signal,
                }

            elif ind == "OBV":
                obv = (volume * (~close.diff().le(0)).astype(int) * 2 - 1).cumsum()
                result["indicators"]["OBV"] = {
                    "value": int(obv.iloc[-1]) if pd.notna(obv.iloc[-1]) else None,
                    "change_5d": int(obv.iloc[-1] - obv.iloc[-5]) if len(obv) >= 5 else None,
                }

        except Exception as e:
            result["indicators"][ind] = {"error": str(e)}

    # Overall signal summary
    signals = []
    rsi_data = result["indicators"].get("RSI", {})
    macd_data = result["indicators"].get("MACD", {})
    if rsi_data.get("value") and rsi_data["value"] < 30:
        signals.append("RSI oversold")
    if rsi_data.get("value") and rsi_data["value"] > 70:
        signals.append("RSI overbought")
    if macd_data.get("signal") and "Bullish" in macd_data.get("signal", ""):
        signals.append("MACD bullish")
    if macd_data.get("signal") and "Bearish" in macd_data.get("signal", ""):
        signals.append("MACD bearish")

    result["overall_signals"] = signals if signals else ["No strong signals"]
    result["timestamp"] = datetime.now().isoformat()

    return clean_nan(result)


# ===== SUPPORT & RESISTANCE =====

@cached(general_cache, ttl=1800)
def compute_support_resistance(symbol: str, period: str = "6mo") -> dict:
    """Compute key support and resistance levels using pivot points and price action."""
    symbol = validate_symbol(symbol)

    for yf_sym in [to_nse_symbol(symbol), symbol]:
        try:
            ticker = yf.Ticker(yf_sym)
            hist = ticker.history(period=period, interval="1d")
            if not hist.empty:
                break
        except Exception:
            continue
    else:
        return {"error": True, "message": f"No data for '{symbol}'."}

    close = hist["Close"]
    high = hist["High"]
    low = hist["Low"]

    current_price = float(close.iloc[-1])
    period_high = float(high.max())
    period_low = float(low.min())

    # Classic Pivot Points (using last trading day)
    last_high = float(high.iloc[-1])
    last_low = float(low.iloc[-1])
    last_close = float(close.iloc[-1])

    pivot = (last_high + last_low + last_close) / 3
    r1 = 2 * pivot - last_low
    s1 = 2 * pivot - last_high
    r2 = pivot + (last_high - last_low)
    s2 = pivot - (last_high - last_low)
    r3 = last_high + 2 * (pivot - last_low)
    s3 = last_low - 2 * (last_high - pivot)

    # Find key levels from price action (local highs/lows)
    window = 10
    local_highs = []
    local_lows = []

    for i in range(window, len(hist) - window):
        if float(high.iloc[i]) == float(high.iloc[i - window:i + window + 1].max()):
            local_highs.append(round(float(high.iloc[i]), 2))
        if float(low.iloc[i]) == float(low.iloc[i - window:i + window + 1].min()):
            local_lows.append(round(float(low.iloc[i]), 2))

    # Cluster nearby levels (within 1.5%)
    def cluster_levels(levels, threshold_pct=1.5):
        if not levels:
            return []
        levels = sorted(set(levels))
        clusters = []
        current_cluster = [levels[0]]
        for lvl in levels[1:]:
            if (lvl - current_cluster[0]) / current_cluster[0] * 100 < threshold_pct:
                current_cluster.append(lvl)
            else:
                clusters.append(round(sum(current_cluster) / len(current_cluster), 2))
                current_cluster = [lvl]
        clusters.append(round(sum(current_cluster) / len(current_cluster), 2))
        return clusters

    resistance_levels = [lv for lv in cluster_levels(local_highs) if lv > current_price][:3]
    support_levels = [lv for lv in cluster_levels(local_lows) if lv < current_price][-3:]

    return clean_nan({
        "symbol": symbol.replace(".NS", "").replace(".BO", ""),
        "current_price": round(current_price, 2),
        "pivot_points": {
            "pivot": round(pivot, 2),
            "resistance_1": round(r1, 2),
            "resistance_2": round(r2, 2),
            "resistance_3": round(r3, 2),
            "support_1": round(s1, 2),
            "support_2": round(s2, 2),
            "support_3": round(s3, 2),
        },
        "price_action_levels": {
            "key_resistance": resistance_levels,
            "key_support": support_levels,
        },
        "period_range": {
            "high": round(period_high, 2),
            "low": round(period_low, 2),
        },
        "timestamp": datetime.now().isoformat(),
    })


# ===== STOCK SCREENER =====

@cached(general_cache, ttl=900)
def screen_stocks(
    exchange: str = "NSE",
    pe_max: float | None = None,
    pe_min: float | None = None,
    roe_min: float | None = None,
    market_cap_min: float | None = None,
    dividend_yield_min: float | None = None,
    debt_equity_max: float | None = None,
    sector: str | None = None,
    limit: int = 15,
) -> dict:
    """Screen stocks based on multiple financial criteria."""

    # Universe of stocks to screen
    if exchange.upper() == "NSE":
        universe = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
            "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
            "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
            "TITAN.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "WIPRO.NS", "HCLTECH.NS",
            "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TATASTEEL.NS", "ADANIENT.NS",
            "NESTLEIND.NS", "ULTRACEMCO.NS", "TECHM.NS", "BAJAJFINSV.NS",
            "DIVISLAB.NS", "DRREDDY.NS", "CIPLA.NS", "BRITANNIA.NS", "APOLLOHOSP.NS",
            "COALINDIA.NS", "BPCL.NS", "TATACONSUM.NS", "HEROMOTOCO.NS", "HINDALCO.NS",
            "EICHERMOT.NS", "GRASIM.NS", "INDUSINDBK.NS", "SBILIFE.NS", "HDFCLIFE.NS",
        ]
    else:
        universe = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
            "JPM", "V", "JNJ", "WMT", "PG", "MA", "HD", "KO", "PEP", "ABBV",
            "MRK", "COST", "CRM", "ORCL", "NFLX", "AMD", "INTC", "DIS",
        ]

    matches = []
    errors = 0

    for sym in universe:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            if not info or info.get("regularMarketPrice") is None:
                errors += 1
                continue

            # Apply filters
            pe = safe_get(info, "trailingPE")
            roe = safe_get(info, "returnOnEquity")
            mcap = safe_get(info, "marketCap")
            dy = safe_get(info, "dividendYield")
            de = safe_get(info, "debtToEquity")
            stock_sector = safe_get(info, "sector", default="")

            if pe_max and pe and pe > pe_max:
                continue
            if pe_min and pe and pe < pe_min:
                continue
            if roe_min and roe and roe < roe_min / 100:
                continue
            if market_cap_min and mcap and mcap < market_cap_min:
                continue
            if dividend_yield_min and dy and dy < dividend_yield_min / 100:
                continue
            if debt_equity_max and de and de > debt_equity_max:
                continue
            if sector and sector.lower() not in stock_sector.lower():
                continue

            matches.append({
                "symbol": sym.replace(".NS", "").replace(".BO", ""),
                "name": safe_get(info, "longName") or safe_get(info, "shortName", default=sym),
                "price": safe_get(info, "regularMarketPrice"),
                "pe_ratio": round(pe, 2) if pe else None,
                "roe": round(roe * 100, 2) if roe else None,
                "market_cap": mcap,
                "market_cap_fmt": format_market_cap(mcap),
                "dividend_yield": round(dy * 100, 2) if dy else None,
                "debt_to_equity": round(de, 2) if de else None,
                "sector": stock_sector,
            })

            if len(matches) >= limit:
                break

        except Exception:
            errors += 1
            continue

    filters_applied = {}
    if pe_max:
        filters_applied["pe_max"] = pe_max
    if pe_min:
        filters_applied["pe_min"] = pe_min
    if roe_min:
        filters_applied["roe_min"] = f"{roe_min}%"
    if market_cap_min:
        filters_applied["market_cap_min"] = format_market_cap(market_cap_min)
    if dividend_yield_min:
        filters_applied["dividend_yield_min"] = f"{dividend_yield_min}%"
    if debt_equity_max:
        filters_applied["debt_equity_max"] = debt_equity_max
    if sector:
        filters_applied["sector"] = sector

    return clean_nan({
        "exchange": exchange.upper(),
        "filters": filters_applied,
        "matches": len(matches),
        "scanned": len(universe),
        "stocks": matches,
        "timestamp": datetime.now().isoformat(),
    })


# ===== COMPARE STOCKS =====

@cached(general_cache, ttl=600)
def compare_stocks(symbols: list[str]) -> dict:
    """Side-by-side comparison of 2-5 stocks."""
    if len(symbols) < 2:
        return {"error": True, "message": "Need at least 2 symbols to compare."}
    if len(symbols) > 5:
        symbols = symbols[:5]

    results = []
    for sym in symbols:
        sym = validate_symbol(sym)
        for yf_sym in [to_nse_symbol(sym), sym]:
            try:
                ticker = yf.Ticker(yf_sym)
                info = ticker.info
                if info and info.get("regularMarketPrice") is not None:
                    results.append({
                        "symbol": sym.replace(".NS", "").replace(".BO", ""),
                        "name": safe_get(info, "longName") or sym,
                        "price": safe_get(info, "regularMarketPrice"),
                        "change_pct": safe_get(info, "regularMarketChangePercent"),
                        "market_cap": safe_get(info, "marketCap"),
                        "market_cap_fmt": format_market_cap(safe_get(info, "marketCap")),
                        "pe_ratio": safe_get(info, "trailingPE"),
                        "pb_ratio": safe_get(info, "priceToBook"),
                        "roe": round(safe_get(info, "returnOnEquity", default=0) * 100, 2)
                               if safe_get(info, "returnOnEquity") else None,
                        "profit_margin": round(safe_get(info, "profitMargins", default=0) * 100, 2)
                                         if safe_get(info, "profitMargins") else None,
                        "revenue_growth": round(safe_get(info, "revenueGrowth", default=0) * 100, 2)
                                          if safe_get(info, "revenueGrowth") else None,
                        "debt_to_equity": safe_get(info, "debtToEquity"),
                        "dividend_yield": round(safe_get(info, "dividendYield", default=0) * 100, 2)
                                          if safe_get(info, "dividendYield") else None,
                        "beta": safe_get(info, "beta"),
                        "sector": safe_get(info, "sector"),
                        "52w_high": safe_get(info, "fiftyTwoWeekHigh"),
                        "52w_low": safe_get(info, "fiftyTwoWeekLow"),
                    })
                    break
            except Exception:
                continue

    return clean_nan({
        "comparison": results,
        "count": len(results),
        "timestamp": datetime.now().isoformat(),
    })


# ===== SECTOR PERFORMANCE =====

@cached(general_cache, ttl=600)
def get_sector_performance() -> dict:
    """Get performance of Nifty sectoral indices."""
    sectors = {
        "Nifty 50": "^NSEI",
        "Bank Nifty": "^NSEBANK",
        "Nifty IT": "^CNXIT",
        "Nifty Pharma": "^CNXPHARMA",
        "Nifty FMCG": "^CNXFMCG",
        "Nifty Auto": "^CNXAUTO",
        "Nifty Metal": "^CNXMETAL",
        "Nifty Realty": "^CNXREALTY",
        "Nifty Energy": "^CNXENERGY",
    }

    results = []
    for name, sym in sectors.items():
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="5d", interval="1d")
            if hist.empty or len(hist) < 2:
                continue

            prev = float(hist["Close"].iloc[-2])
            curr = float(hist["Close"].iloc[-1])
            change_pct = ((curr - prev) / prev) * 100

            results.append({
                "sector": name,
                "value": round(curr, 2),
                "change_pct": round(change_pct, 2),
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["change_pct"], reverse=True)

    return clean_nan({
        "sectors": results,
        "best_performer": results[0] if results else None,
        "worst_performer": results[-1] if results else None,
        "timestamp": datetime.now().isoformat(),
    })


# ===== PORTFOLIO ANALYSIS =====

def analyze_portfolio(
    holdings: list[dict],
) -> dict:
    """
    Analyze a portfolio.

    Args:
        holdings: List of {"symbol": "RELIANCE", "quantity": 10, "buy_price": 2500}
    """
    if not holdings:
        return {"error": True, "message": "No holdings provided."}

    portfolio = []
    total_invested = 0
    total_current = 0

    for h in holdings:
        sym = validate_symbol(h.get("symbol", ""))
        qty = h.get("quantity", 0)
        buy_price = h.get("buy_price", 0)

        if qty <= 0 or buy_price <= 0:
            continue

        for yf_sym in [to_nse_symbol(sym), sym]:
            try:
                ticker = yf.Ticker(yf_sym)
                info = ticker.info
                if info and info.get("regularMarketPrice") is not None:
                    current_price = float(info["regularMarketPrice"])
                    invested = buy_price * qty
                    current = current_price * qty
                    pnl = current - invested
                    pnl_pct = (pnl / invested) * 100

                    total_invested += invested
                    total_current += current

                    portfolio.append({
                        "symbol": sym.replace(".NS", "").replace(".BO", ""),
                        "quantity": qty,
                        "buy_price": buy_price,
                        "current_price": round(current_price, 2),
                        "invested": round(invested, 2),
                        "current_value": round(current, 2),
                        "pnl": round(pnl, 2),
                        "pnl_pct": round(pnl_pct, 2),
                        "weight_pct": 0,  # Calculated below
                    })
                    break
            except Exception:
                continue

    # Calculate weights
    for p in portfolio:
        p["weight_pct"] = round((p["current_value"] / total_current) * 100, 2) if total_current > 0 else 0

    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    # Concentration risk
    max_weight = max((p["weight_pct"] for p in portfolio), default=0)
    concentration_risk = "High" if max_weight > 40 else "Medium" if max_weight > 25 else "Low"

    return clean_nan({
        "summary": {
            "total_invested": round(total_invested, 2),
            "current_value": round(total_current, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "num_holdings": len(portfolio),
            "concentration_risk": concentration_risk,
            "highest_weight": f"{max_weight}%",
        },
        "holdings": sorted(portfolio, key=lambda x: x["current_value"], reverse=True),
        "winners": [p for p in portfolio if p["pnl"] > 0],
        "losers": [p for p in portfolio if p["pnl"] < 0],
        "timestamp": datetime.now().isoformat(),
    })


# ===== BACKTEST =====

@cached(historical_cache, ttl=86400)
def backtest_sma_crossover(
    symbol: str,
    short_window: int = 20,
    long_window: int = 50,
    period: str = "2y",
    initial_capital: float = 100000,
) -> dict:
    """Simple SMA crossover backtest."""
    symbol = validate_symbol(symbol)

    for yf_sym in [to_nse_symbol(symbol), symbol]:
        try:
            ticker = yf.Ticker(yf_sym)
            hist = ticker.history(period=period, interval="1d")
            if not hist.empty:
                break
        except Exception:
            continue
    else:
        return {"error": True, "message": f"No data for '{symbol}'."}

    if len(hist) < long_window + 10:
        return {"error": True, "message": f"Not enough data. Need at least {long_window + 10} days."}

    close = hist["Close"]
    sma_short = close.rolling(window=short_window).mean()
    sma_long = close.rolling(window=long_window).mean()

    # Generate signals
    position = 0  # 0 = no position, 1 = long
    capital = initial_capital
    shares = 0
    trades = []

    for i in range(long_window, len(close)):
        if sma_short.iloc[i] > sma_long.iloc[i] and position == 0:
            # Buy signal
            price = float(close.iloc[i])
            shares = int(capital / price)
            if shares > 0:
                capital -= shares * price
                position = 1
                trades.append({
                    "date": hist.index[i].strftime("%Y-%m-%d"),
                    "action": "BUY",
                    "price": round(price, 2),
                    "shares": shares,
                })

        elif sma_short.iloc[i] < sma_long.iloc[i] and position == 1:
            # Sell signal
            price = float(close.iloc[i])
            capital += shares * price
            trades.append({
                "date": hist.index[i].strftime("%Y-%m-%d"),
                "action": "SELL",
                "price": round(price, 2),
                "shares": shares,
                "pnl": round(shares * (price - trades[-1]["price"]), 2),
            })
            shares = 0
            position = 0

    # Close any open position
    if position == 1:
        final_price = float(close.iloc[-1])
        capital += shares * final_price

    final_value = capital
    total_return = ((final_value - initial_capital) / initial_capital) * 100

    # Buy and hold comparison
    buy_hold_return = float((close.iloc[-1] / close.iloc[long_window] - 1) * 100)

    winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
    losing_trades = [t for t in trades if t.get("pnl", 0) < 0]

    return clean_nan({
        "symbol": symbol.replace(".NS", "").replace(".BO", ""),
        "strategy": f"SMA {short_window}/{long_window} Crossover",
        "period": period,
        "results": {
            "initial_capital": initial_capital,
            "final_value": round(final_value, 2),
            "total_return_pct": round(total_return, 2),
            "buy_hold_return_pct": round(buy_hold_return, 2),
            "strategy_vs_buyhold": round(total_return - buy_hold_return, 2),
            "total_trades": len([t for t in trades if t["action"] == "SELL"]),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(len(winning_trades) / max(len(winning_trades) + len(losing_trades), 1) * 100, 1),
        },
        "trades": trades[-10:],  # Last 10 trades
        "verdict": "Strategy BEAT buy-and-hold" if total_return > buy_hold_return
                   else "Buy-and-hold was BETTER",
        "disclaimer": "Past performance does not guarantee future results. This is not financial advice.",
        "timestamp": datetime.now().isoformat(),
    })
