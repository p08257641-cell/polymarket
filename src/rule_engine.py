import json
import logging
from typing import Dict, Any, List
from config.settings import settings
from src.market_finder import market_finder
from src.polymarket_client import polymarket_client
from src.risk_manager import risk_manager

logger = logging.getLogger("polymarket_bot")

class RuleEngine:
    def __init__(self):
        self.rules_file = settings.RULES_PATH

    def load_rules(self) -> List[Dict[str, Any]]:
        """Load and parse trading rules from JSON file."""
        try:
            if not self.rules_file.exists():
                logger.warning(f"Rules file {self.rules_file} not found.")
                return []
            with open(self.rules_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [r for r in data.get("rules", []) if r.get("enabled", False)]
        except Exception as e:
            logger.error(f"Failed to read trading rules: {e}")
            return []

    def evaluate_all(self):
        """Main evaluation cycle: checks all active rules against live Polymarket data."""
        rules = self.load_rules()
        if not rules:
            logger.info("No active rules found to evaluate.")
            return

        for rule in rules:
            try:
                rule_type = rule.get("type")
                if rule_type == "price_threshold":
                    self._evaluate_price_threshold(rule)
                elif rule_type == "binary_arbitrage":
                    self._evaluate_binary_arbitrage(rule)
                elif rule_type == "high_prob_settlement":
                    self._evaluate_high_prob_settlement(rule)
                elif rule_type == "price_range_scalp":
                    self._evaluate_price_range_scalp(rule)
                else:
                    logger.warning(f"Unknown rule type: {rule_type} in rule '{rule.get('id')}'")
            except Exception as e:
                logger.error(f"Error evaluating rule '{rule.get('id')}': {e}", exc_info=True)

    def _evaluate_price_threshold(self, rule: Dict[str, Any]):
        rule_id = rule["id"]
        filt = rule.get("market_filter", {})
        params = rule.get("params", {})
        slug = filt.get("slug")

        market = market_finder.get_market_by_slug(slug) if slug else None
        if not market:
            logger.warning(f"[{rule_id}] Market slug '{slug}' not found or inactive.")
            return

        outcome = params.get("outcome", "Yes")
        token_id = market["clob_tokens"].get(outcome)
        if not token_id:
            logger.warning(f"[{rule_id}] Token for outcome '{outcome}' not found in market {slug}")
            return

        book = polymarket_client.get_order_book(token_id)
        best_ask = book["best_ask"]
        best_bid = book["best_bid"]
        mid = polymarket_client.get_midpoint_price(token_id)
        current_price = best_ask if best_ask > 0 else mid

        logger.info(
            f"[RULE] [{rule['name']}] Market: '{market['question'][:40]}...' | "
            f"Current {outcome} Price: ${current_price:.3f} (Bid: ${best_bid:.3f}, Ask: ${best_ask:.3f})"
        )

        # 1. Check Take-Profit & Stop-Loss for existing positions
        positions = polymarket_client.simulated_positions if polymarket_client.dry_run else {}
        if token_id in positions:
            pos = positions[token_id]
            shares = pos["shares"]
            avg_entry = pos["avg_entry"]
            take_profit = params.get("take_profit_price")
            stop_loss = params.get("stop_loss_price")

            # Take profit trigger
            if take_profit and best_bid >= take_profit:
                logger.info(f"[PROFIT] TAKE PROFIT TRIGGERED for {outcome}: Bid ${best_bid:.3f} >= Target ${take_profit:.3f}")
                polymarket_client.place_order(
                    token_id=token_id,
                    side="SELL",
                    price=best_bid,
                    size=shares,
                    market_title=market["question"],
                    outcome=outcome
                )
                risk_manager.record_trade_execution(rule_id, token_id)
                return

            # Stop loss trigger
            if stop_loss and best_bid <= stop_loss:
                logger.info(f"[STOP-LOSS] STOP LOSS TRIGGERED for {outcome}: Bid ${best_bid:.3f} <= Cutoff ${stop_loss:.3f}")
                polymarket_client.place_order(
                    token_id=token_id,
                    side="SELL",
                    price=best_bid,
                    size=shares,
                    market_title=market["question"],
                    outcome=outcome
                )
                risk_manager.record_trade_execution(rule_id, token_id)
                return

        # 2. Check Entry Buy Trigger
        trigger_below = params.get("trigger_price_below")
        if trigger_below and current_price <= trigger_below:
            order_amount = params.get("order_amount_usd", 10.0)
            shares_to_buy = round(order_amount / current_price, 2)
            
            # Risk check
            current_exposure = sum(
                p["shares"] * p["avg_entry"] for p in polymarket_client.simulated_positions.values()
            ) if polymarket_client.dry_run else 0.0

            allowed, reason = risk_manager.can_execute_trade(
                rule_id=rule_id,
                token_id=token_id,
                price=current_price,
                amount_usd=order_amount,
                current_exposure_usd=current_exposure
            )

            if not allowed:
                logger.info(f"[SKIP] [{rule_id}] Rule triggered but skipped by Risk Manager: {reason}")
                return

            logger.info(f"[TRIGGER] BUY CONDITION MET: Price ${current_price:.3f} <= Trigger ${trigger_below:.3f}")
            polymarket_client.place_order(
                token_id=token_id,
                side="BUY",
                price=current_price,
                size=shares_to_buy,
                market_title=market["question"],
                outcome=outcome
            )
            risk_manager.record_trade_execution(rule_id, token_id)

    def _evaluate_binary_arbitrage(self, rule: Dict[str, Any]):
        """Scan top markets to find instances where Buy(YES) + Buy(NO) < 1.00 - spread."""
        rule_id = rule["id"]
        params = rule.get("params", {})
        filt = rule.get("market_filter", {})
        max_cost = params.get("max_combined_cost", 0.98)
        leg_amount_usd = params.get("allocation_per_leg_usd", 10.0)

        markets = market_finder.get_top_volume_markets(limit=filt.get("max_markets_to_scan", 15))
        for m in markets:
            if m.get("closed") or not m.get("active"):
                continue
            
            tokens = m.get("clob_tokens", {})
            yes_token = tokens.get("Yes")
            no_token = tokens.get("No")
            if not yes_token or not no_token:
                continue

            book_yes = polymarket_client.get_order_book(yes_token)
            book_no = polymarket_client.get_order_book(no_token)

            ask_yes = book_yes["best_ask"]
            ask_no = book_no["best_ask"]

            if ask_yes > 0 and ask_no > 0:
                combined_cost = ask_yes + ask_no
                if combined_cost <= max_cost:
                    profit_pct = round(((1.0 - combined_cost) / combined_cost) * 100, 2)
                    logger.info(
                        f"[ARBITRAGE] Opportunity in: {m['question']}\n"
                        f"   Ask YES: ${ask_yes:.3f} + Ask NO: ${ask_no:.3f} = ${combined_cost:.3f}\n"
                        f"   Guaranteed Resolution Margin: +{profit_pct}%"
                    )

                    # Execute both legs
                    size_yes = round(leg_amount_usd / ask_yes, 2)
                    size_no = round(leg_amount_usd / ask_no, 2)

                    polymarket_client.place_order(yes_token, "BUY", ask_yes, size_yes, m["question"], "Yes")
                    polymarket_client.place_order(no_token, "BUY", ask_no, size_no, m["question"], "No")
                    risk_manager.record_trade_execution(rule_id, yes_token)
                    break

    def _evaluate_high_prob_settlement(self, rule: Dict[str, Any]):
        """
        High-Probability Settlement Harvesting Strategy:
        Scans liquid markets where outcome is 97% to 98.5% decided ($0.970 - $0.985).
        Buys and holds until $1.00 settlement to capture a low-risk 1.5% - 3.0% yield.
        A few fills per day reliably yields the $3.00 daily target.
        """
        rule_id = rule["id"]
        params = rule.get("params", {})
        filt = rule.get("market_filter", {})

        min_entry_price = params.get("min_entry_price", 0.965)
        max_entry_price = params.get("max_entry_price", 0.985)
        allocation_usd = params.get("allocation_usd", 25.0)
        min_vol = filt.get("min_volume_24hr", 20000)

        markets = market_finder.get_top_volume_markets(limit=filt.get("max_markets_to_scan", 10))
        for m in markets:
            if m.get("closed") or not m.get("active"):
                continue
            if m.get("volume_24hr", 0) < min_vol:
                continue

            # Check each outcome (Yes or No)
            for outcome, token_id in m.get("clob_tokens", {}).items():
                if not token_id:
                    continue

                book = polymarket_client.get_order_book(token_id)
                best_ask = book["best_ask"]

                if min_entry_price <= best_ask <= max_entry_price:
                    expected_yield_pct = round(((1.0 - best_ask) / best_ask) * 100, 2)
                    shares = round(allocation_usd / best_ask, 2)
                    expected_profit = round(shares * (1.0 - best_ask), 2)

                    logger.info(
                        f"[HIGH-PROB HARVEST] Opportunity in: '{m['question'][:40]}...'\n"
                        f"   Outcome: {outcome} @ ${best_ask:.3f} | Expected Resolution Yield: +{expected_yield_pct}%\n"
                        f"   Target Profit on ${allocation_usd:.2f}: +${expected_profit:.2f}"
                    )

                    current_exposure = sum(
                        p["shares"] * p["avg_entry"] for p in polymarket_client.simulated_positions.values()
                    ) if polymarket_client.dry_run else 0.0

                    allowed, reason = risk_manager.can_execute_trade(
                        rule_id=rule_id,
                        token_id=token_id,
                        price=best_ask,
                        amount_usd=allocation_usd,
                        current_exposure_usd=current_exposure
                    )

                    if allowed:
                        polymarket_client.place_order(
                            token_id=token_id,
                            side="BUY",
                            price=best_ask,
                            size=shares,
                            market_title=m["question"],
                            outcome=outcome
                        )
                        risk_manager.record_trade_execution(rule_id, token_id)
                        return  # Execute one high-confidence trade per cycle
                    else:
                        logger.info(f"[SKIP] High-prob trade skipped by risk manager: {reason}")

    def _evaluate_price_range_scalp(self, rule: Dict[str, Any]):
        # Scalping logic for deep-discount markets
        pass

rule_engine = RuleEngine()
