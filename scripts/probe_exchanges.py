"""
READ-ONLY check of candidate exchanges before we build collectors.

For each one it prints: HTTP status, size, the shape of the reply,
and ONE sample ticker (preferably BTC/INR) - so collectors are built
on real field names, not guesses.

Run on your Mac:
    python3 -m scripts.probe_exchanges
Run just some:
    python3 -m scripts.probe_exchanges coindcx giottus
"""

import json
import sys

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (Scanbase market data check)", "Accept": "application/json"}

CANDIDATES = {
    "coindcx": "https://api.coindcx.com/exchange/ticker",
    "wazirx": "https://api.wazirx.com/sapi/v1/tickers/24hr",
    "giottus": "https://www.giottus.com/api/ticker",
    "zebpay": "https://www.zebapi.com/pro/v1/market/",
    "zebpay_v2": "https://sapi.zebpay.com/api/v2/market/allTickers",
    "bitbns": "https://bitbns.com/order/getTickerWithVolume/",
    "kucoin": "https://api.kucoin.com/api/v1/market/allTickers",
    "delta": "https://api.delta.exchange/v2/tickers?contract_types=spot",
}

WANTED_HINTS = ("BTCINR", "BTC-INR", "BTC_INR", "BTC/INR", "BTCUSDT", "BTC-USDT")


def looks_like_btc(item, key=""):
    blob = (key + " " + json.dumps(item, default=str)[:300]).upper().replace('"', "")
    return any(h in blob for h in WANTED_HINTS)


def find_list(data, path=""):
    """Finds the biggest list or dict-of-dicts inside the reply."""
    if isinstance(data, list):
        return path or "(top level list)", data
    if isinstance(data, dict):
        values = list(data.values())
        if len(values) > 20 and all(isinstance(v, dict) for v in values[:20]):
            return path or "(top level dict keyed by pair)", data
        best = (None, None)
        for k, v in data.items():
            if isinstance(v, (list, dict)):
                p, found = find_list(v, f"{path}.{k}" if path else k)
                if found is not None and (best[1] is None or len(found) > len(best[1])):
                    best = (p, found)
        return best
    return None, None


def sample(found):
    if isinstance(found, list):
        for item in found:
            if looks_like_btc(item):
                return item
        return found[0] if found else None
    for k, v in found.items():
        if looks_like_btc(v, k):
            return {"__pair_key__": k, **v} if isinstance(v, dict) else {k: v}
    k = next(iter(found), None)
    return {"__pair_key__": k, **found[k]} if k is not None else None


def main():
    wanted = sys.argv[1:] or list(CANDIDATES)
    for name in wanted:
        url = CANDIDATES.get(name)
        if not url:
            print(f"\n=== {name}: unknown name ===")
            continue
        print(f"\n=== {name} ===\n{url}")
        try:
            r = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        except Exception as e:
            print(f"FAILED: {type(e).__name__}: {e}")
            continue
        print(f"status {r.status_code}, {len(r.content):,} bytes")
        if r.status_code != 200:
            print(r.text[:200])
            continue
        try:
            data = r.json()
        except Exception:
            print("Not JSON:", r.text[:200])
            continue
        path, found = find_list(data)
        if found is None:
            print("Could not find a ticker list. Start of reply:")
            print(json.dumps(data, default=str)[:400])
            continue
        count = len(found)
        inr = sum(1 for x in (found if isinstance(found, list) else found.keys())
                  if "INR" in json.dumps(x, default=str).upper())
        print(f"list at: {path}  |  {count:,} items  |  ~{inr:,} mention INR")
        print("sample:")
        print(json.dumps(sample(found), indent=2, default=str)[:900])


if __name__ == "__main__":
    main()
