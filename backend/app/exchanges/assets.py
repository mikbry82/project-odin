from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedAsset:
    canonical_id: str
    display_symbol: str


DISPLAY_ALIASES = {
    "XBT": "BTC",
    "XXBT": "BTC",
    "XETH": "ETH",
    "ZEUR": "EUR",
    "ZUSD": "USD",
    "ZGBP": "GBP",
}


def normalize_asset(asset_id: str, display_hint: str | None = None) -> NormalizedAsset:
    canonical = asset_id
    display = display_hint or DISPLAY_ALIASES.get(canonical, canonical)
    display = DISPLAY_ALIASES.get(display, display)
    return NormalizedAsset(canonical_id=canonical, display_symbol=display)
