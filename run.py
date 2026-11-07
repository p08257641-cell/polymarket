import argparse
import sys

# Ensure UTF-8 output encoding for cross-platform terminals (Windows CMD / PowerShell / Linux)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from tabulate import tabulate
from config.settings import settings
from src.bot import PolymarketBot
from src.market_finder import market_finder
from src.polymarket_client import polymarket_client
from src.rule_engine import rule_engine

def cmd_search(query: str, limit: int = 10):
    print(f"\n[SEARCH] Querying Polymarket for: '{query}' (limit: {limit})...\n")
    results = market_finder.search_markets(query, limit=limit)
    if not results:
        print("No markets found matching your query.")
        return

    table = []
    for r in results:
        yes_token = r["clob_tokens"].get("Yes", "N/A")
        price_yes = r["outcome_prices"].get("Yes", 0.0)
        table.append([
            r["question"][:50] + ("..." if len(r["question"]) > 50 else ""),
            r["slug"],
            f"${price_yes:.3f}" if price_yes else "N/A",
            f"${r['volume_24hr']:,.0f}",
            yes_token[:16] + "..." if len(yes_token) > 16 else yes_token
        ])

    headers = ["Question", "Slug", "Yes Price", "24h Vol", "Yes Token ID"]
    print(tabulate(table, headers=headers, tablefmt="grid"))
    print("\nTip: Copy the 'Slug' into config/trading_rules.json to create a rule for that market!\n")

def cmd_status():
    print("\n" + "=" * 55)
    print(" [*] POLYMARKET CLOUD BOT STATUS")
    print("=" * 55)
    mode = "DRY-RUN (Simulation)" if settings.DRY_RUN else "LIVE TRADING"
    print(f"Mode: {mode}")
    print(f"Rules configured: {len(rule_engine.load_rules())} active")
    
    if settings.DRY_RUN:
        print(f"Simulated Cash: ${polymarket_client.simulated_balance_usd:,.2f}")
        positions = polymarket_client.simulated_positions
        if positions:
            print("\nOpen Simulated Positions:")
            pos_table = []
            for tid, p in positions.items():
                pos_table.append([p.get("title", tid[:15]), p.get("outcome"), f"{p['shares']:.2f}", f"${p['avg_entry']:.3f}"])
            print(tabulate(pos_table, headers=["Market", "Outcome", "Shares", "Avg Price"], tablefmt="simple"))
        else:
            print("No open positions.")
    print("=" * 55 + "\n")

def cmd_test_rules():
    from src.bot import setup_logging
    setup_logging()
    print("\n[TEST] Running single-pass evaluation of trading rules...\n")
    rule_engine.evaluate_all()
    print("\n[DONE] Evaluation complete.\n")

def main():
    parser = argparse.ArgumentParser(description="Polymarket 24/7 Cloud Trading Bot")
    parser.add_argument("--search", type=str, help="Search markets by keyword/topic")
    parser.add_argument("--status", action="store_true", help="View current positions and mode")
    parser.add_argument("--test-rules", action="store_true", help="Run a single-pass rule test without looping")
    parser.add_argument("--live", action="store_true", help="Override to live trading mode")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run simulation mode")

    args = parser.parse_args()

    if args.dry_run:
        settings.DRY_RUN = True
    elif args.live:
        settings.DRY_RUN = False

    if args.search:
        cmd_search(args.search)
    elif args.status:
        cmd_status()
    elif args.test_rules:
        cmd_test_rules()
    else:
        # Run main 24/7 loop
        bot = PolymarketBot()
        bot.start()

if __name__ == "__main__":
    main()
