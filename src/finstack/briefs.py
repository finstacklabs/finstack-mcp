"""
FinStack daily brief generator.

This module is the first bridge from the open-source MCP engine to the paid
Indian market daily brief product.
"""

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
    status = market_status.get("status", "UNKNOWN")
    lines = [f"Indian market brief for {datetime.now().strftime('%Y-%m-%d')}."]
    lines.append(f"Market status: {status}.")

    if gainers:
        top = gainers[0]
        lines.append(
            f"Top momentum came from {top.get('symbol', 'N/A')} with "
            f"{top.get('change_percent', top.get('change_pct', 'N/A'))}% change."
        )

    if losers:
        lag = losers[0]
        lines.append(
            f"Main weakness showed in {lag.get('symbol', 'N/A')} with "
            f"{lag.get('change_percent', lag.get('change_pct', 'N/A'))}% move."
        )

    if watchlist:
        lines.append(f"Watchlist coverage included {len(watchlist)} tracked names.")

    lines.append("Use this output as a first-pass market briefing, not investment advice.")
    return " ".join(lines)


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

    return {
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an Indian market daily brief.")
    parser.add_argument(
        "--watchlist",
        default="",
        help="Comma-separated watchlist symbols, for example RELIANCE,TCS,HDFCBANK",
    )
    parser.add_argument("--date", default="", help="Brief date in YYYY-MM-DD format")
    parser.add_argument("--style", default="concise", help="Narrative style hint")
    args = parser.parse_args()

    watchlist = [symbol for symbol in args.watchlist.split(",") if symbol.strip()]
    payload = generate_daily_brief(
        watchlist=watchlist,
        brief_date=args.date or None,
        style=args.style,
    )
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
