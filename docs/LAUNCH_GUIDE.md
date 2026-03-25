# Launch Guide

## Goal

Launch `finstack-mcp` today as a clean open-source repo and use it as the public engine for the future paid daily brief product.

## 1. Local Checks

```bash
cd finstack-mcp
pip install -e ".[dev]"
pytest -q -p no:cacheprovider
python -m finstack.server
python -m finstack.briefs --watchlist RELIANCE,TCS,HDFCBANK
```

## 2. GitHub

Create a new public repository named `finstack-mcp`.

Recommended metadata:

- description: `India-first MCP server for NSE/BSE, fundamentals, analytics, and daily research workflows.`
- topics: `mcp`, `finance`, `nse`, `bse`, `stocks`, `india`, `python`, `claude`

Push commands:

```bash
git init
git add .
git commit -m "Launch finstack-mcp v0.3.1"
git branch -M main
git remote add origin https://github.com/<your-username>/finstack-mcp.git
git push -u origin main
```

## 3. PyPI

Build locally:

```bash
python -m pip install build
python -m build
```

Publish with Twine or GitHub Trusted Publishing after you create the project on PyPI.

## 4. MCP Registries

Use the current `server.json` after GitHub and PyPI are live.

Submit the project to the registries you plan to target after the package is public.

## 5. Landing Page

Deploy `landing-page/` as a static site.

Current message:

- FinStack MCP = open-source engine
- FinStack Brief = paid Indian market daily brief

## 6. Demo Story

Use this story consistently in posts and conversations:

1. install `finstack-mcp`
2. use the MCP tools locally
3. show the daily brief generator
4. explain that the paid layer is delivery and workflow, not just access

## 7. After Launch

1. collect first users
2. collect first daily brief feedback
3. build delivery formats
4. validate pricing before adding more features
