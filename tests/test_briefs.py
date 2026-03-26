from finstack.briefs import generate_daily_brief


def test_generate_daily_brief_shapes_output(monkeypatch):
    monkeypatch.setattr("finstack.briefs.get_market_status", lambda: {"status": "OPEN"})
    monkeypatch.setattr("finstack.briefs.get_index_data", lambda name: {"index": name, "value": 100})
    monkeypatch.setattr(
        "finstack.briefs.get_market_movers",
        lambda kind: {"stocks": [{"symbol": f"{kind.upper()}1", "change_pct": 1.5}]},
    )
    monkeypatch.setattr(
        "finstack.briefs.get_sector_performance",
        lambda: {"leaders": [{"sector": "IT", "change_pct": 2.1}]},
    )
    monkeypatch.setattr("finstack.briefs.get_fii_dii_data", lambda: {"data": "ok"})
    monkeypatch.setattr("finstack.briefs.get_bulk_deals", lambda: {"deals": []})
    monkeypatch.setattr(
        "finstack.briefs.get_quarterly_results",
        lambda symbol: {"latest_quarter": "2025-12-31", "quarters": [{"revenue": 10}]},
    )
    monkeypatch.setattr(
        "finstack.briefs.get_corporate_actions",
        lambda symbol: {"actions": [{"date": "2026-03-25", "type": "DIVIDEND"}]},
    )
    monkeypatch.setattr(
        "finstack.briefs.get_earnings_calendar",
        lambda symbol: {"symbol": symbol, "earnings_date": "2026-04-15"},
    )

    brief = generate_daily_brief(["RELIANCE", "TCS"], brief_date="2026-03-25")

    assert brief["brief_type"] == "indian_market_daily_brief"
    assert brief["brief_date"] == "2026-03-25"
    assert brief["indices"]["nifty50"]["index"] == "NIFTY50"
    assert len(brief["watchlist"]) == 2
    assert "Market status: OPEN." in brief["summary"]
    assert "delivery_formats" in brief
    assert "FinStack Brief | 2026-03-25" in brief["delivery_formats"]["plain_text"]
    assert "*FinStack Brief*" in brief["delivery_formats"]["telegram_markdown"]
    assert brief["delivery_formats"]["email"]["subject"].startswith("FinStack Brief | 2026-03-25")
