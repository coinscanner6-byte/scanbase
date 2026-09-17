"""
Where to look for a coin's logo, best source first.

Both sources are free and need no credit on the website:
  - Trust Wallet assets     (MIT licence)  - clean PNGs, found by blockchain
                                             and contract address
  - cryptocurrency-icons    (CC0, public domain) - found by symbol

Pure functions - no internet, no database - so they can be tested.
"""

from shared.keccak import checksum_address

TW = "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains"
ICONS = "https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color"

# Higher = better. A logo is only replaced by a better source.
SOURCE_RANK = {"coinscanner": 1, "icons": 2, "trustwallet": 3}

# Coin slug -> Trust Wallet folder for the coin's OWN blockchain logo.
NATIVE_CHAINS = {
    "bitcoin": "bitcoin", "ethereum": "ethereum", "binancecoin": "smartchain",
    "ripple": "ripple", "dogecoin": "doge", "cardano": "cardano",
    "solana": "solana", "tron": "tron", "avalanche-2": "avalanchec",
    "polkadot": "polkadot", "litecoin": "litecoin", "bitcoin-cash": "bitcoincash",
    "stellar": "stellar", "cosmos": "cosmos", "near": "near", "aptos": "aptos",
    "sui": "sui", "the-open-network": "ton", "hedera-hashgraph": "hedera",
    "algorand": "algorand", "tezos": "tezos", "filecoin": "filecoin",
    "ethereum-classic": "classic", "matic-network": "polygon",
    "polygon-ecosystem-token": "polygon", "fantom": "fantom",
    "internet-computer": "internet_computer", "zcash": "zcash", "dash": "dash",
    "iota": "iota", "theta-token": "theta", "vechain": "vechain", "eos": "eos",
    "neo": "neo", "ontology": "ontology", "harmony": "harmony", "kava": "kava",
    "zilliqa": "zilliqa", "waves": "waves", "osmosis": "osmosis",
    "sei-network": "sei", "kaspa": "kaspa", "monero": "monero",
    "celestia": "celestia", "injective-protocol": "native_injective",
    "mantle": "mantle", "cronos": "cronos", "icon": "icon", "qtum": "qtum",
    "nervos-network": "nervos", "ravencoin": "ravencoin", "digibyte": "digibyte",
    "decred": "decred", "nano": "nano", "terra-luna-2": "terrav2",
    "flow": "flow", "multiversx": "elrond", "elrond-erd-2": "elrond",
    "thorchain": "thorchain", "aeternity": "aeternity", "wax": "wax",
    "conflux-token": "conflux", "bitcoin-gold": "bitcoingold",
}

# Contract platform name (as stored in coin data) -> Trust Wallet folder.
# evm=True means the address must be written in checksummed form.
PLATFORMS = {
    "ethereum": ("ethereum", True),
    "binance-smart-chain": ("smartchain", True),
    "polygon-pos": ("polygon", True),
    "arbitrum-one": ("arbitrum", True),
    "optimistic-ethereum": ("optimism", True),
    "base": ("base", True),
    "avalanche": ("avalanchec", True),
    "fantom": ("fantom", True),
    "cronos": ("cronos", True),
    "linea": ("linea", True),
    "zksync": ("zksync", True),
    "mantle": ("mantle", True),
    "celo": ("celo", True),
    "solana": ("solana", False),
    "tron": ("tron", False),
    "sui": ("sui", False),
    "aptos": ("aptos", False),
    "the-open-network": ("ton", False),
}

# Platforms tried first when a token lives on several chains.
PLATFORM_ORDER = ["ethereum", "binance-smart-chain", "solana", "polygon-pos",
                  "arbitrum-one", "base", "tron", "avalanche", "optimistic-ethereum"]


def trustwallet_urls(slug=None, contracts=None):
    """Trust Wallet addresses to try for one listed coin, best first."""
    urls = []
    chain = NATIVE_CHAINS.get(slug or "")
    if chain:
        urls.append(f"{TW}/{chain}/info/logo.png")

    contracts = contracts if isinstance(contracts, dict) else {}
    ordered = sorted(contracts.items(),
                     key=lambda kv: PLATFORM_ORDER.index(kv[0])
                     if kv[0] in PLATFORM_ORDER else len(PLATFORM_ORDER))
    for platform, address in ordered:
        if platform not in PLATFORMS or not address:
            continue
        folder, evm = PLATFORMS[platform]
        addr = checksum_address(address) if evm else str(address).strip()
        if addr:
            urls.append(f"{TW}/{folder}/assets/{addr}/logo.png")
    return urls


def icons_url(symbol):
    return f"{ICONS}/{symbol.lower()}.png" if symbol and symbol.isalnum() else None


def candidates(symbol, slug=None, contracts=None):
    """[(source, url), ...] best first, for one symbol."""
    out = [("trustwallet", u) for u in trustwallet_urls(slug, contracts)]
    icon = icons_url(symbol)
    if icon:
        out.append(("icons", icon))
    return out
