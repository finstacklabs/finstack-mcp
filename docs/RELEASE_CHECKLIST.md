# Release Checklist

## Before tagging

- [ ] Confirm version in `pyproject.toml`
- [ ] Confirm version in `src/finstack/__init__.py`
- [ ] Update `CHANGELOG.md`
- [ ] Recheck README tool count and demo links
- [ ] Recheck docs links in README

## Validation

- [ ] `python -m py_compile src/finstack/server.py`
- [ ] `python -m py_compile src/finstack/tools/probability.py`
- [ ] `python -m py_compile src/finstack/tools/intelligence.py`
- [ ] `python -m py_compile src/finstack/briefs.py`
- [ ] Run a spot-check on:
  - [ ] `get_stock_brief`
  - [ ] `get_stock_debate`
  - [ ] `get_stock_signal_score`
  - [ ] `get_fno_trade_setup`
  - [ ] `get_morning_fno_brief`

## Package build

- [ ] `python -m build`
- [ ] inspect `dist/`
- [ ] verify wheel + sdist produced

## GitHub release

- [ ] set repo description
- [ ] add repo topics
- [ ] create release tag
- [ ] paste release body from `docs/GITHUB_LAUNCH_KIT.md`
- [ ] attach screenshots / GIFs

## PyPI

- [ ] upload with `twine`
- [ ] verify package page renders README correctly
- [ ] test `pip install finstack-mcp` in a clean environment

## Marketing assets

- [ ] post one stock brief GIF
- [ ] post one F&O setup screenshot
- [ ] post one agent battle visual
- [ ] mention proof/evaluation honestly
