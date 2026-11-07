import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

class Settings:
    # Mode
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").strip().lower() in ("true", "1", "yes")

    # Polygon & Wallet
    POLYGON_PRIVATE_KEY: str = os.getenv("POLYGON_PRIVATE_KEY", "").strip()
    SIGNATURE_TYPE: int = int(os.getenv("SIGNATURE_TYPE", "0"))
    POLYGON_RPC_URL: str = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com").strip()
    CHAIN_ID: int = int(os.getenv("CHAIN_ID", "137"))

    # Polymarket Hosts
    CLOB_API_URL: str = os.getenv("CLOB_API_URL", "https://clob.polymarket.com").strip().rstrip("/")
    GAMMA_API_URL: str = os.getenv("GAMMA_API_URL", "https://gamma-api.polymarket.com").strip().rstrip("/")

    # Risk Controls
    MAX_ORDER_SIZE_USD: float = float(os.getenv("MAX_ORDER_SIZE_USD", "25.0"))
    MAX_TOTAL_EXPOSURE_USD: float = float(os.getenv("MAX_TOTAL_EXPOSURE_USD", "100.0"))
    MAX_SLIPPAGE_PERCENT: float = float(os.getenv("MAX_SLIPPAGE_PERCENT", "1.5"))
    MIN_PROFIT_SPREAD: float = float(os.getenv("MIN_PROFIT_SPREAD", "0.02"))

    # Monitoring & Loop Frequency
    LOOP_INTERVAL_SECONDS: int = int(os.getenv("LOOP_INTERVAL_SECONDS", "10"))

    # Daily Profit Goal: Set to 0.0 for UNLIMITED daily profit (no daily cap)
    DAILY_PROFIT_TARGET_USD: float = float(os.getenv("DAILY_PROFIT_TARGET_USD", "0.0"))
    WEB_SERVER_PORT: int = int(os.getenv("PORT", os.getenv("WEB_SERVER_PORT", "8080")))
    ENABLE_HEALTH_SERVER: bool = os.getenv("ENABLE_HEALTH_SERVER", "true").strip().lower() in ("true", "1", "yes")

    # Notifications
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

    # File paths
    RULES_PATH: Path = BASE_DIR / "config" / "trading_rules.json"
    LOGS_DIR: Path = BASE_DIR / "logs"

    @classmethod
    def is_configured_for_live(cls) -> bool:
        if cls.DRY_RUN:
            return False
        if not cls.POLYGON_PRIVATE_KEY or cls.POLYGON_PRIVATE_KEY.startswith("0x000000"):
            return False
        return True

settings = Settings()
settings.LOGS_DIR.mkdir(exist_ok=True)
