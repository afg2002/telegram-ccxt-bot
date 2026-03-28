"""Telegram Trading Bot - Interactive UI with real-time prices, signals & arbitrage."""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.constants import ParseMode, ChatAction

import config
from modules.exchange_manager import ExchangeManager
from modules.arbitrage_scanner import ArbitrageScanner
from modules.alert_manager import AlertManager, AlertType
from modules.signal_analyzer import SignalAnalyzer, SignalType

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class TradingBot:
    """Main Telegram Trading Bot class with interactive UI."""

    def __init__(self):
        self.exchange_manager = ExchangeManager(
            config.EXCHANGE_CONFIGS,
            circuit_breaker_threshold=config.CIRCUIT_BREAKER_THRESHOLD,
            circuit_breaker_cooldown=config.CIRCUIT_BREAKER_COOLDOWN,
        )
        self.arbitrage_scanner = ArbitrageScanner(
            self.exchange_manager, config.ARBITRAGE_THRESHOLD
        )
        self.alert_manager = AlertManager()
        self.signal_analyzer = SignalAnalyzer()
        self.background_tasks: List[asyncio.Task] = []

        # Bot settings (configurable)
        self.settings = {
            "arbitrage_threshold": config.ARBITRAGE_THRESHOLD,
            "price_update_interval": config.PRICE_UPDATE_INTERVAL,
            "alert_check_interval": config.ALERT_CHECK_INTERVAL,
            "max_arb_pairs": 100,
            "signal_timeframe": "1h",
        }

    # ─────────────────────────────────────────────
    # UTILITY METHODS
    # ─────────────────────────────────────────────

    async def send_typing(self, update: Update):
        """Send typing indicator."""
        await update.effective_chat.send_action(ChatAction.TYPING)

    async def send_upload_photo(self, update: Update):
        """Send uploading photo indicator."""
        await update.effective_chat.send_action(ChatAction.UPLOAD_PHOTO)

    def get_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Get main menu inline keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📊 Prices", callback_data="menu_prices"),
                InlineKeyboardButton("💰 Arbitrage", callback_data="menu_arb"),
            ],
            [
                InlineKeyboardButton("📈 Signals", callback_data="menu_signals"),
                InlineKeyboardButton("🔔 Alerts", callback_data="menu_alerts"),
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
                InlineKeyboardButton("📊 Status", callback_data="menu_status"),
            ],
            [
                InlineKeyboardButton("❓ Help", callback_data="menu_help"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_price_keyboard(self) -> InlineKeyboardMarkup:
        """Get price menu keyboard."""
        keyboard = []
        # Add buttons for tracked pairs
        row = []
        for i, pair in enumerate(config.TRADING_PAIRS[:10]):
            symbol = pair.split("/")[0]
            row.append(InlineKeyboardButton(symbol, callback_data=f"price_{pair}"))
            if len(row) == 5:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="menu_main")])
        return InlineKeyboardMarkup(keyboard)

    def get_arb_keyboard(self) -> InlineKeyboardMarkup:
        """Get arbitrage menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🔍 Scan All Pairs", callback_data="arb_scan_all"),
                InlineKeyboardButton("📊 Scan Top 20", callback_data="arb_scan_top20"),
            ],
            [
                InlineKeyboardButton("▶️ Start Auto-Scan", callback_data="arb_start"),
                InlineKeyboardButton("⏹ Stop Auto-Scan", callback_data="arb_stop"),
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_signal_keyboard(self) -> InlineKeyboardMarkup:
        """Get signal menu keyboard."""
        keyboard = []
        row = []
        for i, pair in enumerate(config.TRADING_PAIRS[:10]):
            symbol = pair.split("/")[0]
            row.append(InlineKeyboardButton(symbol, callback_data=f"signal_{pair}"))
            if len(row) == 5:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append(
            [
                InlineKeyboardButton("📊 All Signals", callback_data="signal_all"),
            ]
        )
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="menu_main")])
        return InlineKeyboardMarkup(keyboard)

    def get_alert_keyboard(self) -> InlineKeyboardMarkup:
        """Get alert menu keyboard."""
        keyboard = [
            [InlineKeyboardButton("📋 View Alerts", callback_data="alert_view")],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Get settings menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(
                    f"🎯 Arb Threshold: {self.settings['arbitrage_threshold']}%",
                    callback_data="setting_arb_threshold",
                )
            ],
            [
                InlineKeyboardButton(
                    f"⏱️ Update Interval: {self.settings['price_update_interval']}s",
                    callback_data="setting_update_interval",
                )
            ],
            [
                InlineKeyboardButton(
                    f"📊 Max Arb Pairs: {self.settings['max_arb_pairs']}",
                    callback_data="setting_max_pairs",
                )
            ],
            [
                InlineKeyboardButton(
                    f"📈 Signal TF: {self.settings['signal_timeframe']}",
                    callback_data="setting_signal_tf",
                )
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    # ─────────────────────────────────────────────
    # AUTHORIZATION
    # ─────────────────────────────────────────────

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized."""
        if not config.ALLOWED_USERS:
            return True
        return user_id in config.ALLOWED_USERS

    async def check_auth(self, update: Update) -> bool:
        """Check authorization."""
        user_id = update.effective_user.id
        if not self.is_authorized(user_id):
            await update.message.reply_text(
                "❌ You are not authorized to use this bot."
            )
            return False
        return True

    # ─────────────────────────────────────────────
    # COMMAND HANDLERS
    # ─────────────────────────────────────────────

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with interactive menu."""
        if not await self.check_auth(update):
            return

        welcome_msg = (
            "🤖 **Trading Bot Active!**\n\n"
            "Welcome to the interactive trading bot.\n"
            "Use the buttons below to navigate:"
        )
        await update.message.reply_text(
            welcome_msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_main_menu_keyboard(),
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await self.start_command(update, context)

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command."""
        if not await self.check_auth(update):
            return

        await update.message.reply_text(
            "📋 **Main Menu**\n\nSelect an option:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_main_menu_keyboard(),
        )

    # ─────────────────────────────────────────────
    # CALLBACK HANDLER (Interactive UI)
    # ─────────────────────────────────────────────

    async def callback_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle all callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()

        if not self.is_authorized(query.from_user.id):
            await query.edit_message_text("❌ Unauthorized")
            return

        data = query.data

        # Main menu navigation
        if data == "menu_main":
            await query.edit_message_text(
                "📋 **Main Menu**\n\nSelect an option:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_main_menu_keyboard(),
            )
        elif data == "menu_prices":
            await query.edit_message_text(
                "📊 **Select a pair to view price:**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_price_keyboard(),
            )
        elif data == "menu_arb":
            await query.edit_message_text(
                "💰 **Arbitrage Scanner**\n\nSelect an action:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_arb_keyboard(),
            )
        elif data == "menu_signals":
            await query.edit_message_text(
                "📈 **Trading Signals**\n\nSelect a pair:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_signal_keyboard(),
            )
        elif data == "menu_alerts":
            await self._handle_alert_view(query)
        elif data == "menu_settings":
            await query.edit_message_text(
                "⚙️ **Settings**\n\nCurrent configuration:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_settings_keyboard(),
            )
        elif data == "menu_status":
            await self._handle_status(query)
        elif data == "menu_help":
            await self._handle_help(query)

        # Price callbacks
        elif data.startswith("price_"):
            symbol = data.replace("price_", "")
            await self._handle_price_callback(query, symbol)

        # Arbitrage callbacks
        elif data == "arb_scan_all":
            await self._handle_arb_scan(query, all_pairs=True)
        elif data == "arb_scan_top20":
            await self._handle_arb_scan(query, all_pairs=False)
        elif data == "arb_start":
            await self._handle_arb_start(query)
        elif data == "arb_stop":
            await self._handle_arb_stop(query)

        # Signal callbacks
        elif data.startswith("signal_"):
            if data == "signal_all":
                await self._handle_all_signals(query)
            else:
                symbol = data.replace("signal_", "")
                await self._handle_signal_callback(query, symbol)

        # Alert callbacks
        elif data == "alert_view":
            await self._handle_alert_view(query)

        # Settings callbacks
        elif data.startswith("setting_"):
            await query.edit_message_text(
                "⚙️ **Settings**\n\nTo change settings, use:\n"
                "/set `<setting> <value>`\n\n"
                "Available settings:\n"
                "• `arb_threshold` - Arbitrage threshold %\n"
                "• `update_interval` - Price update interval (s)\n"
                "• `max_pairs` - Max pairs to scan\n"
                "• `signal_tf` - Signal timeframe (1m/5m/15m/1h/4h/1d)",
                parse_mode=ParseMode.MARKDOWN,
            )

    async def _handle_price_callback(self, query: CallbackQuery, symbol: str):
        """Handle price button callback."""
        await query.edit_message_text(f"⏳ Fetching {symbol} price...")

        tickers = await self.exchange_manager.fetch_all_tickers([symbol])

        if not tickers.get(symbol):
            cached = self.exchange_manager.get_cached_price(symbol)
            if cached:
                msg = (
                    f"⚠️ No live data for {symbol}\n\n"
                    f"📦 Cached: ${cached['price']:,.2f}\n"
                    f"📡 Source: {cached['source']}"
                )
            else:
                msg = f"❌ Could not fetch price for {symbol}"
            await query.edit_message_text(msg, reply_markup=self.get_price_keyboard())
            return

        exchange_prices = tickers[symbol]
        prices = []
        for exchange, ticker in exchange_prices.items():
            if exchange.startswith("_"):
                continue
            last = ticker.get("last", 0)
            change = ticker.get("change_24h", 0)
            change_emoji = "🟢" if change and change >= 0 else "🔴"
            prices.append(
                f"• **{exchange}**: ${last:,.2f} {change_emoji} {change:+.2f}%"
            )

        all_prices = [
            t.get("last", 0)
            for e, t in exchange_prices.items()
            if not e.startswith("_") and t.get("last")
        ]
        avg_price = sum(all_prices) / len(all_prices) if all_prices else 0

        msg = (
            f"💰 **{symbol}** Price\n"
            f"{'─' * 25}\n\n" + "\n".join(prices) + f"\n\n📊 Avg: **${avg_price:,.2f}**"
        )
        await query.edit_message_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_price_keyboard(),
        )

    async def _handle_arb_scan(self, query: CallbackQuery, all_pairs: bool = False):
        """Handle arbitrage scan callback."""
        await query.edit_message_text(
            "🔍 Scanning for arbitrage opportunities...\n"
            f"Mode: {'All pairs' if all_pairs else 'Top 20'}"
        )

        if all_pairs:
            opportunities = await self.arbitrage_scanner.scan(
                symbols=None, max_pairs=self.settings["max_arb_pairs"]
            )
        else:
            opportunities = await self.arbitrage_scanner.scan(
                symbols=config.TRADING_PAIRS[:20]
            )

        msg = self.arbitrage_scanner.format_opportunities(opportunities, max_display=10)
        await query.edit_message_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_arb_keyboard(),
        )

    async def _handle_arb_start(self, query: CallbackQuery):
        """Handle start auto-scan callback."""
        if self.background_tasks:
            await query.edit_message_text(
                "⚠️ Auto-scan already running!",
                reply_markup=self.get_arb_keyboard(),
            )
            return

        task = asyncio.create_task(
            self.arbitrage_scanner.continuous_scan(
                symbols=None,
                interval=self.settings["price_update_interval"],
                callback=self._arb_callback,
                max_pairs=self.settings["max_arb_pairs"],
            )
        )
        self.background_tasks.append(task)

        await query.edit_message_text(
            f"✅ Auto-scan started!\n\n"
            f"📊 Interval: {self.settings['price_update_interval']}s\n"
            f"🎯 Threshold: {self.settings['arbitrage_threshold']}%\n"
            f"📦 Max pairs: {self.settings['max_arb_pairs']}",
            reply_markup=self.get_arb_keyboard(),
        )

    async def _handle_arb_stop(self, query: CallbackQuery):
        """Handle stop auto-scan callback."""
        for task in self.background_tasks:
            task.cancel()
        self.background_tasks.clear()

        await query.edit_message_text(
            "🛑 Auto-scan stopped.",
            reply_markup=self.get_arb_keyboard(),
        )

    async def _arb_callback(self, opportunities):
        """Callback for arbitrage opportunities (background task)."""
        if opportunities:
            logger.info(f"[ARB] Found {len(opportunities)} opportunities")

    async def _handle_signal_callback(self, query: CallbackQuery, symbol: str):
        """Handle signal button callback."""
        await query.edit_message_text(f"⏳ Analyzing {symbol}...")

        # Fetch OHLCV data
        exchange_name = (
            self.exchange_manager.get_healthy_exchanges()[0]
            if self.exchange_manager.get_healthy_exchanges()
            else None
        )
        if not exchange_name:
            await query.edit_message_text(
                "❌ No healthy exchanges available",
                reply_markup=self.get_signal_keyboard(),
            )
            return

        exchange = self.exchange_manager.get_exchange(exchange_name)
        if not exchange:
            await query.edit_message_text(
                "❌ Exchange not available",
                reply_markup=self.get_signal_keyboard(),
            )
            return

        try:
            # Fetch OHLCV in thread
            import asyncio

            loop = asyncio.get_event_loop()
            ohlcv = await loop.run_in_executor(
                None,
                lambda: exchange.fetch_ohlcv(
                    symbol, self.settings["signal_timeframe"], limit=100
                ),
            )

            if not ohlcv:
                await query.edit_message_text(
                    f"❌ No data available for {symbol}",
                    reply_markup=self.get_signal_keyboard(),
                )
                return

            signal = self.signal_analyzer.analyze(
                symbol=symbol,
                ohlcv=ohlcv,
                timeframe=self.settings["signal_timeframe"],
            )

            if signal:
                await query.edit_message_text(
                    signal.to_message(),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self.get_signal_keyboard(),
                )
            else:
                await query.edit_message_text(
                    f"❌ Could not generate signal for {symbol}",
                    reply_markup=self.get_signal_keyboard(),
                )

        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            await query.edit_message_text(
                f"❌ Error: {str(e)}",
                reply_markup=self.get_signal_keyboard(),
            )

    async def _handle_all_signals(self, query: CallbackQuery):
        """Handle all signals callback."""
        await query.edit_message_text("⏳ Analyzing all pairs...")

        exchange_name = (
            self.exchange_manager.get_healthy_exchanges()[0]
            if self.exchange_manager.get_healthy_exchanges()
            else None
        )
        if not exchange_name:
            await query.edit_message_text(
                "❌ No healthy exchanges available",
                reply_markup=self.get_signal_keyboard(),
            )
            return

        exchange = self.exchange_manager.get_exchange(exchange_name)
        if not exchange:
            await query.edit_message_text(
                "❌ Exchange not available",
                reply_markup=self.get_signal_keyboard(),
            )
            return

        import asyncio

        signals = []
        for pair in config.TRADING_PAIRS[:10]:  # Limit to 10 for performance
            try:
                loop = asyncio.get_event_loop()
                ohlcv = await loop.run_in_executor(
                    None,
                    lambda p=pair: exchange.fetch_ohlcv(
                        p, self.settings["signal_timeframe"], limit=100
                    ),
                )
                if ohlcv:
                    signal = self.signal_analyzer.analyze(
                        symbol=pair,
                        ohlcv=ohlcv,
                        timeframe=self.settings["signal_timeframe"],
                    )
                    if signal:
                        signals.append(signal)
            except Exception as e:
                logger.error(f"Error analyzing {pair}: {e}")

        if signals:
            msg = self.signal_analyzer.format_signal_summary(signals)
            await query.edit_message_text(
                msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_signal_keyboard(),
            )
        else:
            await query.edit_message_text(
                "❌ No signals available",
                reply_markup=self.get_signal_keyboard(),
            )

    async def _handle_alert_view(self, query: CallbackQuery):
        """Handle view alerts callback."""
        msg = self.alert_manager.format_user_alerts(query.from_user.id)
        await query.edit_message_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_alert_keyboard(),
        )

    async def _handle_status(self, query: CallbackQuery):
        """Handle status callback."""
        exchanges = self.exchange_manager.get_available_exchanges()
        healthy = self.exchange_manager.get_healthy_exchanges()
        arb_stats = self.arbitrage_scanner.get_statistics()
        active_alerts = self.alert_manager.get_active_count()

        health_map = self.exchange_manager.get_health_map()
        health_lines = []
        for name, health in health_map.items():
            status_emoji = "🟢" if health["status"] == "UP" else "🔴"
            failures = health.get("failures", 0)
            health_lines.append(f"  {status_emoji} {name}: {health['status']}")

        msg = (
            f"🤖 **Bot Status**\n"
            f"{'─' * 25}\n\n"
            f"📡 Exchanges: {', '.join(exchanges)}\n"
            f"✅ Healthy: {', '.join(healthy) if healthy else 'None'}\n"
            f"📊 Tracked: {len(config.TRADING_PAIRS)} pairs\n"
            f"🔔 Alerts: {active_alerts}\n"
            f"🔄 Scanning: {'Yes' if self.background_tasks else 'No'}\n\n"
            f"💚 **Health**:\n" + "\n".join(health_lines) + "\n\n"
            f"📈 **Arb Stats**:\n"
            f"  Found: {arb_stats.get('total_opportunities', 0)}\n"
            f"  Max: {arb_stats.get('max_spread', 0):.2f}%"
        )
        await query.edit_message_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]
            ),
        )

    async def _handle_help(self, query: CallbackQuery):
        """Handle help callback."""
        help_msg = (
            "❓ **Help**\n"
            f"{'─' * 25}\n\n"
            "**Commands:**\n"
            "/start - Main menu\n"
            "/menu - Quick menu\n"
            "/price `<symbol>` - Get price\n"
            "/signal `<symbol>` - Get signal\n"
            "/arb - Scan arbitrage\n"
            "/alert `<symbol> above|below <price>` - Set alert\n"
            "/set `<setting> <value>` - Change setting\n"
            "/status - Bot status\n\n"
            "**Interactive Buttons:**\n"
            "Use inline buttons for quick actions!"
        )
        await query.edit_message_text(
            help_msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]
            ),
        )

    # ─────────────────────────────────────────────
    # TEXT COMMAND HANDLERS
    # ─────────────────────────────────────────────

    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /price <symbol> command."""
        if not await self.check_auth(update):
            return

        if not context.args:
            await update.message.reply_text(
                "📊 **Select a pair:**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_price_keyboard(),
            )
            return

        symbol = context.args[0].upper()
        await self.send_typing(update)

        tickers = await self.exchange_manager.fetch_all_tickers([symbol])

        if not tickers.get(symbol):
            cached = self.exchange_manager.get_cached_price(symbol)
            if cached:
                await update.message.reply_text(
                    f"⚠️ No live data for {symbol}\n"
                    f"📦 Cached: ${cached['price']:,.2f} ({cached['source']})",
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await update.message.reply_text(
                    f"❌ Could not fetch price for {symbol}"
                )
            return

        exchange_prices = tickers[symbol]
        prices = []
        for exchange, ticker in exchange_prices.items():
            if exchange.startswith("_"):
                continue
            last = ticker.get("last", 0)
            change = ticker.get("change_24h", 0)
            change_emoji = "🟢" if change and change >= 0 else "🔴"
            prices.append(
                f"• **{exchange}**: ${last:,.2f} {change_emoji} {change:+.2f}%"
            )

        all_prices = [
            t.get("last", 0)
            for e, t in exchange_prices.items()
            if not e.startswith("_") and t.get("last")
        ]
        avg_price = sum(all_prices) / len(all_prices) if all_prices else 0

        msg = (
            f"💰 **{symbol}** Price\n"
            f"{'─' * 25}\n\n"
            + "\n".join(prices)
            + f"\n\n📊 Avg: **${avg_price:,.2f}**\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signal <symbol> command."""
        if not await self.check_auth(update):
            return

        if not context.args:
            await update.message.reply_text(
                "📈 **Select a pair for signal:**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_signal_keyboard(),
            )
            return

        symbol = context.args[0].upper()
        await self.send_typing(update)

        exchange_name = (
            self.exchange_manager.get_healthy_exchanges()[0]
            if self.exchange_manager.get_healthy_exchanges()
            else None
        )
        if not exchange_name:
            await update.message.reply_text("❌ No healthy exchanges available")
            return

        exchange = self.exchange_manager.get_exchange(exchange_name)
        if not exchange:
            await update.message.reply_text("❌ Exchange not available")
            return

        try:
            loop = asyncio.get_event_loop()
            ohlcv = await loop.run_in_executor(
                None,
                lambda: exchange.fetch_ohlcv(
                    symbol, self.settings["signal_timeframe"], limit=100
                ),
            )

            if not ohlcv:
                await update.message.reply_text(f"❌ No data available for {symbol}")
                return

            signal = self.signal_analyzer.analyze(
                symbol=symbol,
                ohlcv=ohlcv,
                timeframe=self.settings["signal_timeframe"],
            )

            if signal:
                await update.message.reply_text(
                    signal.to_message(),
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await update.message.reply_text(
                    f"❌ Could not generate signal for {symbol}"
                )

        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def arb_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /arb command."""
        if not await self.check_auth(update):
            return

        await update.message.reply_text(
            "💰 **Arbitrage Scanner**\n\nSelect an action:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_arb_keyboard(),
        )

    async def set_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /set <setting> <value> command."""
        if not await self.check_auth(update):
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                "⚙️ **Current Settings**\n\n"
                + "\n".join(f"• {k}: {v}" for k, v in self.settings.items())
                + "\n\nUsage: `/set <setting> <value>`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        setting = context.args[0].lower()
        value = context.args[1]

        valid_settings = {
            "arb_threshold": ("arbitrage_threshold", float),
            "update_interval": ("price_update_interval", int),
            "alert_interval": ("alert_check_interval", int),
            "max_pairs": ("max_arb_pairs", int),
            "signal_tf": ("signal_timeframe", str),
        }

        if setting not in valid_settings:
            await update.message.reply_text(
                f"❌ Unknown setting: {setting}\n\n"
                f"Valid settings: {', '.join(valid_settings.keys())}"
            )
            return

        key, type_func = valid_settings[setting]
        try:
            typed_value = type_func(value)
            self.settings[key] = typed_value

            # Update arbitrage scanner threshold if changed
            if key == "arbitrage_threshold":
                self.arbitrage_scanner.threshold = typed_value

            await update.message.reply_text(
                f"✅ Setting updated!\n\n**{key}**: {typed_value}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except ValueError:
            await update.message.reply_text(f"❌ Invalid value for {setting}")

    async def alert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alert command."""
        if not await self.check_auth(update):
            return

        if len(context.args) < 3:
            await update.message.reply_text(
                "🔔 **Alerts**\n\n"
                "Usage: `/alert BTC/USDT above 50000`\n"
                "or: `/alert BTC/USDT below 45000`\n\n"
                "Or use the menu:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_alert_keyboard(),
            )
            return

        symbol = context.args[0].upper()
        alert_type_str = context.args[1].lower()

        try:
            target_value = float(context.args[2])
        except ValueError:
            await update.message.reply_text("❌ Invalid price value")
            return

        if alert_type_str == "above":
            alert_type = AlertType.PRICE_ABOVE
        elif alert_type_str == "below":
            alert_type = AlertType.PRICE_BELOW
        else:
            await update.message.reply_text("❌ Use 'above' or 'below'")
            return

        alert = self.alert_manager.create_alert(
            user_id=update.effective_user.id,
            symbol=symbol,
            alert_type=alert_type,
            target_value=target_value,
        )

        await update.message.reply_text(
            f"✅ Alert created!\n\n{alert.to_message()}",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        if not await self.check_auth(update):
            return

        exchanges = self.exchange_manager.get_available_exchanges()
        healthy = self.exchange_manager.get_healthy_exchanges()
        arb_stats = self.arbitrage_scanner.get_statistics()
        active_alerts = self.alert_manager.get_active_count()

        health_map = self.exchange_manager.get_health_map()
        health_lines = []
        for name, health in health_map.items():
            status_emoji = "🟢" if health["status"] == "UP" else "🔴"
            health_lines.append(f"  {status_emoji} {name}: {health['status']}")

        msg = (
            f"🤖 **Bot Status**\n"
            f"{'─' * 25}\n\n"
            f"📡 Exchanges: {', '.join(exchanges)}\n"
            f"✅ Healthy: {', '.join(healthy) if healthy else 'None'}\n"
            f"📊 Tracked: {len(config.TRADING_PAIRS)} pairs\n"
            f"🔔 Alerts: {active_alerts}\n"
            f"🔄 Scanning: {'Yes' if self.background_tasks else 'No'}\n\n"
            f"💚 **Health**:\n" + "\n".join(health_lines) + "\n\n"
            f"📈 **Arb Stats**:\n"
            f"  Found: {arb_stats.get('total_opportunities', 0)}\n"
            f"  Max: {arb_stats.get('max_spread', 0):.2f}%\n"
            f"  Avg: {arb_stats.get('avg_spread', 0):.2f}%"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    # ─────────────────────────────────────────────
    # BACKGROUND TASKS
    # ─────────────────────────────────────────────

    async def monitor_alerts(self, application: Application):
        """Background task to monitor price alerts."""
        logger.info("Starting alert monitoring...")

        while True:
            try:
                if self.alert_manager.get_active_count() > 0:
                    alert_symbols = list(
                        set(
                            alert.symbol
                            for alert in self.alert_manager.alerts.values()
                            if alert.is_active
                        )
                    )

                    if alert_symbols:
                        tickers = await self.exchange_manager.fetch_all_tickers(
                            alert_symbols
                        )
                        triggered = await self.alert_manager.check_alerts(tickers)

                        for trigger in triggered:
                            try:
                                await application.bot.send_message(
                                    chat_id=config.TELEGRAM_CHAT_ID,
                                    text=trigger["message"],
                                    parse_mode=ParseMode.MARKDOWN,
                                )
                            except Exception as e:
                                logger.error(f"Failed to send alert: {e}")

            except Exception as e:
                logger.error(f"Error in alert monitoring: {e}")

            await asyncio.sleep(self.settings["alert_check_interval"])


def main():
    """Main entry point."""
    bot = TradingBot()
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    handlers = [
        CommandHandler("start", bot.start_command),
        CommandHandler("help", bot.help_command),
        CommandHandler("menu", bot.menu_command),
        CommandHandler("price", bot.price_command),
        CommandHandler("signal", bot.signal_command),
        CommandHandler("signals", bot.signal_command),
        CommandHandler("arb", bot.arb_command),
        CommandHandler("alert", bot.alert_command),
        CommandHandler("alerts", bot.alert_command),
        CommandHandler("set", bot.set_command),
        CommandHandler("status", bot.status_command),
    ]

    for handler in handlers:
        application.add_handler(handler)

    # Register callback handler for inline buttons
    application.add_handler(CallbackQueryHandler(bot.callback_handler))

    # Start alert monitoring
    application.job_queue.run_once(
        lambda ctx: asyncio.create_task(bot.monitor_alerts(application)),
        when=1,
    )

    logger.info("🤖 Trading Bot starting...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
