# Security Policy

This project places **real orders** in real accounts — a brokerage (Interactive Brokers)
and crypto exchanges (spot, via CCXT). Treat it with the corresponding care.

## Secrets and credentials
- **Never** commit the `.env` file (it is already in `.gitignore`). It holds the
  account id, **crypto exchange API keys/secrets**, and sensitive configuration. The
  committed file is `.env.example` (keys only, no values).
- **IBKR** has no API keys in the code: authentication is a **manual login** to the
  Client Portal Gateway (a local session). Do not paste session tokens/cookies into issues.
- **Crypto** authenticates with a persistent exchange **API key + secret** (and optional
  passphrase) in `.env` — the most sensitive credentials in the repo. Scope the key to
  **spot trading only** (no withdrawals, no futures) and ideally IP-allowlist it; never commit it.
- Before opening an issue or PR, make sure no pasted log contains a real account
  id, balances, order identifiers, or API keys.

## Code safety defaults
- `paper`/dry-run by default; **per-venue** live gates — IBKR `live` requires
  `TRADING_ALLOW_LIVE=true`, crypto `live` requires `CRYPTO_ALLOW_LIVE=true` **and**
  `CRYPTO_TRADING_MODE=live` (arming one venue does not arm the other).
- Per-order value limit (`MAX_ORDER_VALUE`); IBKR adds a trading-hours (RTH) check (crypto is 24/7).
- Crypto is **spot-only** by default (`CRYPTO_ALLOW_MARGIN=false`).
- Unknown confirmation warnings **block** the order (they are not auto-confirmed).

## Reporting a vulnerability
Instead of opening a public issue, use GitHub
[Security Advisories](https://github.com/pedrobraiti/agentic-trading-mcp/security/advisories/new)
(private disclosure). Describe the impact and how to reproduce it. I'll respond as
soon as I can.
