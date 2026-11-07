import json
import logging
import requests
from typing import List, Dict, Any, Optional
from config.settings import settings

logger = logging.getLogger("polymarket_bot")

class MarketFinder:
    def __init__(self):
        self.gamma_url = settings.GAMMA_API_URL
        self.headers = {
            "User-Agent": "PolymarketCloudTrader/1.0",
            "Accept": "application/json"
        }

    def _safe_json_parse(self, val: Any, default=None):
        if isinstance(val, (list, dict)):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return default or []
        return default or []

    def normalize_market(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Convert raw Gamma API market object into clean structured dictionary."""
        outcomes = self._safe_json_parse(raw.get("outcomes"), ["Yes", "No"])
        clob_tokens = self._safe_json_parse(raw.get("clobTokenIds"), [])
        outcome_prices = self._safe_json_parse(raw.get("outcomePrices"), [])

        token_map = {}
        price_map = {}
        for idx, outcome in enumerate(outcomes):
            if idx < len(clob_tokens):
                token_map[outcome] = clob_tokens[idx]
            if idx < len(outcome_prices):
                try:
                    price_map[outcome] = float(outcome_prices[idx])
                except (ValueError, TypeError):
                    price_map[outcome] = 0.0

        return {
            "id": raw.get("id"),
            "question": raw.get("question", "Unknown Question"),
            "slug": raw.get("slug", ""),
            "condition_id": raw.get("conditionId"),
            "active": raw.get("active", False),
            "closed": raw.get("closed", False),
            "end_date": raw.get("endDate"),
            "volume_24hr": float(raw.get("volume24hr", 0) or 0),
            "volume_total": float(raw.get("volume", 0) or 0),
            "liquidity": float(raw.get("liquidity", 0) or 0),
            "outcomes": outcomes,
            "clob_tokens": token_map,
            "outcome_prices": price_map,
            "raw": raw
        }

    def search_markets(self, query: str = "", limit: int = 10) -> List[Dict[str, Any]]:
        """Search active markets by text query or slug, ordered by 24h volume."""
        try:
            params = {
                "active": "true",
                "closed": "false",
                "order": "volume24hr",
                "ascending": "false",
                "limit": 100 if query else limit
            }
            res = requests.get(f"{self.gamma_url}/markets", params=params, headers=self.headers, timeout=10)
            res.raise_for_status()
            data = res.json()

            results = []
            query_lower = query.lower().strip()
            for item in data:
                norm = self.normalize_market(item)
                if not query_lower:
                    results.append(norm)
                elif query_lower in norm["question"].lower() or query_lower in norm["slug"].lower():
                    results.append(norm)

                if len(results) >= limit:
                    break

            return results
        except Exception as e:
            logger.error(f"Error searching markets for query '{query}': {e}")
            return []

    def get_market_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Fetch single market by unique slug."""
        try:
            params = {"slug": slug.strip()}
            res = requests.get(f"{self.gamma_url}/markets", params=params, headers=self.headers, timeout=10)
            res.raise_for_status()
            data = res.json()
            if data and len(data) > 0:
                return self.normalize_market(data[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching market slug '{slug}': {e}")
            return None

    def get_top_volume_markets(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch most active markets sorted by 24h volume."""
        try:
            params = {
                "active": "true",
                "closed": "false",
                "order": "volume24hr",
                "ascending": "false",
                "limit": limit
            }
            res = requests.get(f"{self.gamma_url}/markets", params=params, headers=self.headers, timeout=10)
            res.raise_for_status()
            return [self.normalize_market(m) for m in res.json()]
        except Exception as e:
            logger.error(f"Error fetching top volume markets: {e}")
            return []

market_finder = MarketFinder()
