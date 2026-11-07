import logging
import time
import requests
from typing import Dict, Any, Optional, List
from config.settings import settings
from src.notifications import notifier

logger = logging.getLogger("polymarket_bot")

class PolymarketClient:
    def __init__(self):
        self.clob_url = settings.CLOB_API_URL
        self.dry_run = settings.DRY_RUN
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        
        # Simulated Paper Trading State (for safe testing)
        self.portfolio_file = settings.LOGS_DIR / "simulated_portfolio.json"
        self.simulated_balance_usd = 1000.0
        self.simulated_positions: Dict[str, Dict[str, Any]] = {}
        self.order_history: List[Dict[str, Any]] = []
        self._load_simulated_portfolio()

        # Real CLOB Client instance
        self.real_client = None
        self._init_client()

    def _load_simulated_portfolio(self):
        """Load simulated portfolio from disk if available."""
        if self.portfolio_file.exists():
            try:
                import json
                with open(self.portfolio_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.simulated_balance_usd = float(data.get("cash_usd", 1000.0))
                    self.simulated_positions = data.get("positions", {})
                    self.order_history = data.get("history", [])
            except Exception as e:
                logger.debug(f"Could not load simulated portfolio: {e}")

    def _save_simulated_portfolio(self):
        """Persist simulated portfolio to disk."""
        try:
            import json
            data = {
                "cash_usd": round(self.simulated_balance_usd, 2),
                "positions": self.simulated_positions,
                "history": self.order_history[-50:]  # keep recent 50
            }
            with open(self.portfolio_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not save simulated portfolio: {e}")

    def _init_client(self):
        """Initialize official py-clob-client if credentials available and not in dry-run."""
        if self.dry_run:
            logger.info("[INIT] PolymarketClient running in DRY-RUN mode (Simulated Paper Trading). No real funds at risk.")
            return

        if not settings.is_configured_for_live():
            logger.warning("[WARNING] Real trading credentials not fully configured. Falling back to DRY-RUN mode.")
            self.dry_run = True
            return

        try:
            # Attempt to load py-clob-client
            try:
                from py_clob_client.client import ClobClient
                self.real_client = ClobClient(
                    host=self.clob_url,
                    key=settings.POLYGON_PRIVATE_KEY,
                    chain_id=settings.CHAIN_ID,
                    signature_type=settings.SIGNATURE_TYPE
                )
                creds = self.real_client.create_or_derive_api_creds()
                self.real_client.set_api_creds(creds)
                logger.info("[AUTH] Official py-clob-client initialized successfully with L1/L2 authentication.")
            except ImportError:
                from py_clob_client_v2 import ClobClient
                temp_client = ClobClient(host=self.clob_url, chain_id=settings.CHAIN_ID, key=settings.POLYGON_PRIVATE_KEY)
                creds = temp_client.create_or_derive_api_key()
                self.real_client = ClobClient(
                    host=self.clob_url,
                    chain_id=settings.CHAIN_ID,
                    key=settings.POLYGON_PRIVATE_KEY,
                    creds=creds
                )
                logger.info("[AUTH] py-clob-client-v2 initialized successfully.")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize live Polymarket ClobClient: {e}. Defaulting to DRY-RUN safety.")
            self.dry_run = True

    def get_order_book(self, token_id: str) -> Dict[str, Any]:
        """Fetch current order book for a given token ID."""
        try:
            url = f"{self.clob_url}/book"
            params = {"token_id": token_id}
            res = requests.get(url, params=params, headers=self.headers, timeout=5)
            res.raise_for_status()
            data = res.json()
            
            # Format bids and asks as sorted floats
            bids = []
            for b in data.get("bids", []):
                try:
                    bids.append({"price": float(b["price"]), "size": float(b["size"])})
                except (KeyError, ValueError):
                    continue
            
            asks = []
            for a in data.get("asks", []):
                try:
                    asks.append({"price": float(a["price"]), "size": float(a["size"])})
                except (KeyError, ValueError):
                    continue

            # Sort bids descending (highest first) and asks ascending (lowest first)
            bids.sort(key=lambda x: x["price"], reverse=True)
            asks.sort(key=lambda x: x["price"])

            best_bid = bids[0]["price"] if bids else 0.0
            best_ask = asks[0]["price"] if asks else 1.0

            return {
                "token_id": token_id,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": round(best_ask - best_bid, 4),
                "bids": bids,
                "asks": asks,
                "timestamp": data.get("timestamp")
            }
        except Exception as e:
            logger.error(f"Error fetching order book for {token_id}: {e}")
            return {"token_id": token_id, "best_bid": 0.0, "best_ask": 1.0, "spread": 1.0, "bids": [], "asks": []}

    def get_midpoint_price(self, token_id: str) -> float:
        """Fetch midpoint price directly from CLOB."""
        try:
            url = f"{self.clob_url}/midpoint"
            params = {"token_id": token_id}
            res = requests.get(url, params=params, headers=self.headers, timeout=5)
            res.raise_for_status()
            data = res.json()
            return float(data.get("mid", 0.0))
        except Exception:
            book = self.get_order_book(token_id)
            if book["best_bid"] > 0 and book["best_ask"] < 1.0:
                return round((book["best_bid"] + book["best_ask"]) / 2, 4)
            return 0.0

    def place_order(
        self,
        token_id: str,
        side: str,  # 'BUY' or 'SELL'
        price: float,
        size: float,
        market_title: str = "",
        outcome: str = "Yes"
    ) -> Dict[str, Any]:
        """
        Execute an order. If DRY_RUN is active, it simulates fill against the live book.
        If live, places order on Polymarket CLOB.
        """
        side = side.upper()
        order_cost_usd = price * size
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # DRY RUN SIMULATION
        if self.dry_run:
            if side == "BUY":
                if order_cost_usd > self.simulated_balance_usd:
                    logger.warning(f"[DRY-RUN] Insufficient funds: Cost ${order_cost_usd:.2f} > Balance ${self.simulated_balance_usd:.2f}")
                    return {"status": "REJECTED", "reason": "Insufficient simulated funds"}
                
                self.simulated_balance_usd -= order_cost_usd
                pos = self.simulated_positions.get(token_id, {"shares": 0.0, "avg_entry": 0.0, "title": market_title, "outcome": outcome})
                total_shares = pos["shares"] + size
                new_avg = ((pos["shares"] * pos["avg_entry"]) + order_cost_usd) / total_shares if total_shares > 0 else price
                self.simulated_positions[token_id] = {
                    "shares": total_shares,
                    "avg_entry": round(new_avg, 4),
                    "title": market_title or token_id[:10],
                    "outcome": outcome
                }
            elif side == "SELL":
                pos = self.simulated_positions.get(token_id, {"shares": 0.0, "avg_entry": 0.0})
                if pos["shares"] < size:
                    size = pos["shares"]  # Sell whatever is owned
                if size <= 0:
                    return {"status": "REJECTED", "reason": "No shares to sell"}
                
                self.simulated_balance_usd += (price * size)
                pos["shares"] -= size
                if pos["shares"] <= 0.0001:
                    self.simulated_positions.pop(token_id, None)

            trade_record = {
                "order_id": f"sim_{int(time.time()*1000)}",
                "mode": "DRY_RUN",
                "timestamp": timestamp,
                "token_id": token_id,
                "title": market_title,
                "outcome": outcome,
                "side": side,
                "price": price,
                "size": size,
                "cost_usd": round(order_cost_usd, 2),
                "status": "FILLED"
            }
            self.order_history.append(trade_record)
            self._save_simulated_portfolio()
            
            msg = (
                f"[SIMULATED TRADE]\n"
                f"Market: {market_title}\n"
                f"Side: {side} {outcome}\n"
                f"Price: ${price:.3f} | Size: {size:.2f} shares\n"
                f"Total Cost: ${order_cost_usd:.2f}\n"
                f"Simulated Cash Remaining: ${self.simulated_balance_usd:.2f}"
            )
            logger.info(msg)
            notifier.send(msg, level="TRADE")
            return {"status": "FILLED", "order": trade_record}

        # LIVE EXECUTION
        try:
            logger.info(f"[EXEC] Submitting LIVE {side} order: {size} @ ${price:.3f} on {token_id}...")
            # Using py-clob-client
            from py_clob_client.clob_types import OrderArgs, OrderType
            from py_clob_client.order_builder.constants import BUY, SELL

            clob_side = BUY if side == "BUY" else SELL
            order_args = OrderArgs(
                price=price,
                size=size,
                side=clob_side,
                token_id=token_id
            )
            signed_order = self.real_client.create_order(order_args)
            resp = self.real_client.post_order(signed_order, OrderType.GTC)
            
            logger.info(f"[SUCCESS] LIVE Order submitted: {resp}")
            notifier.send(f"LIVE {side} Order submitted for {market_title} ({outcome}): {size} shares @ ${price:.3f}", level="TRADE")
            return {"status": "SUBMITTED", "response": resp}
        except Exception as e:
            logger.error(f"[ERROR] Failed to submit live order: {e}")
            notifier.send(f"Order failed on {market_title}: {e}", level="ERROR")
            return {"status": "ERROR", "error": str(e)}

    def cancel_all_orders(self):
        """Cancel open orders."""
        if self.dry_run or not self.real_client:
            logger.info("All simulated orders cleared.")
            return
        try:
            self.real_client.cancel_all()
            logger.info("Cancelled all open orders on CLOB.")
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")

polymarket_client = PolymarketClient()
