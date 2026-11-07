# 🌐 Polymarket 24/7 Cloud Automated Trading Bot

A production-grade, 24/7 cloud trading bot for [Polymarket](https://polymarket.com). It runs continuously on any cloud server (DigitalOcean, AWS, Hetzner, Railway, etc.), monitors live order books, and automatically submits trades based on your custom rules with built-in risk management.

---

## ⚡ Highlights

- **24/7 Cloud Ready**: Includes Docker & Docker Compose setup, auto-restart on crashes or server reboots, and Linux `systemd` service templates.
- **Simulated Paper Trading Mode (Dry-Run)**: Test any strategy or rule against live Polymarket order books without risking real money.
- **Rule Engine**:
  - **Price Threshold**: Buy YES/NO on dips, take profit on spikes, or trigger stop-loss cutoffs.
  - **Negative-Risk / Binary Arbitrage**: Exploits mispricings where `Ask(YES) + Ask(NO) < 1.00 - margin` to lock in profit.
  - **Volume & Topic Filtering**: Automatically scans high-volume or specific topic markets.
- **Risk Guardrails**: Limits maximum position size, maximum portfolio exposure, cooldowns, and slippage protection.
- **Real-Time Mobile Notifications**: Integrates with Telegram and Discord webhooks to alert you whenever trades occur or rules trigger.
- **CLI Utilities**: Search active markets, view positions, and test rules in one line.

---

## 📁 Project Architecture

```
polymarket/
├── config/
│   ├── settings.py             # Loads .env, validates limits & endpoints
│   └── trading_rules.json      # Your custom trading rules (editable anytime)
├── src/
│   ├── bot.py                  # Main 24/7 continuous daemon loop
│   ├── polymarket_client.py    # Polymarket CLOB client (Live + Paper trading)
│   ├── market_finder.py        # Gamma API market search and discovery
│   ├── rule_engine.py          # Evaluates trading conditions against live order books
│   ├── risk_manager.py         # Position size and exposure guardrails
│   └── notifications.py        # Telegram & Discord mobile alerts
├── deploy/
│   ├── Dockerfile              # Container image for 24/7 cloud runtime
│   ├── docker-compose.yml      # 1-command cloud background orchestration
│   ├── polymarket-bot.service  # Linux systemd daemon configuration
│   └── setup_cloud.sh          # 1-click VPS installation script
├── logs/                       # Local execution logs & simulated portfolio
├── .env                        # Local configuration & credentials
├── .env.example                # Template for configuration
├── requirements.txt            # Python dependencies
└── run.py                      # Main CLI interface
```

---

## 🚀 Quick Start (Testing Locally)

### 1. View Bot Status & Paper Portfolio
```bash
python run.py --status
```

### 2. Search Active Polymarket Markets & Token IDs
```bash
python run.py --search "election"
python run.py --search "fed"
```
*Copy the `Slug` or `Token ID` to use in your trading rules.*

### 3. Test Rules in Dry-Run Mode (Single Pass)
```bash
python run.py --test-rules
```

### 4. Run the Continuous Bot Loop
```bash
python run.py
```

---

## ⚙️ Customizing Trading Rules

All rules live inside [`config/trading_rules.json`](file:///c:/Users/OHENEBA/Downloads/polymarket/config/trading_rules.json). You can edit them at any time without changing any Python code.

### Example 1: Dip Buyer / Price Threshold
```json
{
  "id": "rule_presidential_dip",
  "name": "Dip Buyer for Target Market",
  "enabled": true,
  "type": "price_threshold",
  "market_filter": {
    "slug": "will-jd-vance-win-the-2028-us-presidential-election"
  },
  "params": {
    "outcome": "Yes",
    "action": "BUY",
    "trigger_price_below": 0.15,
    "take_profit_price": 0.35,
    "stop_loss_price": 0.08,
    "order_amount_usd": 20.0
  }
}
```

### Example 2: Binary Arbitrage Scanner
```json
{
  "id": "rule_binary_arbitrage",
  "name": "Binary Market Mispricing Arbitrage",
  "enabled": true,
  "type": "binary_arbitrage",
  "market_filter": {
    "min_volume_24hr": 50000,
    "max_markets_to_scan": 10
  },
  "params": {
    "max_combined_cost": 0.98,
    "min_expected_profit_pct": 2.0,
    "allocation_per_leg_usd": 15.0
  }
}
```

---

## ☁️ Deploying to the Cloud for 24/7 Execution

Since your local internet is unreliable, running this on a cloud Virtual Private Server (VPS) ensures **99.99% uptime, zero dropped connections, and sub-millisecond network latency**.

### Step 1: Choose a Cloud Provider ($4 - $6 / month)
Create a small Linux VPS (Ubuntu 22.04 or 24.04, 1GB RAM is plenty) on:
- **DigitalOcean** (Droplet)
- **Hetzner** (Cloud Server)
- **AWS EC2** (t3.micro or t4g.small)
- **Railway** / **Render**

> **IMPORTANT GEOLOCATION NOTE:** Polymarket restricts IP addresses located in the United States. When spinning up your cloud VPS, **select a datacenter region outside the US** (e.g. Frankfurt, Amsterdam, London, Singapore, or Tokyo).

### Step 2: Upload Files to Your Cloud Server
From your machine, copy the project folder to your server:
```bash
scp -r c:\Users\OHENEBA\Downloads\polymarket root@<YOUR_SERVER_IP>:/root/polymarket
```
Or push to a private GitHub repository and `git clone` it on the server.

### Step 3: Run the Cloud Setup Script
SSH into your server:
```bash
ssh root@<YOUR_SERVER_IP>
cd /root/polymarket
chmod +x deploy/setup_cloud.sh
./deploy/setup_cloud.sh
```

### Step 4: Run 24/7 with Docker (Recommended)
```bash
# Start bot in background
docker compose -f deploy/docker-compose.yml up -d --build

# View live 24/7 logs
docker logs -f polymarket-24-7-bot

# Stop bot
docker compose -f deploy/docker-compose.yml down
```

---

## 🔒 Switching from Dry-Run to Live Trading

When you are satisfied with your rules after testing in paper trading mode:

1. Open your `.env` file on the cloud server (`nano .env`).
2. Set:
   ```env
   DRY_RUN=false
   POLYGON_PRIVATE_KEY=your_actual_polygon_private_key
   ```
3. Ensure your Polygon wallet has:
   - **USDC.e / USDC** on Polygon network (to fund trades).
   - A tiny amount of **POL/MATIC** (~0.5 POL is enough for thousands of transactions).
4. Restart the bot:
   ```bash
   docker compose -f deploy/docker-compose.yml restart
   ```

---

## 📱 Mobile Alerts (Telegram / Discord)

To get instant notifications on your phone whenever a trade executes:

1. **Telegram**:
   - Create a bot with `@BotFather` on Telegram to get your `TELEGRAM_BOT_TOKEN`.
   - Message your bot or `@userinfobot` to get your `TELEGRAM_CHAT_ID`.
   - Paste them into `.env`.
2. **Discord**:
   - Create a Webhook in any Discord channel (Channel Settings -> Integrations -> Webhooks).
   - Paste the webhook URL into `DISCORD_WEBHOOK_URL` in `.env`.
