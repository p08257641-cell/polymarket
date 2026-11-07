# 🚀 Deploying 100% Free to Render (Frankfurt, Non-US)

Render provides a **100% Free Tier with NO credit card required** and has a data center in **Frankfurt, Germany** (outside the US, which bypasses Polymarket's geo-blocking).

---

## 3-Minute Step-by-Step Instructions

### Step 1: Push Code to GitHub
1. Open your browser and go to [github.com/new](https://github.com/new).
2. Create a **Private Repository** called `polymarket-bot`.
3. In your local terminal inside `c:\Users\OHENEBA\Downloads\polymarket`, run:
   ```bash
   git init
   git add .
   git commit -m "Initial commit for Polymarket cloud bot"
   git branch -M main
   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/polymarket-bot.git
   git push -u origin main
   ```

---

### Step 2: Create a Free Account on Render
1. Go to [render.com](https://render.com) and click **Sign Up** (choose **Sign in with GitHub** — no credit card needed).
2. On your dashboard, click the blue **New +** button in the top right.
3. Select **Web Service**.
4. Choose **Build and deploy from a Git repository** -> Click **Next**.
5. Connect your `polymarket-bot` repository.

---

### Step 3: Configure Settings (Takes 30 seconds)
Render will ask for a few settings:
* **Name**: `polymarket-24-7-bot`
* **Region**: Select **Frankfurt (EU - Central)** *(Crucial so Polymarket doesn't geo-block you!)*
* **Branch**: `main`
* **Runtime**: `Python 3`
* **Build Command**: `pip install -r requirements.txt`
* **Start Command**: `python run.py`
* **Instance Type**: Select **Free** ($0 / month)

Scroll down to **Environment Variables** and add:
* `DRY_RUN`: `true`
* `DAILY_PROFIT_TARGET_USD`: `3.0`
* `ENABLE_HEALTH_SERVER`: `true`
*(When you are ready for real funds, you can add your `POLYGON_PRIVATE_KEY` here).*

Click **Create Web Service**!

---

### Step 4: Keep It Running 24/7 for Free (No Sleeping)
Render free services spin down after 15 minutes of inactivity unless pinged. Because your bot includes a built-in health server on `/health`:

1. Copy your new Render app URL (e.g., `https://polymarket-24-7-bot.onrender.com`).
2. Go to [UptimeRobot.com](https://uptimerobot.com) (100% free forever) and sign up.
3. Click **Add New Monitor**:
   * **Monitor Type**: `HTTP(s)`
   * **Friendly Name**: `Polymarket Bot 24/7`
   * **URL**: `https://polymarket-24-7-bot.onrender.com/health`
   * **Monitoring Interval**: `Every 10 minutes`
4. Click **Create Monitor**.

🎉 **Your bot will now run 24 hours a day, 7 days a week in Frankfurt, Germany completely free of charge!**
