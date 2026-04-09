# Proof And Accuracy Notes

FinStack should be marketed as a decision-support and market-intelligence stack, not as a guaranteed stock picker.

## What is already true

- `evaluate_signal_quality` gives a real evaluation layer for the price-action core.
- `get_stock_signal_score` exposes factor-level reasoning instead of a black-box number.
- `get_stock_brief`, `get_stock_debate`, `get_fno_trade_setup`, and `get_morning_fno_brief` all expose supporting and opposing factors.

## What we can claim safely

- "Multi-factor market intelligence for Indian equities and index options."
- "Built for decision-support, triage, and research workflows."
- "Includes an evaluation layer for the price-action core."
- "Shows factors, risks, and conflicting signals instead of pretending certainty."

## What we should not claim yet

- "Guaranteed accuracy"
- "Best stock picks in India"
- "Beats the market"
- "Always profitable"
- "SEBI-grade investment advice"

## Recommended public wording

Use copy like:

> FinStack helps you ask better market questions and get structured signals faster.

Or:

> FinStack is an MCP-native market intelligence layer for Indian equities, F&O setups, stock research, and daily brief workflows.

## Accuracy framing for launch

Best launch posture:

- show one or two evaluated examples
- link to `evaluate_signal_quality`
- explain that some tools are heuristic and context-driven
- explain that live data availability can affect output richness

## Good proof assets to publish

- screenshot of `evaluate_signal_quality("RELIANCE")`
- screenshot or GIF of `get_stock_brief("RELIANCE")`
- screenshot of `get_fno_trade_setup("NIFTY")`
- one morning note example from `get_morning_fno_brief()`

## Suggested FAQ answer

**How accurate is FinStack?**

FinStack is designed as a market-intelligence and research assistant, not a guaranteed advisory engine. Some parts of the stack include evaluation and outcome tracking for the signal core, while other parts are heuristic workflows that expose reasoning, risks, and uncertainty directly. It should be used for decision-support, not blind execution.
