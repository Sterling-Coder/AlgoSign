"""Plain-English names so calls read like advice, not ticker soup."""

NAMES: dict[str, str] = {
    # US broad
    "SPY": "US 500 (S&P)", "QQQ": "US Tech (Nasdaq 100)", "VTI": "US Total Market",
    "IWM": "US Small Caps", "DIA": "US Dow 30",
    # US sectors
    "XLK": "US Tech", "XLF": "US Financials", "XLE": "US Energy",
    "XLV": "US Healthcare", "XLI": "US Industrials", "XLY": "US Consumer (disc.)",
    "XLP": "US Consumer (staples)", "XLU": "US Utilities", "XLB": "US Materials",
    "XLRE": "US Real Estate", "XLC": "US Communications",
    # world / country
    "VXUS": "World ex-US", "EFA": "Developed ex-US", "VWO": "Emerging Markets",
    "INDA": "India", "FXI": "China", "EWJ": "Japan", "EWG": "Germany",
    "EWU": "UK", "EWZ": "Brazil",
    # assets
    "GLD": "Gold", "SLV": "Silver", "TLT": "US Long Bonds", "USO": "Crude Oil",
    "BITO": "Bitcoin (futures)",
    # gap-radar underlyings
    "TSLA": "Tesla", "NVDA": "Nvidia", "MU": "Micron", "CRCL": "Circle",
    "SNDK": "SanDisk",
    # India
    "NIFTYBEES.NS": "Nifty 50", "BANKBEES.NS": "Bank Nifty",
    "JUNIORBEES.NS": "Nifty Next 50", "ITBEES.NS": "Nifty IT",
    "GOLDBEES.NS": "Gold (India)", "RELIANCE.NS": "Reliance",
    "TCS.NS": "TCS", "INFY.NS": "Infosys", "HDFCBANK.NS": "HDFC Bank",
    "ICICIBANK.NS": "ICICI Bank",
}


# Live names harvested from the screener at runtime (lower priority than the
# curated NAMES above, which give plain-English labels for indices/ETFs).
_LIVE: dict[str, str] = {}


def register(mapping: dict[str, str]) -> None:
    """Merge live symbol->name pairs (e.g. from the universe screener)."""
    for sym, nm in mapping.items():
        if sym and nm:
            _LIVE[sym.upper()] = nm


def name(symbol: str) -> str:
    key = symbol.upper()
    return NAMES.get(key) or _LIVE.get(key) or symbol
