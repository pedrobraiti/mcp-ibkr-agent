"""Crypto execution MCP server — a thin CCXT adapter over the shared ``trading_core``.

Authenticates with a persistent exchange API key (no gateway, no browser login, no
tickle), trades 24/7, and reuses the same domain models, safety guard and trade journal
as the IBKR server. Spot-only by default.
"""
