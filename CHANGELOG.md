# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [SemVer](https://semver.org/).

## [Unreleased]

### Added
- **`session_status` and `portfolio` report `account_type`** (`"LIVE"`/`"PAPER"`)
  straight from IBKR's `isPaper` — the ground truth, independent of the cosmetic
  `IBKR_TRADING_MODE` label. A LIVE account also returns an explicit `warning`, so the
  agent can never mistake a real-money account for paper.

### Docs
- Troubleshoot `ERR_CONNECTION_REFUSED` (the gateway simply isn't running) distinctly
  from the "logged in but nothing happens" case.
- Clarify that `IBKR_TRADING_MODE` is a label, not the account selector.

## [0.3.0] - 2026-06-23

### Added
- **`trailing_stop`** — a stop that follows the price by a US$ amount or a %. CPAPI
  fields (`trailingAmt`/`trailingType`) and the `o10152` "Stop Variant" confirmation
  were validated live; `o10152` is now allow-listed so stop/stop-limit/trailing orders
  aren't blocked.

### Changed
- **Order placement survives a transient 503.** The gateway can answer an order POST
  with a 503 *after the order already landed*; placement now looks the order up by its
  client id (cOID) before retrying, so it never double-submits.
- **Position money fields are rounded to cents** (market price, average cost, market
  value, unrealized P&L); the fractional **quantity** stays exact.

## [0.2.2] - 2026-06-23

### Added
- **`get_quotes(symbols)`** — quote a whole watchlist in one snapshot call instead of
  one round-trip per symbol. Live-validated.
- **`wait_for_fill(order_id, timeout_seconds)`** — poll an order until it fills (or is
  cancelled/rejected), closing the confirm-the-fill loop so the agent doesn't have to
  orchestrate the retry. Bounded (timeout capped at 120s).

### Docs
- `CLAUDE.md`'s day-to-day tool list was stale (10 tools); now lists all 18.

## [0.2.1] - 2026-06-23

### Fixed
- **The value cap no longer blocks exits.** `MAX_ORDER_VALUE` is a spend limit, so it
  now applies to BUYS only — sells, `close_position`, and stop-losses larger than the
  limit are allowed, otherwise a position bigger than the cap could not be closed or
  protected.

## [0.2.0] - 2026-06-23

A loop-closing release: the agent can now confirm fills, set prices, attach risk, and
keep its own session warm. Every new order path was validated live.

### Added
- **`order_status(order_id)`** tool — confirm an order's state, filled quantity and
  average price after `buy`/`sell` (positions lag right after a trade).
- **LIMIT orders** — `buy`/`sell`/`preview_order` accept an optional `limit_price`
  (market by default; LIMIT requires `quantity`, since `cashQty` is market-only).
  Live-validated; IBKR's `o163` percentage-constraint confirmation is allow-listed so
  deliberate away-from-market limits aren't spuriously blocked.
- **`stop_order`** — STOP (stop-loss) and STOP-LIMIT orders. Live-validated; CPAPI
  carries a plain STOP's trigger in `price` (not `auxPrice`).
- **`bracket_order`** — an entry with attached take-profit + stop-loss exits (OCO via
  `parentId`/`ocaGroupId`). Guarded on the entry; live-validated structurally.
- **In-server keep-alive** — the MCP server now runs a background `/tickle` on its
  lifespan, so interactive use no longer needs the standalone `ibkr-keepalive`.
- GitHub issue/PR templates.

### Fixed
- **`whatif`/`preview_order` parsing** validated against a live response: money fields
  arrive as unit-suffixed strings (`"2.02 USD"`), warnings come from `warns`, and a
  fractional cash order reports available-funds impact (now exposed as
  `available_funds_before`/`after`) instead of the null margin blocks.

## [0.1.0] - 2026-06-22

First working release, validated live against a real IBKR account.

### Added
- **MCP server** (FastMCP) with 10 tools: `session_status`, `market_status`,
  `get_quote`, `account_summary`, `positions`, `buy`, `sell`, `close_position`,
  `cancel_order`, `open_orders`.
- **Fractional buys** by dollar amount (`cashQty`) and **fractional sells/closes**
  by share quantity (incl. `close_position`, which reads the exact position size).
- **Hexagonal** architecture (domain / adapters / safety / server) over the
  Interactive Brokers Client Portal API (REST).
- **Safety guards**: paper-first, dry-run by default, live lock, per-order value
  limit, regular trading hours (RTH) with **NYSE holidays**, and an allow-list for
  confirmation warnings (with an automatic *decline* when an unknown warning blocks
  the order).
- **Keep-alive** session loop with a reauth alert (`ibkr-keepalive`).
- **Healthcheck** for connection/account (`ibkr-healthcheck`).

[0.3.0]: https://github.com/pedrobraiti/mcp-ibkr-agent/releases/tag/v0.3.0
[0.2.2]: https://github.com/pedrobraiti/mcp-ibkr-agent/releases/tag/v0.2.2
[0.2.1]: https://github.com/pedrobraiti/mcp-ibkr-agent/releases/tag/v0.2.1
[0.2.0]: https://github.com/pedrobraiti/mcp-ibkr-agent/releases/tag/v0.2.0
[0.1.0]: https://github.com/pedrobraiti/mcp-ibkr-agent/releases/tag/v0.1.0
