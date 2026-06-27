"""Per-venue capability contract.

So the generic ``GuardedBroker`` never branches on the venue, each adapter declares a
``Capabilities`` object and the **composition root** (each server's ``services.py``) reads
it to configure the guard — e.g. ``market_hours_model`` → ``require_market_open``,
``supports_shorting`` → ``allow_short``. The same safety layer then wraps Interactive
Brokers (RTH, no sell-by-value) and a crypto exchange (24/7, spot-only) with no
``if venue == "ibkr"`` anywhere. The remaining flags document the venue's contract for
the agent/skill. Keeping it a small frozen dataclass makes the contract explicit and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MarketHours(StrEnum):
    """When the venue accepts orders."""

    RTH_NYSE = "RTH_NYSE"  # US regular trading hours + NYSE holidays (Interactive Brokers)
    ALWAYS_OPEN = "ALWAYS_OPEN"  # 24/7 (crypto spot)


@dataclass(frozen=True)
class Capabilities:
    """What a venue's adapter supports, read by the generic safety layer."""

    supports_fractional: bool  # fractional sizes allowed (IBKR with permission; crypto: yes)
    supports_buy_by_value: bool  # buy by quote-currency amount (cashQty / cost)
    supports_sell_by_value: bool  # IBKR: False; crypto: False (sell by base quantity)
    supports_shorting: bool  # IBKR: depends; crypto spot: False
    market_hours_model: MarketHours
    quote_currency: str  # IBKR: "USD"; crypto: configurable (e.g. "USDT")

    @property
    def requires_market_open(self) -> bool:
        return self.market_hours_model is MarketHours.RTH_NYSE


# Interactive Brokers (US stocks, fractional via cashQty, RTH).
IBKR_CAPABILITIES = Capabilities(
    supports_fractional=True,
    supports_buy_by_value=True,
    supports_sell_by_value=False,
    supports_shorting=True,
    market_hours_model=MarketHours.RTH_NYSE,
    quote_currency="USD",
)


def crypto_capabilities(quote_currency: str, *, allow_margin: bool = False) -> Capabilities:
    """Capabilities for a spot crypto venue (24/7, buy-by-cost, no shorting unless margin)."""
    return Capabilities(
        supports_fractional=True,
        supports_buy_by_value=True,
        supports_sell_by_value=False,
        supports_shorting=allow_margin,
        market_hours_model=MarketHours.ALWAYS_OPEN,
        quote_currency=quote_currency.strip().upper(),
    )
