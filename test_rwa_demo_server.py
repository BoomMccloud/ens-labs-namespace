import unittest
from unittest.mock import patch

import rwa_demo_server as server


class SecStockIdentityTests(unittest.TestCase):
    def setUp(self):
        self.rows = server._normalize_sec_payload(
            {
                "fields": ["exchange", "ticker", "name", "cik"],
                "data": [
                    ["NYSE", "IBM", "INTERNATIONAL BUSINESS MACHINES CORP", 51143],
                    ["Nasdaq", "MSFT", "MICROSOFT CORP", 789019],
                    ["NYSE", "IBM-WT", "IBM ACQUISITION WARRANT", 999999],
                    ["NYSE", "", "BROKEN ROW", 1],
                ],
            }
        )

    def test_normalizes_fields_by_name_and_drops_invalid_rows(self):
        self.assertEqual(3, len(self.rows))
        self.assertEqual(
            {
                "cik": 51143,
                "name": "INTERNATIONAL BUSINESS MACHINES CORP",
                "symbol": "IBM",
                "exchange": "NYSE",
            },
            self.rows[0],
        )

    def test_exact_ticker_wins_over_partial_name_matches(self):
        self.assertEqual("IBM", server._find_sec_stock("ibm", self.rows)["symbol"])

    def test_company_name_search_resolves_identity(self):
        result = server._find_sec_stock("international business machines", self.rows)
        self.assertEqual(51143, result["cik"])

    def test_catalog_search_marks_only_the_complete_ticker_match(self):
        rows = server._normalize_sec_payload(
            {
                "fields": ["cik", "name", "ticker", "exchange"],
                "data": [
                    [98537, "CITIGROUP INC", "C", "NYSE"],
                    [200, "CALEDONIA MINING CORP", "CMCL", "NYSE American"],
                    [300, "C3 AI INC", "AI", "NYSE"],
                    [400, "CABOT CORP", "CBT", "NYSE"],
                ],
            }
        )
        results = server._search_sec_stocks("C", rows, limit=4)
        self.assertEqual("C", results[0]["symbol"])
        self.assertTrue(results[0]["exact"])
        self.assertEqual(1, sum(result["exact"] for result in results))
        self.assertTrue(all(result["symbol"].startswith("C") for result in results))

    def test_sec_dataset_is_reused_from_cache(self):
        payload = '{"fields":["cik","name","ticker","exchange"],"data":[[51143,"IBM","IBM","NYSE"]]}'
        server._sec_stock_cache = None
        with patch.object(server, "_fetch_text", return_value=payload) as fetch:
            server._load_sec_stocks()
            server._load_sec_stocks()
        self.assertEqual(1, fetch.call_count)

    def test_quote_failure_keeps_the_sec_identity(self):
        server._cache.clear()
        identity = {"cik": 51143, "name": "IBM", "symbol": "IBM", "exchange": "NYSE"}
        with patch.object(server, "_resolve_stock_identity", return_value=(identity, True)), patch.object(
            server, "_fetch_stock_quote", side_effect=ValueError("offline")
        ):
            result = server.lookup_stock("IBM")
        self.assertEqual("SEC", result["identityProvider"])
        self.assertFalse(result["quoteLive"])
        self.assertIsNone(result["price"])


class CryptoCatalogTests(unittest.TestCase):
    def test_dex_result_preserves_pair_identity_fields(self):
        payload = {
            "pairs": [
                {
                    "chainId": "base",
                    "dexId": "uniswap",
                    "pairAddress": "0xpair",
                    "baseToken": {"address": "0xbase", "name": "Banana Gun", "symbol": "BANANA"},
                    "quoteToken": {"address": "0xquote", "name": "Wrapped Ether", "symbol": "WETH"},
                    "priceUsd": "1",
                    "liquidity": {"usd": 100},
                }
            ]
        }
        result = server._normalize_dex_search(payload, "BANANA", limit=1)[0]
        self.assertEqual("uniswap", result["dexId"])
        self.assertEqual("0xpair", result["pairAddress"])
        self.assertEqual(payload["pairs"][0]["baseToken"], result["baseToken"])
        self.assertEqual(payload["pairs"][0]["quoteToken"], result["quoteToken"])

    def test_known_tickers_use_contract_discovery_too(self):
        payload = '{"pairs":[{"chainId":"base","baseToken":{"address":"0xabc","name":"Bitcoin","symbol":"BTC"},"priceUsd":"1","liquidity":{"usd":100}}]}'
        server._cache.clear()
        with patch.object(server, "_fetch_text", return_value=payload):
            result = server.search_crypto("BTC")
        self.assertEqual("DexScreener", result["provider"])
        self.assertEqual("0xabc", result["results"][0]["address"])

    def test_coingecko_results_are_unverified_catalog_candidates(self):
        results = server._normalize_coingecko_search(
            {
                "coins": [
                    {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC", "market_cap_rank": 1},
                    {"id": "bitcoin-base", "name": "Bitcoin Base", "symbol": "BTC", "market_cap_rank": 3243},
                ]
            },
            "BTC",
            limit=5,
        )
        self.assertEqual(2, len(results))
        self.assertTrue(all(result["verified"] is False for result in results))
        self.assertEqual(1, results[0]["rank"])

    def test_dex_results_dedupe_contracts_not_pairs(self):
        token = {"address": "0xabc", "name": "Boner Coin", "symbol": "BONER"}
        payload = {
            "pairs": [
                {"chainId": "robinhood", "baseToken": token, "priceUsd": "0.05", "liquidity": {"usd": 200}, "marketCap": 5000},
                {"chainId": "robinhood", "baseToken": token, "priceUsd": "0.06", "liquidity": {"usd": 100}, "marketCap": 6000},
                {"chainId": "base", "baseToken": {**token, "address": "0xdef"}, "priceUsd": "0.001", "liquidity": {"usd": 50}, "marketCap": 1000},
            ]
        }
        results = server._normalize_dex_search(payload, "BONER", limit=5)
        self.assertEqual(2, len(results))
        self.assertEqual("0xabc", results[0]["address"])
        self.assertTrue(all(result["verified"] is False for result in results))


if __name__ == "__main__":
    unittest.main()
