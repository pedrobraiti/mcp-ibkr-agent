# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [SemVer](https://semver.org/).

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

[0.1.0]: https://github.com/pedrobraiti/mcp-ibkr-agent/releases/tag/v0.1.0
