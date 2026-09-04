#!/usr/bin/env bash
set -euo pipefail

base_url="${MARKET_HOOK_BASE_URL:-http://127.0.0.1:8765}"
demo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if rg -q 'benefit-strip|Recognizable names|Verify before acting|One shared identity' "${demo_dir}/rwa-ens-identity-demo.html"; then
  echo "slide 8 still contains the removed benefit strip" >&2
  exit 1
fi

if rg -q 'stockFallbackResults|provider:.Fallback.,results:fallback' "${demo_dir}/rwa-ens-identity-demo.html"; then
  echo "stock search still contains a hard-coded result fallback" >&2
  exit 1
fi

if rg -q 'class="match-type"|Exact ticker|Ticker prefix' "${demo_dir}/rwa-ens-identity-demo.html"; then
  echo "result rows still contain a right-side match label" >&2
  exit 1
fi

node -e '
const source = require("fs").readFileSync(process.argv[1], "utf8");
const rule = selector => source.match(new RegExp(selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s*\\{([^}]*)\\}", "s"))?.[1] || "";
const px = (css, property) => Number(css.match(new RegExp(property + "\\s*:\\s*([0-9.]+)px"))?.[1]);
const fontPx = css => Number((css.match(/font-size\s*:\s*([0-9.]+)px/) || css.match(/font\s*:[^;]*?([0-9.]+)px/))?.[1]);
const name = rule(".stock-copy strong");
const meta = rule(".stock-copy small");
const darkName = rule(".dark-device .stock-copy strong");
const darkMeta = rule(".dark-device .stock-copy small");
const darkResolution = rule(".dark-device .resolve-line");
if (px(name, "font-size") < 16 || px(meta, "font-size") < 12) process.exit(1);
if (!/color:\s*#515154/.test(meta)) process.exit(1);
if (!/color:\s*#f5f5f7/.test(darkName)) process.exit(1);
if (!/color:\s*#b7b7bd/.test(darkMeta) || !/color:\s*#a1a1a6/.test(darkResolution)) process.exit(1);
const readableType = [
  ".live-label", ".eyebrow", ".device-bar", ".search button", ".pill", ".catalog-head", ".stock-copy small", ".quick-picks button", ".resolve-line",
  ".pair-symbols span", ".crypto-copy .pair-names", ".crypto-copy .pair-addresses", ".chain span", ".chain code", ".attestation-summary-copy a",
  ".namespace-type", ".namespace-copy code", ".stealth-copy span", ".namespace-relation", ".tree-level span", ".tree-level code", ".tree-note",
  ".menu-label", ".menu-copy strong", ".menu-copy span", ".menu-copy code", ".comparison-label", ".comparison-card code", ".comparison-card li",
  ".asset-row span", ".verification-copy small", ".verification-copy strong", ".verification-copy span",
  ".verification-card a", ".order-details div", ".buy", ".fine", ".success-kicker", ".success-name", ".success-route div", ".success-checks li", ".counter", ".hint"
];
if (readableType.some(selector => fontPx(rule(selector)) < 14)) process.exit(1);
if (!["pair-symbols", "pair-names", "pair-addresses", "baseToken", "quoteToken", "pairAddress"].every(value => source.includes(value))) process.exit(1);
const scenes = [...source.matchAll(/<section class="scene[^>]*data-scene="(\d+)"/g)].map(match => Number(match[1]));
const dots = [...source.matchAll(/class="dot(?: active)?" data-step="(\d+)"/g)].map(match => Number(match[1]));
if (JSON.stringify(scenes) !== JSON.stringify([0, 1, 2, 3, 4, 5, 6, 7]) || JSON.stringify(dots) !== JSON.stringify([0, 1, 2, 3, 4, 5, 6, 7])) process.exit(1);
const buyingSlide = source.indexOf("04 · Buying with ENS");
const namespaceSlide = source.indexOf("05 · What is a namespace?");
if (buyingSlide < 0 || namespaceSlide < buyingSlide) process.exit(1);
if (!["Same name.<br><span class=\"blue\">Buy anywhere.</span>", "Use the same verified asset name wherever ENS is integrated."].every(value => source.includes(value))) process.exit(1);
if (source.includes("One name.<br><span class=\"blue\">Buy anywhere.</span>")) process.exit(1);
if (["04 · Namespace", "05 · Confidence", "Know what you buy.", "Right issuer. Right chain. Right contract.", "ENS verified*"].some(value => source.includes(value))) process.exit(1);
if (source.includes("So people hunt") || source.includes("benji.franklintempleton.eth")) process.exit(1);
if (!["01 · Traditional markets", "One ticker.<br><span class=\"blue\">One company.</span>", "Listed tickers are unique."].every(value => source.includes(value))) process.exit(1);
if (["01 · Stocks", "Stocks are simple.", "One ticker resolves to one listed company."].some(value => source.includes(value))) process.exit(1);
if (!["02 · Crypto markets", "One ticker.<br><span class=\"blue\">Many tokens.</span>", "Token tickers are not unique."].every(value => source.includes(value))) process.exit(1);
if (["02 · Tokens", "Same ticker. Different assets. Different contracts."].some(value => source.includes(value))) process.exit(1);
if (!source.includes("03 · Crypto markets with ENS") || !source.includes("One asset.<br><span class=\"blue\">One ENS name.</span>")) process.exit(1);
if (["03 · ENS", "ENS names:<br>", "Every chain."].some(value => source.includes(value))) process.exit(1);
if (!source.includes("<p class=\"sub\">ENS names are unique and issuer-controlled.</p>") || source.includes("<p class=\"sub ens-name\">")) process.exit(1);
if (!["05 · What is a namespace?", "Names organized<br><span class=\"blue\">under one trusted root.</span>", "A namespace gives every participant and asset a unique, predictable place under", "Names become more specific as you move left."].every(value => source.includes(value))) process.exit(1);
if (!["06 · Namespace design", "A good namespace<br><span class=\"blue\">works like a clear menu.</span>", "Each level narrows the choice: assets → BENJI → policies → redemption. New facets can be added without changing the asset’s identity.", "namespace-menu", "Assets", "BENJI", "Policies", "Redemption", "redemption.policies.benji.assets.franklintempleton.eth"].every(value => source.includes(value))) process.exit(1);
if (!["07 · Connected by names", "A connected namespace<br><span class=\"blue\">works like a map.</span>", "While a name identifies an entity, asset, or account, records explain how they are related."].every(value => source.includes(value))) process.exit(1);
if (["Every relationship<br><span class=\"blue\">becomes clear.</span>", "Each party can verify exactly who and what it is interacting with."].some(value => source.includes(value))) process.exit(1);
if (!["08 · Why it matters", "A shared namespace<br><span class=\"blue\">makes every interaction safer.</span>", "Find the right entity, asset, account, or policy. Verify the relationship. Then act.", "Without a namespace", "With a namespace"].every(value => source.includes(value))) process.exit(1);
if (["benefit-strip", "Recognizable names", "Verify before acting", "One shared identity"].some(value => source.includes(value))) process.exit(1);
if (["Identify first.<br><span class=\"blue\">Interact safely.</span>", "Find the intended entity, asset, or account without copying unknown addresses."].some(value => source.includes(value))) process.exit(1);
if (!["namespace-tree", "namespace-menu", "namespace-flow", "safety-comparison"].every(value => source.includes(value))) process.exit(1);
if (["namespace-categories", "category-card", "A place<br><span class=\"blue\">for everything.</span>", "Entities identify organizations. Assets identify what they issue. Accounts identify who holds or receives them.", "05 · Namespace design", "Names connect<br><span class=\"blue\">the ecosystem.</span>", "Three names.<br><span class=\"blue\">One system.</span>", "An entity issues the asset. An account holds it."].some(value => source.includes(value))) process.exit(1);
if (/beiji/i.test(source) || (source.match(/benji\.assets\.franklintempleton\.eth/g) || []).length < 3) process.exit(1);
if (!["namespace-flow", "Entities", "Assets", "Accounts", "ft-digital-assets.entities.franklintempleton.eth", "alice.accounts.franklintempleton.eth", "issues", "held by", "stealth-visual", "Stealth addresses", "Fresh address every transfer"].every(value => source.includes(value))) process.exit(1);
if (px(rule(".namespace-type"), "font-size") < 12 || px(rule(".namespace-copy strong"), "font-size") < 20 || px(rule(".namespace-copy code"), "font-size") < 13) process.exit(1);
if (px(rule(".stealth-copy strong"), "font-size") < 15 || px(rule(".stealth-copy span"), "font-size") < 13) process.exit(1);
if (!source.includes("class=\"verification-card\"") || !source.includes("Third-party verification")) process.exit(1);
if (!["Purchase simulated", "id=\"successAmount\"", "id=\"successChain\"", "id=\"successContract\"", "Asset identity matched", "Issuer attestation valid", "Correct chain contract selected", "id=\"continueButton\""].every(value => source.includes(value))) process.exit(1);
if (["Identity confirmed.", "Simulated purchase complete.", "Replay demo", "id=\"resetButton\""].some(value => source.includes(value))) process.exit(1);
if (!/continueButton[\s\S]*show\(4\)/.test(source)) process.exit(1);
if (!source.includes("class=\"attestation-summary\"") || !source.includes("class=\"verified-badge\"") || !source.includes("<strong>Attestation valid*</strong>") || !source.includes("View proof ↗")) process.exit(1);
if (["✓ Resolved", "Issuer verified*", "✓ Issuer + custodian attested*", "<small>Fee</small>", "<small>6 months</small>", "id=\"attestationToggle\""].some(value => source.includes(value))) process.exit(1);
if (!/href="https:\/\/easscan\.org\/" target="_blank" rel="noopener noreferrer"/.test(source)) process.exit(1);
if (source.includes("<span>Attestation</span><b>Valid*</b>")) process.exit(1);
' "${demo_dir}/rwa-ens-identity-demo.html"

if [[ ! -f "${demo_dir}/vercel.json" || ! -f "${demo_dir}/api/lookup.py" || ! -f "${demo_dir}/api/search.py" ]]; then
  echo "Vercel deployment entry points are missing" >&2
  exit 1
fi

if ! rg -q '^\*\*Why:\*\*' "${demo_dir}/README.md" || ! rg -q '^\*\*Guarded by:\*\* `test-market-hook\.sh`' "${demo_dir}/README.md"; then
  echo "the Vercel adapter constraint is not documented" >&2
  exit 1
fi

DEMO_DIR="${demo_dir}" python3 -c '
import importlib
import json
import os
from pathlib import Path

root = Path(os.environ["DEMO_DIR"])
config = json.loads((root / "vercel.json").read_text())
assert {"source": "/", "destination": "/rwa-ens-identity-demo.html"} in config.get("rewrites", [])

lookup = importlib.import_module("api.lookup")
search = importlib.import_module("api.search")
from http.server import BaseHTTPRequestHandler
assert issubclass(lookup.handler, BaseHTTPRequestHandler)
assert issubclass(search.handler, BaseHTTPRequestHandler)
assert lookup.handler.__module__ == "api.lookup"
assert search.handler.__module__ == "api.search"
'

stock_json="$(curl -fsS "${base_url}/api/lookup?type=stock&q=MSFT")"
sec_stock_json="$(curl -fsS "${base_url}/api/lookup?type=stock&q=IBM")"
crypto_json="$(curl -fsS "${base_url}/api/lookup?type=crypto&q=bitcoin")"
stock_search_json="$(curl -fsS "${base_url}/api/search?type=stock&q=C")"
arbitrary_stock_search_json="$(curl -fsS "${base_url}/api/search?type=stock&q=GOOG")"
btc_search_json="$(curl -fsS "${base_url}/api/search?type=crypto&q=BTC")"
boner_search_json="$(curl -fsS "${base_url}/api/search?type=crypto&q=BONER")"

node -e '
const [stock, secStock, crypto, stockSearch, arbitraryStockSearch, btcSearch, bonerSearch] = process.argv.slice(1).map(JSON.parse);
if (stock.provider !== "Google Finance" || stock.assetType !== "stock" || !(stock.price > 0) || stock.currency !== "USD" || stock.live !== true) process.exit(1);
if (stock.identityProvider !== "SEC" || !(stock.cik > 0)) process.exit(1);
if (secStock.symbol !== "IBM" || secStock.identityProvider !== "SEC" || !(secStock.cik > 0) || !secStock.name.toUpperCase().includes("INTERNATIONAL BUSINESS MACHINES")) process.exit(1);
if (crypto.provider !== "CoinGecko" || crypto.assetType !== "crypto" || !(crypto.price > 0) || crypto.currency !== "USD" || crypto.live !== true) process.exit(1);
const exactStocks = stockSearch.results.filter(result => result.exact === true);
if (stockSearch.provider !== "SEC" || stockSearch.results.length < 4 || exactStocks.length !== 1 || exactStocks[0].symbol !== "C" || !exactStocks[0].name.toUpperCase().includes("CITIGROUP")) process.exit(1);
if (stockSearch.results.some(result => !result.symbol.startsWith("C"))) process.exit(1);
const arbitraryExact = arbitraryStockSearch.results.filter(result => result.exact === true);
if (arbitraryStockSearch.provider !== "SEC" || arbitraryExact.length !== 1 || arbitraryExact[0].symbol !== "GOOG" || !arbitraryExact[0].name.toUpperCase().includes("ALPHABET")) process.exit(1);
if (btcSearch.results.length < 4 || btcSearch.results.some(result => result.verified !== false) || btcSearch.results.filter(result => result.symbol.toUpperCase() === "BTC").length < 3) process.exit(1);
const btcKeys = btcSearch.results.map(result => `${result.chain}:${result.address}`);
if (btcKeys.some(key => key.endsWith(":null")) || new Set(btcKeys).size !== btcKeys.length) process.exit(1);
if (bonerSearch.results.length < 4 || bonerSearch.results.some(result => result.verified !== false) || bonerSearch.results.filter(result => result.symbol.toUpperCase() === "BONER").length < 3) process.exit(1);
if (bonerSearch.results.some(result => !result.baseToken?.name || !result.baseToken?.symbol || !result.baseToken?.address)) process.exit(1);
if (bonerSearch.results.some(result => !result.quoteToken?.name || !result.quoteToken?.symbol || !result.quoteToken?.address)) process.exit(1);
if (bonerSearch.results.some(result => !result.chain || !result.pairAddress)) process.exit(1);
const bonerKeys = bonerSearch.results.map(result => `${result.chain}:${result.address}`);
if (new Set(bonerKeys).size !== bonerKeys.length) process.exit(1);
' "$stock_json" "$sec_stock_json" "$crypto_json" "$stock_search_json" "$arbitrary_stock_search_json" "$btc_search_json" "$boner_search_json"
