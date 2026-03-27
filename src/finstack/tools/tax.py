"""
FinStack Tax Tools

Tool 40:
  40. calculate_tax_liability - LTCG/STCG tax calculator for Indian equity trades
"""

import json
from datetime import datetime


def _parse_date(date_str: str) -> datetime:
    """Parse date from DD-MM-YYYY or YYYY-MM-DD format."""
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(
        f"Invalid date format: '{date_str}'. Use DD-MM-YYYY (e.g. 15-01-2023)."
    )


def _holding_period_days(buy_date: datetime, sell_date: datetime) -> int:
    return (sell_date - buy_date).days


def _classify_gain(days: int, asset_type: str) -> str:
    """Return LTCG or STCG based on holding period and asset type."""
    if asset_type in ("equity", "mutual_fund_equity"):
        return "LTCG" if days > 365 else "STCG"
    elif asset_type in ("debt_fund", "mutual_fund_debt"):
        # Post April 1 2023 — debt funds taxed at slab rate regardless
        return "DEBT_SLAB"
    else:
        return "LTCG" if days > 365 else "STCG"


def _tax_amount(gain_type: str, profit: float, asset_type: str) -> tuple[float | None, str]:
    """
    Returns (tax_amount, note).
    tax_amount is None when taxed at slab rate (cannot determine without income).
    """
    if profit <= 0:
        return 0.0, "No tax on capital loss. Loss can be carried forward for 8 years."

    if gain_type == "STCG":
        # Section 111A: 20% flat for listed equity/equity MF (post July 2024 budget)
        if asset_type in ("equity", "mutual_fund_equity"):
            tax = profit * 0.20
            return tax, "Section 111A — 20% flat rate on STCG for listed equity (post July 2024 Budget)"
        else:
            return None, "STCG on debt funds is taxed at your income slab rate. Consult a CA for exact liability."

    elif gain_type == "LTCG":
        if asset_type in ("equity", "mutual_fund_equity"):
            # Section 112A: 12.5% above ₹1.25L exemption (post July 2024 budget)
            exemption = 125000.0
            taxable = max(0.0, profit - exemption)
            tax = taxable * 0.125
            note = (
                "Section 112A — 12.5% on LTCG above ₹1,25,000 exemption (post July 2024 Budget). "
                "Note: ₹1.25L exemption is cumulative across ALL equity LTCG in the financial year."
            )
            return tax, note
        else:
            return None, "LTCG on this asset type is taxed at slab rate. Consult a CA."

    elif gain_type == "DEBT_SLAB":
        return None, (
            "Debt mutual funds purchased after April 1, 2023 are taxed at your income slab rate "
            "regardless of holding period. No LTCG benefit or indexation available."
        )

    return None, "Unable to determine tax. Consult a CA."


def compute_tax_liability(
    buy_price: float,
    buy_date_str: str,
    sell_price: float,
    sell_date_str: str,
    quantity: int,
    asset_type: str = "equity",
    symbol: str = "",
) -> dict:
    """Core computation — returns a structured dict."""
    buy_date = _parse_date(buy_date_str)
    sell_date = _parse_date(sell_date_str)

    if sell_date <= buy_date:
        raise ValueError("Sell date must be after buy date.")

    days = _holding_period_days(buy_date, sell_date)
    gain_type = _classify_gain(days, asset_type)

    total_buy = buy_price * quantity
    total_sell = sell_price * quantity
    profit = total_sell - total_buy
    profit_per_share = sell_price - buy_price

    tax, note = _tax_amount(gain_type, profit, asset_type)

    years = days // 365
    months = (days % 365) // 30
    remaining_days = days % 30
    holding_str = f"{years}y {months}m {remaining_days}d" if years else f"{months}m {remaining_days}d"

    return {
        "symbol": symbol.upper() if symbol else "—",
        "asset_type": asset_type,
        "quantity": quantity,
        "buy_price": buy_price,
        "buy_date": buy_date.strftime("%d %b %Y"),
        "sell_price": sell_price,
        "sell_date": sell_date.strftime("%d %b %Y"),
        "holding_period_days": days,
        "holding_period": holding_str,
        "gain_type": gain_type,
        "profit_per_share": round(profit_per_share, 2),
        "total_investment": round(total_buy, 2),
        "total_sale_value": round(total_sell, 2),
        "gross_profit": round(profit, 2),
        "tax_liability": round(tax, 2) if tax is not None else None,
        "tax_note": note,
        "disclaimer": (
            "This is an estimate only. Tax liability depends on your total annual gains, "
            "income slab, and other factors. Consult a SEBI-registered CA for filing."
        ),
    }


def _format_tax_output(result: dict) -> str:
    """Format the tax result into a readable text block."""
    lines = []
    lines.append("=" * 52)
    lines.append("  FinStack Tax Calculator — LTCG / STCG (India)")
    lines.append("=" * 52)

    if result["symbol"] != "—":
        lines.append(f"  Symbol        : {result['symbol']}")
    lines.append(f"  Asset Type    : {result['asset_type'].replace('_', ' ').title()}")
    lines.append(f"  Quantity      : {result['quantity']:,} shares/units")
    lines.append("")
    lines.append(f"  Buy Price     : ₹{result['buy_price']:,.2f}  ({result['buy_date']})")
    lines.append(f"  Sell Price    : ₹{result['sell_price']:,.2f}  ({result['sell_date']})")
    lines.append("")
    lines.append(f"  Holding Period: {result['holding_period']} ({result['holding_period_days']} days)")
    lines.append(f"  Gain Type     : {result['gain_type']}")
    lines.append("")
    lines.append(f"  Total Invested: ₹{result['total_investment']:,.2f}")
    lines.append(f"  Sale Value    : ₹{result['total_sale_value']:,.2f}")

    profit = result["gross_profit"]
    sign = "+" if profit >= 0 else ""
    lines.append(f"  Gross P&L     : {sign}₹{profit:,.2f}")
    lines.append("")

    if result["tax_liability"] is not None:
        lines.append(f"  Tax Liability : ₹{result['tax_liability']:,.2f}")
        net = profit - result["tax_liability"]
        lines.append(f"  Net Profit    : ₹{net:,.2f}")
    else:
        lines.append("  Tax Liability : Taxed at income slab rate")

    lines.append("")
    lines.append(f"  Note: {result['tax_note']}")
    lines.append("")
    lines.append(f"  ⚠ {result['disclaimer']}")
    lines.append("=" * 52)

    return "\n".join(lines)


def register_tax_tools(mcp):
    """Register tax tools with the MCP server."""

    @mcp.tool()
    def calculate_tax_liability(
        buy_price: float,
        buy_date: str,
        sell_price: float,
        sell_date: str,
        quantity: int,
        asset_type: str = "equity",
        symbol: str = "",
    ) -> str:
        """Calculate Indian LTCG / STCG tax liability for an equity or mutual fund trade.

        Applies Indian tax rules (post July 2024 Budget):
        - Listed equity / equity MF STCG (≤365 days): 20% flat (Section 111A)
        - Listed equity / equity MF LTCG (>365 days): 12.5% above ₹1.25L exemption (Section 112A)
        - Debt funds (post Apr 2023): taxed at income slab rate regardless of holding period
        - Capital losses: carried forward for 8 years

        Args:
            buy_price: Purchase price per share/unit in INR
            buy_date: Date of purchase in DD-MM-YYYY format (e.g. 15-01-2023)
            sell_price: Selling price per share/unit in INR
            sell_date: Date of sale in DD-MM-YYYY format (e.g. 20-03-2024)
            quantity: Number of shares or units
            asset_type: One of: equity, mutual_fund_equity, mutual_fund_debt, debt_fund
            symbol: Optional stock/fund symbol for display (e.g. RELIANCE, TCS)

        Returns:
            Formatted tax summary with holding period, gain classification, and tax liability.

        Examples:
            calculate_tax_liability(buy_price=1200, buy_date="01-01-2023",
                                    sell_price=1500, sell_date="15-03-2024",
                                    quantity=100, symbol="RELIANCE")
        """
        try:
            result = compute_tax_liability(
                buy_price=buy_price,
                buy_date_str=buy_date,
                sell_price=sell_price,
                sell_date_str=sell_date,
                quantity=quantity,
                asset_type=asset_type,
                symbol=symbol,
            )
            return _format_tax_output(result)
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Tax calculation failed: {e}"
