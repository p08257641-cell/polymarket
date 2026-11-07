import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from config.settings import settings

logger = logging.getLogger("polymarket_bot")

class BotStatusHandler(BaseHTTPRequestHandler):
    # References injected by PolymarketBot
    bot_instance = None

    def log_message(self, format, *args):
        # Silence default standard HTTP logging so console stays clean
        pass

    def do_GET(self):
        if self.path in ("/", "/health", "/status"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            from src.polymarket_client import polymarket_client

            # Calculate detailed portfolio financials
            positions = polymarket_client.simulated_positions if settings.DRY_RUN else {}
            invested_usd = 0.0
            expected_payout_usd = 0.0
            positions_list = []

            for tid, pos in positions.items():
                cost = round(pos["shares"] * pos["avg_entry"], 2)
                payout = round(pos["shares"] * 1.0, 2)
                invested_usd += cost
                expected_payout_usd += payout
                positions_list.append({
                    "market": pos.get("title", tid[:15]),
                    "outcome": pos.get("outcome", "Yes"),
                    "shares": round(pos["shares"], 2),
                    "entry_price": round(pos["avg_entry"], 3),
                    "invested_cost_usd": cost,
                    "expected_payout_usd": payout,
                    "expected_profit_usd": round(payout - cost, 2)
                })

            cash = round(polymarket_client.simulated_balance_usd, 2) if settings.DRY_RUN else "N/A"
            expected_profit_total = round(expected_payout_usd - invested_usd, 2)
            total_portfolio = round(cash + expected_payout_usd, 2) if isinstance(cash, (int, float)) else "N/A"

            status_payload = {
                "status": "RUNNING",
                "service": "Polymarket 24/7 Cloud Trader",
                "mode": "DRY_RUN" if settings.DRY_RUN else "LIVE",
                "profit_status": f"+${expected_profit_total:.2f} PENDING UPON RESOLUTION",
                "cash_balance_usd": cash,
                "invested_in_trades_usd": round(invested_usd, 2),
                "expected_resolution_payout_usd": round(expected_payout_usd, 2),
                "expected_net_profit_usd": expected_profit_total,
                "estimated_total_portfolio_usd": total_portfolio,
                "open_positions_count": len(positions_list),
                "open_positions": positions_list,
                "uptime_iterations": getattr(self.bot_instance, "iteration", 0) if self.bot_instance else 0
            }
            self.wfile.write(json.dumps(status_payload, indent=2).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def start_health_server(bot_ref, port: int = 8080):
    """Start the lightweight health web server in a daemon thread."""
    BotStatusHandler.bot_instance = bot_ref
    server = HTTPServer(("0.0.0.0", port), BotStatusHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"[SERVER] 24/7 Web & Health Keep-Alive server listening on port {port}")
    return server
