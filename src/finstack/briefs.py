"""Daily brief generation and delivery formatting for FinStack."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime

from finstack.data.analytics import get_sector_performance
from finstack.data.nse import get_index_data, get_market_movers, get_market_status
from finstack.data.nse_advanced import (
    get_bulk_deals,
    get_corporate_actions,
    get_earnings_calendar,
    get_fii_dii_data,
    get_quarterly_results,
)


def _safe_list(value: object, limit: int = 5) -> list[dict]:
    if isinstance(value, list):
        return value[:limit]
    return []


def _safe_dict(value: object) -> dict:
    if isinstance(value, dict):
        return value
    return {}


def _format_number(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return "N/A"


def _format_change(entry: dict) -> str:
    change_pct = entry.get("change_percent", entry.get("change_pct"))
    if isinstance(change_pct, (int, float)):
        prefix = "+" if change_pct > 0 else ""
        return f"{prefix}{change_pct:.2f}%"
    return "N/A"


def _first_watchlist_signal(item: dict) -> str:
    earnings = _safe_dict(item.get("earnings"))
    actions = _safe_list(item.get("corporate_actions"), limit=1)
    quarter = _safe_dict(item.get("quarterly_results"))

    if earnings.get("earnings_date"):
        dates = earnings["earnings_date"]
        if isinstance(dates, list) and dates:
            return f"Earnings due {dates[0]}"
        return f"Earnings due {dates}"

    if actions:
        action = actions[0]
        return f"{action.get('type', 'Action')} tracked"

    latest_quarter = quarter.get("latest_quarter")
    if latest_quarter:
        return f"Results updated for {latest_quarter}"

    return "Monitoring"


def _watchlist_section(symbols: list[str]) -> list[dict]:
    results: list[dict] = []
    for symbol in symbols:
        entry: dict = {"symbol": symbol}

        try:
            quarter = _safe_dict(get_quarterly_results(symbol))
            if not quarter.get("error"):
                entry["quarterly_results"] = {
                    "latest_quarter": quarter.get("latest_quarter"),
                    "summary": _safe_list(quarter.get("quarters"), limit=1),
                }
        except Exception as exc:  # pragma: no cover
            entry["quarterly_results_error"] = str(exc)

        try:
            actions = _safe_dict(get_corporate_actions(symbol))
            if not actions.get("error"):
                entry["corporate_actions"] = _safe_list(actions.get("actions"), limit=3)
        except Exception as exc:  # pragma: no cover
            entry["corporate_actions_error"] = str(exc)

        try:
            earnings = _safe_dict(get_earnings_calendar(symbol))
            if not earnings.get("error"):
                entry["earnings"] = earnings
        except Exception as exc:  # pragma: no cover
            entry["earnings_error"] = str(exc)

        results.append(entry)

    return results


def _narrative(
    market_status: dict,
    gainers: list[dict],
    losers: list[dict],
    watchlist: list[dict],
) -> str:
    status = market_status.get("nse_status") or market_status.get("status", "UNKNOWN")
    lines = [f"Indian market brief for {datetime.now().strftime('%Y-%m-%d')}."]
    lines.append(f"Market status: {status}.")

    if gainers:
        top = gainers[0]
        lines.append(
            f"Top momentum came from {top.get('symbol', 'N/A')} with "
            f"{_format_change(top)}."
        )

    if losers:
        lag = losers[0]
        lines.append(
            f"Main weakness showed in {lag.get('symbol', 'N/A')} with "
            f"{_format_change(lag)}."
        )

    if watchlist:
        lines.append(f"Watchlist coverage included {len(watchlist)} tracked names.")

    lines.append("Use this output as a first-pass market briefing, not investment advice.")
    return " ".join(lines)


def _render_plain_text(payload: dict) -> str:
    market_status = _safe_dict(payload.get("market_status"))
    indices = _safe_dict(payload.get("indices"))
    movers = _safe_dict(payload.get("market_movers"))
    watchlist = _safe_list(payload.get("watchlist"))
    sectors = _safe_dict(payload.get("sector_performance"))
    fii_dii = _safe_dict(payload.get("institutional_flow"))

    lines = [
        f"FinStack Brief | {payload.get('brief_date', 'N/A')}",
        f"Market status: {market_status.get('nse_status', market_status.get('status', 'UNKNOWN'))}",
        "",
    ]

    nifty = _safe_dict(indices.get("nifty50"))
    sensex = _safe_dict(indices.get("sensex"))
    bank_nifty = _safe_dict(indices.get("bank_nifty"))
    lines.extend(
        [
            f"Nifty 50: {_format_number(nifty.get('value'))} ({_format_change(nifty)})",
            f"Sensex: {_format_number(sensex.get('value'))} ({_format_change(sensex)})",
            f"Bank Nifty: {_format_number(bank_nifty.get('value'))} ({_format_change(bank_nifty)})",
            "",
        ]
    )

    gainers = _safe_list(movers.get("gainers"), limit=3)
    losers = _safe_list(movers.get("losers"), limit=3)
    if gainers:
        lines.append("Top gainers: " + ", ".join(f"{item['symbol']} {_format_change(item)}" for item in gainers))
    if losers:
        lines.append("Top losers: " + ", ".join(f"{item['symbol']} {_format_change(item)}" for item in losers))

    best_sector = _safe_dict(sectors.get("best_performer"))
    if best_sector:
        lines.append(
            f"Leading sector: {best_sector.get('sector', 'N/A')} ({_format_change(best_sector)})"
        )

    flow_data = _safe_list(fii_dii.get("data"), limit=2)
    if flow_data:
        parts = []
        for row in flow_data:
            parts.append(f"{row.get('category', 'N/A')}: {row.get('netValue', 'N/A')}")
        lines.append("Institutional flow: " + " | ".join(parts))

    if watchlist:
        lines.append("")
        lines.append("Watchlist signals:")
        for item in watchlist:
            lines.append(f"- {item.get('symbol', 'N/A')}: {_first_watchlist_signal(item)}")

    lines.append("")
    lines.append(payload.get("summary", ""))
    return "\n".join(lines).strip()


def _render_telegram(payload: dict) -> str:
    market_status = _safe_dict(payload.get("market_status"))
    indices = _safe_dict(payload.get("indices"))
    movers = _safe_dict(payload.get("market_movers"))
    watchlist = _safe_list(payload.get("watchlist"))

    nifty = _safe_dict(indices.get("nifty50"))
    sensex = _safe_dict(indices.get("sensex"))

    lines = [
        f"*FinStack Brief* | `{payload.get('brief_date', 'N/A')}`",
        f"Market: *{market_status.get('nse_status', market_status.get('status', 'UNKNOWN'))}*",
        "",
        f"Nifty 50: *{_format_number(nifty.get('value'))}* ({_format_change(nifty)})",
        f"Sensex: *{_format_number(sensex.get('value'))}* ({_format_change(sensex)})",
    ]

    gainers = _safe_list(movers.get("gainers"), limit=3)
    losers = _safe_list(movers.get("losers"), limit=3)
    if gainers:
        lines.append("Top gainers: " + ", ".join(f"{item['symbol']} {_format_change(item)}" for item in gainers))
    if losers:
        lines.append("Top losers: " + ", ".join(f"{item['symbol']} {_format_change(item)}" for item in losers))

    if watchlist:
        lines.append("")
        lines.append("*Watchlist*")
        for item in watchlist:
            lines.append(f"- {item.get('symbol', 'N/A')}: {_first_watchlist_signal(item)}")

    lines.append("")
    lines.append(payload.get("summary", ""))
    lines.append("")
    lines.append("_Not investment advice._")
    return "\n".join(lines).strip()


def _render_email(payload: dict) -> dict:
    subject = f"FinStack Brief | {payload.get('brief_date', 'N/A')} | Indian market snapshot"
    plain_text = _render_plain_text(payload)
    html = f"""
<html>
  <body style="margin:0;padding:24px;background:#f6f1e8;color:#171411;font-family:Arial,sans-serif;">
    <div style="max-width:700px;margin:0 auto;background:#fffdf8;border:1px solid #e7dcc8;border-radius:18px;padding:28px;">
      <p style="margin:0 0 8px;color:#0d6b57;font-weight:700;">FinStack Brief</p>
      <h1 style="margin:0 0 18px;font-size:28px;">Indian market snapshot for {payload.get('brief_date', 'N/A')}</h1>
      <pre style="white-space:pre-wrap;font-family:Arial,sans-serif;line-height:1.7;font-size:15px;margin:0;">{plain_text}</pre>
    </div>
  </body>
</html>
""".strip()
    return {
        "subject": subject,
        "text": plain_text,
        "html": html,
    }


def _delivery_formats(payload: dict) -> dict:
    plain_text = _render_plain_text(payload)
    telegram = _render_telegram(payload)
    email = _render_email(payload)
    return {
        "plain_text": plain_text,
        "telegram_markdown": telegram,
        "email": email,
    }


def generate_daily_brief(
    watchlist: list[str] | None = None,
    brief_date: str | None = None,
    style: str = "concise",
) -> dict:
    """Generate a structured Indian market daily brief."""
    watchlist = [symbol.strip().upper() for symbol in (watchlist or []) if symbol.strip()]
    brief_date = brief_date or date.today().isoformat()

    market_status = _safe_dict(get_market_status())
    nifty = _safe_dict(get_index_data("NIFTY50"))
    sensex = _safe_dict(get_index_data("SENSEX"))
    bank_nifty = _safe_dict(get_index_data("BANKNIFTY"))
    gainers = _safe_list(_safe_dict(get_market_movers("gainers")).get("stocks"))
    losers = _safe_list(_safe_dict(get_market_movers("losers")).get("stocks"))
    active = _safe_list(_safe_dict(get_market_movers("active")).get("stocks"))
    sector_performance = _safe_dict(get_sector_performance())
    fii_dii = _safe_dict(get_fii_dii_data())
    bulk_deals = _safe_dict(get_bulk_deals())
    watchlist_data = _watchlist_section(watchlist)

    payload = {
        "brief_type": "indian_market_daily_brief",
        "generated_at": datetime.now().isoformat(),
        "brief_date": brief_date,
        "style": style,
        "market_status": market_status,
        "indices": {
            "nifty50": nifty,
            "sensex": sensex,
            "bank_nifty": bank_nifty,
        },
        "market_movers": {
            "gainers": gainers,
            "losers": losers,
            "most_active": active,
        },
        "sector_performance": sector_performance,
        "institutional_flow": fii_dii,
        "bulk_deals": bulk_deals,
        "watchlist": watchlist_data,
        "summary": _narrative(market_status, gainers, losers, watchlist_data),
    }
    payload["delivery_formats"] = _delivery_formats(payload)
    return payload


def get_morning_brief() -> dict:
    """
    8:15 AM pre-market brief for Indian traders.

    Auto-compiles:
      - GIFT Nifty pre-market signal + global overnight
      - FII net flow from yesterday
      - Top 3 stock setups (gainers + unusual movers)
      - Nifty direction probability signal
      - Macro alert (VIX, G-Sec)
      - Earnings due today

    Returns structured JSON + ready-to-send plain text / Telegram format.
    """
    from finstack.data.market_intelligence import get_gift_nifty, get_india_vix
    from finstack.data.probability import get_nifty_outlook

    brief = generate_daily_brief(
        watchlist=["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"],
        style="morning",
    )

    # Augment with GIFT Nifty + VIX + direction probability
    gift  = {}
    vix   = {}
    nifty_outlook = {}

    try:
        gift = get_gift_nifty() or {}
    except Exception:
        pass
    try:
        vix = get_india_vix() or {}
    except Exception:
        pass
    try:
        nifty_outlook = get_nifty_outlook() or {}
    except Exception:
        pass

    brief["pre_market"] = {
        "gift_nifty":      gift,
        "india_vix":       vix,
        "nifty_direction": {
            "probability_up": nifty_outlook.get("probability_up"),
            "signal":         nifty_outlook.get("signal"),
            "bull_factors":   nifty_outlook.get("bull_factors", [])[:2],
            "bear_factors":   nifty_outlook.get("bear_factors", [])[:2],
        },
    }

    # Plain text morning format
    prob = nifty_outlook.get("probability_up")
    gift_val = gift.get("gift_nifty") or gift.get("value", "")
    vix_val  = vix.get("vix") or vix.get("current", "")

    brief["morning_text"] = (
        f"Good morning. FinStack 8:15 AM Brief — {brief.get('brief_date', '')}\n\n"
        f"GIFT Nifty: {gift_val} | India VIX: {vix_val}\n"
        f"Direction: {nifty_outlook.get('signal', 'N/A')} ({prob}% up probability)\n\n"
        + brief.get("delivery_formats", {}).get("plain_text", "")
    )

    return brief


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an Indian market daily brief.")
    parser.add_argument(
        "--watchlist",
        default="",
        help="Comma-separated watchlist symbols, for example RELIANCE,TCS,HDFCBANK",
    )
    parser.add_argument("--date", default="", help="Brief date in YYYY-MM-DD format")
    parser.add_argument("--style", default="concise", help="Narrative style hint")
    parser.add_argument(
        "--output",
        default="json",
        choices=["json", "text", "telegram", "email-text", "email-html"],
        help="Render the brief in a delivery-friendly format",
    )
    args = parser.parse_args()

    watchlist = [symbol for symbol in args.watchlist.split(",") if symbol.strip()]
    payload = generate_daily_brief(
        watchlist=watchlist,
        brief_date=args.date or None,
        style=args.style,
    )

    if args.output == "json":
        print(json.dumps(payload, indent=2, default=str))
    elif args.output == "text":
        print(payload["delivery_formats"]["plain_text"])
    elif args.output == "telegram":
        print(payload["delivery_formats"]["telegram_markdown"])
    elif args.output == "email-text":
        print(payload["delivery_formats"]["email"]["text"])
    elif args.output == "email-html":
        print(payload["delivery_formats"]["email"]["html"])


if __name__ == "__main__":
    main()
