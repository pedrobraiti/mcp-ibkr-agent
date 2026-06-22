# Contributing

Thanks for your interest! This is **trading plumbing** — changes that affect order
execution need extra care.

## Setup

```bash
python -m venv .venv
# Windows (PowerShell): & ".venv\Scripts\Activate.ps1"
# Linux/macOS:          source .venv/bin/activate
pip install -e ".[dev]"
```

## Before opening a PR

- `ruff check .` (lint) and `pytest -q` (tests) must pass — CI runs both.
- Cover any new logic with tests. The suite runs **offline** (respx/fakes), so it
  does not need the gateway or an account.
- **Never** include secrets, real account ids, or account data in code, tests, or
  logs.

## Style

- Commits follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`.
- Imperative mood; explain the **why** when it isn't obvious.

## Architecture

Hexagonal (ports & adapters): swapping/extending the broker or the data source
lives in `adapters/` + `server/services.py`; the domain (`domain/`) does not know
about IBKR. See the [README](README.md) for the overview and
[DECISIONS.md](DECISIONS.md) for the rationale.
