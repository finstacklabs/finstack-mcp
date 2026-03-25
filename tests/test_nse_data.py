import pandas as pd

from finstack.data.nse import get_market_movers
from finstack.data.nse_advanced import _format_calendar_value


class _Columns:
    def get_level_values(self, _index: int):
        return ["RELIANCE.NS", "TCS.NS"]


class _FakeDownload:
    columns = _Columns()

    def __getitem__(self, key: str):
        datasets = {
            "RELIANCE.NS": pd.DataFrame(
                {"Close": [100.0, 103.0], "Volume": [1000, 1200]}
            ),
            "TCS.NS": pd.DataFrame(
                {"Close": [100.0, 98.0], "Volume": [1500, 1300]}
            ),
        }
        return datasets[key]


def test_market_movers_losers_only_include_negative_changes(monkeypatch):
    monkeypatch.setattr("finstack.data.nse.yf.download", lambda *args, **kwargs: _FakeDownload())

    result = get_market_movers("losers")

    assert result["stocks"]
    assert all(item["change_pct"] < 0 for item in result["stocks"])


def test_format_calendar_value_normalizes_dates():
    result = _format_calendar_value([pd.Timestamp("2026-04-24")])

    assert result == ["2026-04-24 00:00:00"] or result == ["2026-04-24"]
