import os
import sys
import time
import signal
import logging
from datetime import datetime, timezone
from config.settings import settings
from src.rule_engine import rule_engine
from src.polymarket_client import polymarket_client
from src.notifications import notifier
from src.health_server import start_health_server

# Setup logging
def setup_logging():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.LOGS_DIR / "trader.log", encoding="utf-8")
    ]
    logging.basicConfig(level=logging.INFO, format=log_format, handlers=handlers)

logger = logging.getLogger("polymarket_bot")

class PolymarketBot:
    def __init__(self):
        self.running = False
        self.iteration = 0
        self.last_heartbeat = 0
        self.current_day_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.daily_profit_usd = 0.0
        self.daily_target_hit = False

    def start(self):
        self.running = True
        setup_logging()

        # Start 24/7 keep-alive server for Koyeb / Free cloud hosting
        if settings.ENABLE_HEALTH_SERVER:
            start_health_server(self, port=settings.WEB_SERVER_PORT)

        goal_str = "UNLIMITED (No Daily Cap)" if settings.DAILY_PROFIT_TARGET_USD <= 0 else f"${settings.DAILY_PROFIT_TARGET_USD:.2f}/day"
        mode_str = "DRY-RUN (Paper Trading)" if settings.DRY_RUN else "LIVE TRADING (Real Funds)"
        logger.info("=" * 60)
        logger.info("[BOT] Polymarket 24/7 Cloud Trading Bot Started")
        logger.info(f"[MODE] Mode: {mode_str}")
        logger.info(f"[GOAL] Profit Mode: {goal_str}")
        logger.info(f"[TIMER] Loop Frequency: Every {settings.LOOP_INTERVAL_SECONDS} seconds")
        logger.info(f"[RISK] Max Single Order: ${settings.MAX_ORDER_SIZE_USD:.2f}")
        logger.info(f"[RISK] Max Portfolio Exposure: ${settings.MAX_TOTAL_EXPOSURE_USD:.2f}")
        logger.info("=" * 60)

        notifier.send(
            f"[BOT] Polymarket Cloud Trader Started\n"
            f"Mode: {mode_str}\n"
            f"Daily Target: {goal_str}\n"
            f"Loop Frequency: {settings.LOOP_INTERVAL_SECONDS}s",
            level="INFO"
        )

        # Register signal handlers for clean cloud termination
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Main 24/7 Loop
        while self.running:
            self.iteration += 1
            now = time.time()
            today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # Reset daily profit counter on new UTC day
            if today_utc != self.current_day_utc:
                logger.info(f"[DAY RESET] New trading day ({today_utc}). Resetting daily profit tracker.")
                self.current_day_utc = today_utc
                self.daily_profit_usd = 0.0
                self.daily_target_hit = False

            try:
                # 1. Periodic Heartbeat (every 10 minutes)
                if now - self.last_heartbeat >= 600:
                    self._log_heartbeat()
                    self.last_heartbeat = now

                # 2. Check if daily profit target already achieved (if a cap is configured)
                if settings.DAILY_PROFIT_TARGET_USD > 0 and self.daily_profit_usd >= settings.DAILY_PROFIT_TARGET_USD:
                    if not self.daily_target_hit:
                        msg = f"[GOAL HIT] Daily target of ${settings.DAILY_PROFIT_TARGET_USD:.2f} reached! ($ {self.daily_profit_usd:.2f}). Pausing trades until tomorrow."
                        logger.info(msg)
                        notifier.send(msg, level="TRADE")
                        self.daily_target_hit = True
                else:
                    # 3. Evaluate all active rules continuously
                    rule_engine.evaluate_all()

            except KeyboardInterrupt:
                logger.info("Shutdown requested by user.")
                break
            except Exception as e:
                logger.error(f"Unexpected error in trading loop: {e}", exc_info=True)
                # Sleep briefly to avoid hot-looping on repeated errors
                time.sleep(5)

            # Sleep until next check
            time.sleep(settings.LOOP_INTERVAL_SECONDS)

        self._shutdown()

    def _log_heartbeat(self):
        positions = polymarket_client.simulated_positions if settings.DRY_RUN else {}
        cash = polymarket_client.simulated_balance_usd if settings.DRY_RUN else "N/A"
        active_pos_count = len(positions)
        logger.info(
            f"[HEARTBEAT] Bot running healthy | Iterations: {self.iteration} | "
            f"Active Positions: {active_pos_count} | Cash: ${cash if isinstance(cash, str) else f'{cash:.2f}'}"
        )

    def _handle_shutdown(self, signum, frame):
        logger.info(f"Received termination signal ({signum}). Initiating graceful shutdown...")
        self.running = False

    def _shutdown(self):
        logger.info("Shutting down bot safely...")
        notifier.send("[ALERT] Polymarket Cloud Trader has shut down.", level="ALERT")
        logger.info("Bot successfully stopped.")

if __name__ == "__main__":
    bot = PolymarketBot()
    bot.start()
