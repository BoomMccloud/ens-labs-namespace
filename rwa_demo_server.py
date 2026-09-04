#!/usr/bin/env python3
"""Local static server plus narrow, cached market-data adapters for the RWA demo."""

from __future__ import annotations

import html
import json
import os
import re
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
CACHE_TTL_SECONDS = 30
SEC_CACHE_TTL_SECONDS = 6 * 60 * 60
USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "ENS-RWA-Demo/1.1 contact=local-demo@example.com",
)
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
COINGECKO_SEARCH_URL = "https://api.coingecko.com/api/v3/search"
DEXSCREENER_SEARCH_URL = "https://api.dexscreener.com/latest/dex/search"
SEARCH_RESULT_LIMIT = 6

STOCKS = {
    "NVDA": {"name": "NVIDIA Corporation", "exchange": "NASDAQ"},
    "AAPL": {"name": "Apple Inc.", "exchange": "NASDAQ"},
    "MSFT": {"name": "Microsoft Corporation", "exchange": "NASDAQ"},
    "TSLA": {"name": "Tesla, Inc.", "exchange": "NASDAQ"},
    "AMZN": {"name": "Amazon.com, Inc.", "exchange": "NASDAQ"},
    "META": {"name": "Meta Platforms, Inc.", "exchange": "NASDAQ"},
}

COINS = {
    "BTC": {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC"},
    "BITCOIN": {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC"},
    "ETH": {"id": "ethereum", "name": "Ethereum", "symbol": "ETH"},
    "ETHEREUM": {"id": "ethereum", "name": "Ethereum", "symbol": "ETH"},
    "SOL": {"id": "solana", "name": "Solana", "symbol": "SOL"},
    "SOLANA": {"id": "solana", "name": "Solana", "symbol": "SOL"},
    "DOGE": {"id": "dogecoin", "name": "Dogecoin", "symbol": "DOGE"},
    "DOGECOIN": {"id": "dogecoin", "name": "Dogecoin", "symbol": "DOGE"},
    "LINK": {"id": "chainlink", "name": "Chainlink", "symbol": "LINK"},
    "CHAINLINK": {"id": "chainlink", "name": "Chainlink", "symbol": "LINK"},
}

_cache: dict[str, tuple[float, dict]] = {}
_sec_stock_cache: tuple[float, list[dict]] | None = None

GOOGLE_EXCHANGES = {
    "Nasdaq": "NASDAQ",
    "NYSE": "NYSE",
    "NYSE American": "NYSEAMERICAN",
    "NYSE Arca": "NYSEARCA",
    "Cboe BZX": "BATS",
    "OTC": "OTCMKTS",
}


def _cached(key: str) -> dict | None:
    entry = _cache.get(key)
    if entry and time.time() - entry[0] < CACHE_TTL_SECONDS:
        return {**entry[1], "cached": True}
    return None


def _store(key: str, value: dict) -> dict:
    _cache[key] = (time.time(), value)
    return value


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json"})
    with urlopen(request, timeout=8) as response:
        return response.read().decode("utf-8")


def _normalize_sec_payload(payload: dict) -> list[dict]:
    fields = payload.get("fields")
    data = payload.get("data")
    if not isinstance(fields, list) or not isinstance(data, list):
        raise ValueError("SEC ticker dataset malformed")
    positions = {field: index for index, field in enumerate(fields)}
    required = {"cik", "name", "ticker", "exchange"}
    if not required.issubset(positions):
        raise ValueError("SEC ticker fields missing")
    stocks = []
    for row in data:
        if not isinstance(row, list) or len(row) < len(fields):
            continue
        try:
            stock = {
                "cik": int(row[positions["cik"]]),
                "name": str(row[positions["name"]]).strip(),
                "symbol": str(row[positions["ticker"]]).strip().upper(),
                "exchange": str(row[positions["exchange"]]).strip(),
            }
        except (TypeError, ValueError):
            continue
        if stock["cik"] > 0 and stock["name"] and stock["symbol"] and stock["exchange"]:
            stocks.append(stock)
    if not stocks:
        raise ValueError("SEC ticker dataset empty")
    return stocks


def _search_text(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _find_sec_stock(query: str, stocks: list[dict]) -> dict | None:
    normalized = query.strip().upper()
    for stock in stocks:
        if stock["symbol"] == normalized:
            return stock
    words = _search_text(query)
    if len(words) < 2:
        return None
    exact = next((stock for stock in stocks if _search_text(stock["name"]) == words), None)
    if exact:
        return exact
    prefix = next((stock for stock in stocks if _search_text(stock["name"]).startswith(words)), None)
    if prefix:
        return prefix
    tokens = words.split()
    return next(
        (stock for stock in stocks if all(token in _search_text(stock["name"]).split() for token in tokens)),
        None,
    )


def _search_sec_stocks(query: str, stocks: list[dict], limit: int = SEARCH_RESULT_LIMIT) -> list[dict]:
    symbol_query = query.strip().upper()
    name_query = _search_text(query)
    if not symbol_query:
        return []
    candidates = []
    for stock in stocks:
        exact = stock["symbol"] == symbol_query
        symbol_prefix = stock["symbol"].startswith(symbol_query)
        name_prefix = len(name_query) > 1 and _search_text(stock["name"]).startswith(name_query)
        if not (exact or symbol_prefix or name_prefix):
            continue
        candidates.append({
            **stock,
            "exact": exact,
            "match": "Exact ticker" if exact else "Ticker prefix" if symbol_prefix else "Company name",
        })
    candidates.sort(key=lambda stock: (
        not stock["exact"],
        not stock["symbol"].startswith(symbol_query),
        len(stock["symbol"]),
        stock["symbol"],
    ))
    return candidates[: max(1, min(limit, SEARCH_RESULT_LIMIT))]


def _load_sec_stocks() -> list[dict]:
    global _sec_stock_cache
    if _sec_stock_cache and time.time() - _sec_stock_cache[0] < SEC_CACHE_TTL_SECONDS:
        return _sec_stock_cache[1]
    stocks = _normalize_sec_payload(json.loads(_fetch_text(SEC_TICKERS_URL)))
    _sec_stock_cache = (time.time(), stocks)
    return stocks


def _local_stock(query: str) -> tuple[str, dict] | None:
    normalized = query.strip().upper()
    if normalized in STOCKS:
        return normalized, STOCKS[normalized]
    lowered = query.strip().lower()
    for symbol, stock in STOCKS.items():
        if lowered in {stock["name"].lower(), stock["name"].split()[0].lower()}:
            return symbol, stock
    return None


def _resolve_stock_identity(query: str) -> tuple[dict, bool]:
    try:
        if stock := _find_sec_stock(query, _load_sec_stocks()):
            return stock, True
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        pass
    local = _local_stock(query)
    if not local:
        raise LookupError("Stock identity not found")
    symbol, stock = local
    return {
        "cik": None,
        "name": stock["name"],
        "symbol": symbol,
        "exchange": stock["exchange"].title(),
    }, False


def _fetch_stock_quote(symbol: str, exchange: str) -> tuple[float, str | None]:
    google_exchange = GOOGLE_EXCHANGES.get(exchange, exchange.upper() if exchange.upper() in {"NASDAQ", "NYSE"} else None)
    if not google_exchange:
        raise ValueError("Quote exchange unsupported")
    url = f"https://www.google.com/finance/quote/{quote(symbol)}:{quote(google_exchange)}"
    page = _fetch_text(url)
    price_match = re.search(r'YMlKec fxKbKc"[^>]*>([^<]+)', page)
    title_match = re.search(r"<title>([^<]+)", page)
    if not price_match:
        raise ValueError("Quote marker missing")
    raw_price = html.unescape(price_match.group(1)).replace(",", "").strip()
    numeric = re.search(r"-?\d+(?:\.\d+)?", raw_price)
    if not numeric:
        raise ValueError("Quote value missing")
    return float(numeric.group(0)), html.unescape(title_match.group(1)) if title_match else None


def lookup_stock(query: str) -> dict:
    stock, identity_live = _resolve_stock_identity(query)
    symbol = stock["symbol"]
    cache_key = f"stock:{symbol}"
    if cached := _cached(cache_key):
        return cached
    value = {
        "assetType": "stock",
        "symbol": symbol,
        "name": stock["name"],
        "exchange": stock["exchange"],
        "cik": stock["cik"],
        "identityProvider": "SEC" if identity_live else "Demo fallback",
        "price": None,
        "currency": "USD",
        "provider": "SEC" if identity_live else "Demo fallback",
        "live": identity_live,
        "quoteLive": False,
        "cached": False,
        "asOf": int(time.time()),
        "sourceTitle": None,
    }
    try:
        price, source_title = _fetch_stock_quote(symbol, stock["exchange"])
        value.update({
            "price": price,
            "provider": "Google Finance",
            "quoteLive": True,
            "sourceTitle": source_title,
        })
    except (HTTPError, URLError, TimeoutError, ValueError):
        pass
    return _store(cache_key, value)


def search_stocks(query: str) -> dict:
    cache_key = f"search:stock:{query.strip().lower()}"
    if cached := _cached(cache_key):
        return cached
    results = _search_sec_stocks(query, _load_sec_stocks())
    if not results:
        raise LookupError("No SEC stock matches")
    value = {
        "assetType": "stock",
        "query": query.strip(),
        "provider": "SEC",
        "verified": True,
        "results": results,
        "cached": False,
    }
    return _store(cache_key, value)


def _number(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _normalize_coingecko_search(payload: dict, query: str, limit: int = SEARCH_RESULT_LIMIT) -> list[dict]:
    coins = payload.get("coins")
    if not isinstance(coins, list):
        raise ValueError("CoinGecko search malformed")
    normalized = query.strip().upper()
    results = []
    for coin in coins:
        if not isinstance(coin, dict) or not coin.get("id") or not coin.get("name") or not coin.get("symbol"):
            continue
        symbol = str(coin["symbol"]).upper()
        results.append({
            "id": str(coin["id"]),
            "name": str(coin["name"]),
            "symbol": symbol,
            "rank": coin.get("market_cap_rank") if isinstance(coin.get("market_cap_rank"), int) else None,
            "chain": "Catalog",
            "address": None,
            "price": None,
            "marketCap": None,
            "liquidity": None,
            "change24h": None,
            "exact": symbol == normalized,
            "verified": False,
            "source": "CoinGecko",
        })
        if len(results) >= max(1, min(limit, SEARCH_RESULT_LIMIT)):
            break
    return results


def _normalize_dex_search(payload: dict, query: str, limit: int = SEARCH_RESULT_LIMIT) -> list[dict]:
    pairs = payload.get("pairs")
    if not isinstance(pairs, list):
        raise ValueError("DexScreener search malformed")
    normalized = query.strip().upper()
    ordered = sorted(
        (pair for pair in pairs if isinstance(pair, dict)),
        key=lambda pair: _number((pair.get("liquidity") or {}).get("usd")) or 0,
        reverse=True,
    )
    results = []
    seen = set()
    for pair in ordered:
        token = pair.get("baseToken")
        if not isinstance(token, dict):
            continue
        quote_token = pair.get("quoteToken") if isinstance(pair.get("quoteToken"), dict) else {}
        address = str(token.get("address") or "").strip()
        symbol = str(token.get("symbol") or "").strip().upper()
        name = str(token.get("name") or "").strip()
        chain = str(pair.get("chainId") or "Unknown").strip()
        if not address or not symbol or not name:
            continue
        key = (chain.lower(), address.lower())
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "id": f"{chain}:{address}",
            "name": name,
            "symbol": symbol,
            "rank": None,
            "chain": chain,
            "address": address,
            "dexId": str(pair.get("dexId") or "Unknown").strip(),
            "pairAddress": str(pair.get("pairAddress") or "").strip(),
            "baseToken": {"address": address, "name": name, "symbol": symbol},
            "quoteToken": {
                "address": str(quote_token.get("address") or "").strip(),
                "name": str(quote_token.get("name") or "Unknown quote").strip(),
                "symbol": str(quote_token.get("symbol") or "?").strip().upper(),
            },
            "price": _number(pair.get("priceUsd")),
            "marketCap": _number(pair.get("marketCap") or pair.get("fdv")),
            "liquidity": _number((pair.get("liquidity") or {}).get("usd")),
            "change24h": _number((pair.get("priceChange") or {}).get("h24")),
            "exact": symbol == normalized,
            "verified": False,
            "source": "DexScreener",
        })
        if len(results) >= max(1, min(limit, SEARCH_RESULT_LIMIT)):
            break
    return results


def search_crypto(query: str) -> dict:
    normalized = query.strip().upper()
    cache_key = f"search:crypto:{normalized}"
    if cached := _cached(cache_key):
        return cached
    payload = json.loads(_fetch_text(f"{DEXSCREENER_SEARCH_URL}?q={quote(query.strip())}"))
    results = _normalize_dex_search(payload, query)
    provider = "DexScreener"
    identities = set()
    for pair in payload.get("pairs") or []:
        if not isinstance(pair, dict) or not isinstance(pair.get("baseToken"), dict):
            continue
        chain = str(pair.get("chainId") or "").lower()
        address = str(pair["baseToken"].get("address") or "").lower()
        if chain and address:
            identities.add((chain, address))
    total = len(identities)
    if not results:
        raise LookupError("No crypto matches")
    value = {
        "assetType": "crypto",
        "query": query.strip(),
        "provider": provider,
        "verified": False,
        "total": max(total, len(results)),
        "results": results,
        "cached": False,
    }
    return _store(cache_key, value)


def lookup_crypto(query: str) -> dict:
    coin = COINS.get(query.strip().upper())
    if not coin:
        raise LookupError("Unsupported demo crypto asset")
    cache_key = f"crypto:{coin['id']}"
    if cached := _cached(cache_key):
        return cached
    coin_id = quote(coin["id"])
    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        f"?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_last_updated_at=true"
    )
    payload = json.loads(_fetch_text(url))
    quote_data = payload.get(coin["id"])
    if not quote_data or not isinstance(quote_data.get("usd"), (int, float)):
        raise ValueError("CoinGecko quote missing")
    value = {
        "assetType": "crypto",
        "symbol": coin["symbol"],
        "name": coin["name"],
        "price": float(quote_data["usd"]),
        "change24h": quote_data.get("usd_24h_change"),
        "currency": "USD",
        "provider": "CoinGecko",
        "live": True,
        "cached": False,
        "asOf": quote_data.get("last_updated_at") or int(time.time()),
    }
    return _store(cache_key, value)


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/lookup", "/api/search"}:
            return super().do_GET()
        params = parse_qs(parsed.query)
        asset_type = params.get("type", [""])[0].strip().lower()
        query = params.get("q", [""])[0].strip()
        if asset_type not in {"stock", "crypto"} or not query or len(query) > 80:
            return self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_request", "message": "Use type=stock|crypto and a short q value."})
        try:
            if parsed.path == "/api/search":
                result = search_stocks(query) if asset_type == "stock" else search_crypto(query)
            else:
                result = lookup_stock(query) if asset_type == "stock" else lookup_crypto(query)
            return self._json(HTTPStatus.OK, result)
        except LookupError as error:
            return self._json(HTTPStatus.NOT_FOUND, {"error": "not_found", "message": str(error)})
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return self._json(HTTPStatus.BAD_GATEWAY, {"error": "provider_unavailable", "message": "Live provider unavailable. Use the demo fallback."})

    def log_message(self, format: str, *args) -> None:
        if self.path.startswith("/api/"):
            super().log_message(format, *args)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), DemoHandler)
    print(f"RWA demo available at http://127.0.0.1:{port}/rwa-ens-identity-demo.html", flush=True)
    server.serve_forever()
