# Contributing to FinStack MCP

Thanks for your interest! Here's how to contribute.

## Setup

```bash
git clone https://github.com/SpawnAgent/finstack-mcp.git
cd finstack-mcp
pip install -e ".[dev]"
```

## Adding a New Tool

1. Add data fetcher function in `src/finstack/data/`
2. Add MCP tool wrapper in `src/finstack/tools/`
3. Register in `src/finstack/server.py`
4. Test with Claude Desktop locally
5. Submit PR

## Code Style

- Python 3.10+, type hints everywhere
- Docstrings on all public functions (Claude reads these)
- Use `clean_nan()` on all return dicts
- Use `@cached()` decorator for API calls
- Return `{"error": True, "message": "..."}` on failures

## Tool Naming

- Indian tools: `nse_*` or `bse_*` prefix
- Global tools: `stock_*`, `crypto_*`, `forex_*`
- Analytics: descriptive name (`technical_indicators`, `stock_screener`)

## Questions?

Open an issue or reach out on [Twitter/X @SpawnAgent](https://x.com/SpawnAgent).
