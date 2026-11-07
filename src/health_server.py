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

            status_payload = {
                "status": "RUNNING",
                "service": "Polymarket 24/7 Cloud Trader",
                "mode": "DRY_RUN" if settings.DRY_RUN else "LIVE",
                "daily_profit_target_usd": settings.DAILY_PROFIT_TARGET_USD,
                "cash_usd": polymarket_client.simulated_balance_usd if settings.DRY_RUN else "N/A",
                "positions_count": len(polymarket_client.simulated_positions) if settings.DRY_RUN else "N/A",
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
