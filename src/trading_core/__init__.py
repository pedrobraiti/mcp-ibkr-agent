"""Shared execution core for the trading MCP servers.

Venue-agnostic domain models, ports, the generic ``GuardedBroker`` safety layer, the
trade journal and the per-venue capability contract. Both the IBKR (``ibkr_agent``) and
the crypto (``crypto_agent``) servers are thin adapters over this core.
"""
