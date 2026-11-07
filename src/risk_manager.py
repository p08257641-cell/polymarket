import time
import logging
from typing import Dict, Any, Tuple
from config.settings import settings

logger = logging.getLogger("polymarket_bot")

class RiskManager:
    def __init__(self):
        self.max_order_size_usd = settings.MAX_ORDER_SIZE_USD
        self.max_total_exposure = settings.MAX_TOTAL_EXPOSURE_USD
        self.max_slippage = settings.MAX_SLIPPAGE_PERCENT / 100.0
        self.cooldown_seconds = 60  # Don't trigger the same rule on the same market within 60s
        self.last_trade_time: Dict[str, float] = {}

    def can_execute_trade(
        self,
        rule_id: str,
        token_id: str,
        price: float,
        amount_usd: float,
        current_exposure_usd: float
    ) -> Tuple[bool, str]:
        """Validate whether a proposed trade complies with all risk parameters."""
        # 1. Price boundaries
        if price <= 0.001 or price >= 0.999:
            return False, f"Price ${price:.3f} outside valid boundary (0.001 - 0.999)"

        # 2. Maximum single order size
        if amount_usd > self.max_order_size_usd:
            return False, f"Order size ${amount_usd:.2f} exceeds MAX_ORDER_SIZE_USD (${self.max_order_size_usd:.2f})"

        # 3. Maximum total exposure
        if (current_exposure_usd + amount_usd) > self.max_total_exposure:
            return False, f"Total exposure would reach ${current_exposure_usd + amount_usd:.2f}, exceeding limit (${self.max_total_exposure:.2f})"

        # 4. Anti-spam / Cooldown prevention
        key = f"{rule_id}_{token_id}"
        last_time = self.last_trade_time.get(key, 0.0)
        now = time.time()
        if (now - last_time) < self.cooldown_seconds:
            remaining = int(self.cooldown_seconds - (now - last_time))
            return False, f"Cooldown active for rule '{rule_id}'. Wait {remaining}s."

        return True, "Approved"

    def record_trade_execution(self, rule_id: str, token_id: str):
        """Record timestamp of trade to prevent double-execution."""
        key = f"{rule_id}_{token_id}"
        self.last_trade_time[key] = time.time()

risk_manager = RiskManager()
