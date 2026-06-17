"""Region-agnostic market data provider interface.

Add a market = add a provider. The rest of the app never knows the source.
"""
from __future__ import annotations

from typing import Protocol

import pandas as pd


class MarketDataProvider(Protocol):
    """Every region/source implements this. Frontend stays dumb."""

    def bars(
        self, symbol: str, start: str | None, end: str | None, interval: str
    ) -> pd.DataFrame:
        """Return OHLCV bars. Index = DatetimeIndex, cols: open/high/low/close/volume."""
        ...
