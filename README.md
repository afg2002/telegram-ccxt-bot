# 🤖 Telegram CCXT Trading Bot

A powerful, interactive Telegram trading bot with real-time cryptocurrency prices, arbitrage detection, technical analysis signals, and price alerts — all powered by CCXT.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CCXT](https://img.shields.io/badge/CCXT-Latest-green.svg)](https://github.com/ccxt/ccxt)

---

## ✨ Features

### 📊 Real-Time Prices
- Fetch live prices from multiple exchanges (Binance, Bybit, OKX, Gate.io, KuCoin, etc.)
- Compare prices across exchanges
- Average price calculation with 24h change indicators
- Price cache fallback when exchanges are down

### 💰 Arbitrage Scanner
- Scan **all USDT pairs** across exchanges
- Detect price spread opportunities
- Configurable threshold (default: 0.5%)
- Auto-scan mode with continuous monitoring
- Top opportunities sorted by spread percentage

### 📈 Trading Signals (Technical Analysis)
Generate buy/sell signals based on multiple indicators:
- **RSI** (Relative Strength Index) — Overbought/Oversold detection
- **MACD** (Moving Average Convergence Divergence) — Trend momentum
- **Volume Analysis** — Unusual volume detection
- **MA Cross** — EMA 9/21 crossover signals
- **Bollinger Bands** — Price position within bands
- **Stochastic** — Momentum oscillator
- **ADX** (Average Directional Index) — Trend strength

Signal Output:
- 🟢🟢 **STRONG BUY** / 🟢 **BUY** / ⚪ **NEUTRAL** / 🔴 **SELL** / 🔴🔴 **STRONG SELL**
- Confidence percentage based on indicator agreement

### 🔔 Price Alerts
- Set alerts for price targets (above/below)
- Background monitoring with automatic notifications
- View and manage your active alerts

### ⚙️ Interactive UI
- Inline keyboard navigation
- Typing/loading indicators
- Button-based quick actions
- Configurable settings via bot commands

### 🛡️ Reliability Features
- **Health Tracking** — Monitor exchange UP/DOWN status
- **Circuit Breaker** — Auto-disable failing exchanges (configurable cooldown)
- **Price Cache** — Fallback to last known prices
- **Structured Logging** — Easy debugging and monitoring

---

## 📸 Screenshots

### Main Menu
```
🤖 Trading Bot Active!

[📊 Prices] [💰 Arbitrage]
[📈 Signals] [🔔 Alerts]
[⚙️ Settings] [📊 Status]
      [❓ Help]
```

### Signal Example
```
🟢🟢 STRONG BUY
📊 Confidence: 85.0%
💰 Price: $66,871.10
⏱️ Timeframe: 1h

Indicators:
  🟢🟢 RSI: 28.50 (STRONG_BUY)
  🟢 MACD: 124.06 (BUY)
  🟢 Volume: 2.15 (BUY)
  🟢 MA Cross: 96.13 (BUY)
  ⚪ Bollinger: 15.32 (BUY)
  🟢 Stochastic: 22.50 (STRONG_BUY)
  ⚪ ADX: 45.20 (NEUTRAL)
```

### Arbitrage Example
```
📊 Arbitrage Opportunities (>0.5%)
Found: 5 | Showing: 5
───────────────────────────

🟢 BTC/USDT
  📥 Buy: gate @ $66,850.00
  📤 Sell: binance @ $67,150.00
  💰 Spread: 0.45%
  ⏱️ 14:32:15

🟡 ETH/USDT
  📥 Buy: gate @ $2,018.50
  📤 Sell: okx @ $2,025.30
  💰 Spread: 0.34%
  ⏱️ 14:32:16
```

---

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- (Optional) Exchange API keys for trading features

### Step 1: Clone Repository
```bash
git clone https://github.com/afg2002/telegram-ccxt-bot.git
cd telegram-ccxt-bot
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment
```bash
cp .env.example .env
```

Edit `.env` with your settings:
```env
# Required: Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Optional: Exchange API Keys (for trading features)
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET=your_binance_secret

BYBIT_API_KEY=your_bybit_api_key
BYBIT_SECRET=your_bybit_secret

OKX_API_KEY=your_okx_api_key
OKX_SECRET=your_okx_secret
OKX_PASSWORD=your_okx_password

# Bot Settings
PRICE_UPDATE_INTERVAL=30
ARBITRAGE_THRESHOLD=0.5
ALERT_CHECK_INTERVAL=10
MAX_ARB_PAIRS=100
SIGNAL_TIMEFRAME=1h

# Circuit Breaker Settings
CIRCUIT_BREAKER_THRESHOLD=3
CIRCUIT_BREAKER_COOLDOWN=900

# Security (comma-separated Telegram user IDs)
ALLOWED_USERS=123456789,987654321
```

### Step 4: Get Telegram Bot Token
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the bot token
4. Paste it in `.env` as `TELEGRAM_BOT_TOKEN`

### Step 5: Get Your Chat ID
1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy your user ID
3. Paste it in `.env` as `TELEGRAM_CHAT_ID` and in `ALLOWED_USERS`

### Step 6: Run the Bot
```bash
python bot.py
```

---

## 📱 Bot Commands

### Core Commands
| Command | Description |
|---------|-------------|
| `/start` | Start bot with interactive main menu |
| `/menu` | Show quick navigation menu |
| `/help` | Show help and command list |
| `/status` | View bot status and exchange health |

### Price Commands
| Command | Description |
|---------|-------------|
| `/price BTC/USDT` | Get price for a specific pair |
| `/price` | Show pair selection menu |

### Signal Commands
| Command | Description |
|---------|-------------|
| `/signal BTC/USDT` | Get trading signal for a pair |
| `/signal` | Show signal menu for all pairs |

### Arbitrage Commands
| Command | Description |
|---------|-------------|
| `/arb` | Open arbitrage scanner menu |

### Alert Commands
| Command | Description |
|---------|-------------|
| `/alert BTC/USDT above 50000` | Set price alert above target |
| `/alert BTC/USDT below 45000` | Set price alert below target |
| `/alerts` | View your active alerts |

### Settings Commands
| Command | Description |
|---------|-------------|
| `/set` | View current settings |
| `/set arb_threshold 0.3` | Set arbitrage threshold |
| `/set update_interval 60` | Set price update interval |
| `/set max_pairs 200` | Set max pairs to scan |
| `/set signal_tf 4h` | Set signal timeframe |

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | - | Telegram bot token (required) |
| `TELEGRAM_CHAT_ID` | - | Your Telegram user ID (required) |
| `PRICE_UPDATE_INTERVAL` | `30` | Seconds between price updates |
| `ARBITRAGE_THRESHOLD` | `0.5` | Minimum spread % for arbitrage |
| `ALERT_CHECK_INTERVAL` | `10` | Seconds between alert checks |
| `MAX_ARB_PAIRS` | `100` | Max pairs to scan for arbitrage |
| `SIGNAL_TIMEFRAME` | `1h` | Timeframe for signals (1m/5m/15m/1h/4h/1d) |
| `CIRCUIT_BREAKER_THRESHOLD` | `3` | Failures before marking exchange DOWN |
| `CIRCUIT_BREAKER_COOLDOWN` | `900` | Seconds before retry (15 min) |
| `ALLOWED_USERS` | - | Comma-separated Telegram user IDs |

### Supported Exchanges
- Binance
- Bybit
- OKX
- Gate.io
- KuCoin
- Bitget
- Huobi
- Kraken

### Trading Pairs
Default tracked pairs (customizable in `config.py`):
```
BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, XRP/USDT
DOGE/USDT, ADA/USDT, AVAX/USDT, DOT/USDT, MATIC/USDT
```

---

## 🏗️ Architecture

```
telegram-ccxt-bot/
├── bot.py                    # Main bot with command handlers & UI
├── config.py                 # Configuration management
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── .env                      # Your configuration (git-ignored)
├── modules/
│   ├── __init__.py
│   ├── exchange_manager.py   # CCXT exchange interactions & health
│   ├── arbitrage_scanner.py  # Arbitrage detection
│   ├── alert_manager.py      # Price alert system
│   └── signal_analyzer.py    # Technical analysis & signals
└── README.md
```

### Module Overview

**`exchange_manager.py`**
- Multi-exchange management via CCXT
- Health tracking (UP/DOWN/UNKNOWN)
- Circuit breaker for failing exchanges
- Price caching for fallback
- Sync/async wrapper for all operations

**`arbitrage_scanner.py`**
- Scan all USDT pairs or specific symbols
- Detect price spreads across exchanges
- Continuous auto-scan mode
- Opportunity history and statistics

**`alert_manager.py`**
- Price alerts (above/below targets)
- Background monitoring
- User-specific alert management
- Automatic notifications

**`signal_analyzer.py`**
- 7 technical indicators
- Weighted signal calculation
- Confidence scoring
- Multiple timeframe support

---

## 🔧 Advanced Usage

### Adding More Exchanges
Edit `config.py`:
```python
EXCHANGE_CONFIGS = {
    "binance": {...},
    "bybit": {...},
    # Add more exchanges here
    "bitget": {"enableRateLimit": True},
    "kraken": {"enableRateLimit": True},
}
```

### Custom Trading Pairs
Edit `config.py`:
```python
TRADING_PAIRS = [
    "BTC/USDT",
    "ETH/USDT",
    # Add your pairs here
    "LINK/USDT",
    "UNI/USDT",
]
```

### Adjusting Signal Weights
Edit `modules/signal_analyzer.py`:
```python
self.weights = {
    "RSI": 1.5,        # Higher = more important
    "MACD": 1.5,
    "Volume": 1.0,
    "MA_Cross": 1.2,
    "Bollinger": 1.0,
    "Stochastic": 1.0,
    "ADX": 0.8,
}
```

---

## 🐛 Troubleshooting

### SSL Certificate Errors
If you see SSL errors (common in some regions):
- The bot automatically handles SSL issues
- Gate.io is recommended for regions with Binance/OKX blocked
- Consider using a VPN for full exchange access

### Exchange Not Connecting
- Check if the exchange is accessible from your region
- Verify API keys are correct (if using authenticated endpoints)
- Check the health status with `/status`

### Bot Not Responding
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Check if your user ID is in `ALLOWED_USERS`
- Look at console logs for error messages

### No Arbitrage Opportunities
- Lower the threshold: `/set arb_threshold 0.2`
- Increase max pairs: `/set max_pairs 200`
- Check if multiple exchanges are healthy

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

**This bot is for educational and informational purposes only.**

- Cryptocurrency trading involves significant risk
- Always do your own research (DYOR)
- Never invest more than you can afford to lose
- The signals provided are not financial advice
- Past performance does not guarantee future results
- Use at your own risk

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📧 Support

If you have any questions or need help:
- Open an issue on GitHub
- Contact via Telegram

---

## 🙏 Acknowledgments

- [CCXT](https://github.com/ccxt/ccxt) - Cryptocurrency trading library
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- All the amazing open-source contributors

---

**Made with ❤️ for the crypto community**
