import json

from finstack.server import TOOL_CATALOG, TOTAL_TOOLS, finstack_info, health_check


def test_tool_catalog_matches_expected_total():
    assert len(TOOL_CATALOG) == 89
    assert TOTAL_TOOLS == 90


def test_finstack_info_reports_catalog_count():
    info = json.loads(finstack_info())

    assert info["tools_available"] == len(TOOL_CATALOG)
    assert len(info["tools"]) == len(TOOL_CATALOG)


def test_health_check_uses_total_tool_count():
    status = health_check()

    assert status["tools"] == TOTAL_TOOLS
