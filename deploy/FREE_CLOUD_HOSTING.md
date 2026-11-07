# 🆓 100% Free 24/7 Cloud Hosting Guide (No Payments)

To run this bot 24/7 without paying monthly server fees, you have two proven zero-cost options that operate **outside the United States** (so Polymarket's geo-blocking does not restrict you).

---

## 🏆 Option 1: Koyeb (Recommended — Zero Cost, Fast Setup, Frankfurt EU)

[Koyeb](https://www.koyeb.com) offers a permanent Free Tier that gives you 512MB RAM and 0.1 vCPU in **Frankfurt, Germany**.

Because free cloud instances normally go to sleep if they receive no web traffic for 1 hour, **this bot includes a built-in Keep-Alive Web Server (`src/health_server.py`)** on port 8080.

### Step-by-Step Setup:
1. **Push your bot to GitHub**:
   * Create a private GitHub repository (e.g. `polymarket-bot`).
   * Push your code to GitHub.
2. **Deploy on Koyeb**:
   * Go to [koyeb.com](https://www.koyeb.com) and create a free account.
   * Click **Create App** -> Select **GitHub**.
   * Choose your repository.
   * Under **Region**, select **Frankfurt (fra)**.
   * Under **Environment Variables**, paste the contents of your `.env` file (e.g. `DRY_RUN=true`, `DAILY_PROFIT_TARGET_USD=3.0`, `PORT=8080`).
   * Click **Deploy**.
3. **Keep It Awake 24/7 for Free**:
   * Koyeb will give you a public URL (e.g., `https://polymarket-bot-yourname.koyeb.app`).
   * Go to [UptimeRobot](https://uptimerobot.com) or [cron-job.org](https://cron-job.org) (both 100% free forever).
   * Create a new HTTP monitor pointing to:  
     `https://polymarket-bot-yourname.koyeb.app/health`
   * Set monitoring interval to **every 20 minutes**.
   * **Result:** The free ping keeps your Koyeb server awake 24/7/365 without sleeping and without paying a single cent.

---

## 🛡️ Option 2: Oracle Cloud "Always Free" Linux VPS (Most Powerful)

[Oracle Cloud Infrastructure (OCI)](https://www.oracle.com/cloud/free/) provides the most generous permanent free tier in the cloud industry:
- **What you get**: 2 AMD Compute VMs (1GB RAM each) or ARM Ampere (up to 4 OCPU, 24GB RAM) **100% free forever**.
- **Location**: You can select **Frankfurt, London, Zurich, or Tokyo** as your "Home Region" during signup.
- **Why it's great**: It is a full Linux VPS with root SSH access. It never sleeps, requires no keep-alive pings, and runs Docker / systemd directly.

### Step-by-Step Setup:
1. Sign up at [oracle.com/cloud/free](https://www.oracle.com/cloud/free/). Select **Frankfurt** or **London** as your Home Region.
   *(Note: Oracle requires a credit card for identity/anti-fraud verification, but charges $0.00).*
2. Go to **Compute** -> **Instances** -> **Create Instance** (choose Ubuntu 24.04, "Always Free Eligible").
3. Connect via SSH:
   ```bash
   ssh -i your_key ubuntu@<YOUR_ORACLE_IP>
   ```
4. Clone your bot and run the 1-click cloud setup:
   ```bash
   git clone <YOUR_REPO_URL> polymarket
   cd polymarket
   chmod +x deploy/setup_cloud.sh
   sudo ./deploy/setup_cloud.sh
   docker compose -f deploy/docker-compose.yml up -d
   ```
5. Your bot is now running 24/7 in the cloud permanently for $0!
