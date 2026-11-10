"""Small value objects returned by the convenience helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TokenBalance:
    """The balance of one token on an address."""

    token_standard: str
    name: str
    symbol: str
    decimals: int
    raw_balance: int

    @property
    def balance(self) -> Decimal:
        """The balance in whole tokens, exact to the token's number of decimals."""
        return Decimal(self.raw_balance).scaleb(-self.decimals)

    def __str__(self) -> str:
        return f"{self.balance:f} {self.symbol}"
