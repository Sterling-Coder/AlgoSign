"""The radar universe per region. Edit here to change what's scanned.

Regions the app switches between: IN (India), US, WORLD (ex-US countries +
global assets). ALL = everything.
"""
from __future__ import annotations

INDIA: list[str] = [
    "NIFTYBEES.NS", "BANKBEES.NS", "JUNIORBEES.NS", "ITBEES.NS", "GOLDBEES.NS",
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
]

US: list[str] = [
    "SPY", "QQQ", "VTI", "IWM", "DIA",
    "XLK", "XLF", "XLE", "XLV", "XLI",
    "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC",
]

WORLD: list[str] = [
    "VXUS", "EFA", "VWO", "INDA", "FXI", "EWJ", "EWG", "EWU", "EWZ",
    "GLD", "SLV", "TLT", "USO", "BITO",
]

_REGIONS = {"IN": INDIA, "US": US, "WORLD": WORLD}


def basket(region: str) -> list[str]:
    r = region.upper()
    if r == "ALL":
        out: list[str] = []
        for v in _REGIONS.values():
            out.extend(v)
        return out
    return _REGIONS.get(r, [])
