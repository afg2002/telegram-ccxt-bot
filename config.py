"""Configuration module for Telegram Trading Bot."""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def _build_exchange_config(api_key: str, secret: str, **extra) -> dict:
    """Build exchange config - only include credentials if actually set."""
    config = {"enableRateLimit": True}

    # Only add credentials if they're non-empty strings
    if api_key and api_key.strip():
        config["apiKey"] = api_key
    if secret and secret.strip():
        config["secret"] = secret

    # Add any extra params (like password for OKX)
    for k, v in extra.items():
        if v and str(v).strip():
            config[k] = v

    return config


# Exchange API Keys - credentials only added if actually provided
EXCHANGE_CONFIGS = {
    "binance": {
        **_build_exchange_config(
            os.getenv("BINANCE_API_KEY", ""),
            os.getenv("BINANCE_SECRET", ""),
        ),
        "options": {"defaultType": "spot"},
    },
    "bybit": _build_exchange_config(
        os.getenv("BYBIT_API_KEY", ""),
        os.getenv("BYBIT_SECRET", ""),
    ),
    "okx": _build_exchange_config(
        os.getenv("OKX_API_KEY", ""),
        os.getenv("OKX_SECRET", ""),
        password=os.getenv("OKX_PASSWORD", ""),
    ),
    # Public-only exchanges (no API keys needed for prices)
    "gate": {"enableRateLimit": True},
    "kucoin": {"enableRateLimit": True},
}

# Supported Trading Pairs
TRADING_PAIRS = [
    "BTC/USDT",
    "ETH/USDT",
    "BNB/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "DOGE/USDT",
    "ADA/USDT",
    "AVAX/USDT",
    "DOT/USDT",
    "MATIC/USDT",
]

# Bot Settings
PRICE_UPDATE_INTERVAL = int(os.getenv("PRICE_UPDATE_INTERVAL", "30"))
ARBITRAGE_THRESHOLD = float(os.getenv("ARBITRAGE_THRESHOLD", "0.5"))
ALERT_CHECK_INTERVAL = int(os.getenv("ALERT_CHECK_INTERVAL", "10"))

# Arbitrage Settings
MAX_ARB_PAIRS = int(os.getenv("MAX_ARB_PAIRS", "100"))

# Signal Settings
SIGNAL_TIMEFRAME = os.getenv("SIGNAL_TIMEFRAME", "1h")

# Circuit Breaker Settings
CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3"))
CIRCUIT_BREAKER_COOLDOWN = int(
    os.getenv("CIRCUIT_BREAKER_COOLDOWN", "900")
)  # 15 minutes

# Security
ALLOWED_USERS = [
    int(uid.strip()) for uid in os.getenv("ALLOWED_USERS", "").split(",") if uid.strip()
]

# Arbitrage Exchanges (exchanges to compare for arbitrage)
ARBITRAGE_EXCHANGES = ["binance", "bybit", "okx", "gate", "kucoin"]

# Display Settings
DECIMAL_PLACES = 8
PERCENTAGE_DECIMALS = 2
