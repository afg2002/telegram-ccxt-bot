"""Telegram Trading Bot - Full-Stack Automated Trading with Advanced Signals."""

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
from modules.alert_manager import AlertManager
from modules.advanced_signals import AdvancedSignalEngine, SignalType
from modules.digest_service import DigestService
from modules.backtester import Backtester
from modules.cross_asset import CrossAssetAnalyzer

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class TradingBot:
    """Full-stack automated trading bot."""

    def __init__(self):
        # Core components
        self.exchange_manager = ExchangeManager(
            config.EXCHANGE_CONFIGS,
            circuit_breaker_threshold=config.CIRCUIT_BREAKER_THRESHOLD,
            circuit_breaker_cooldown=config.CIRCUIT_BREAKER_COOLDOWN,
        )
        self.arbitrage_scanner = ArbitrageScanner(
            self.exchange_manager, config.ARBITRAGE_THRESHOLD
        )
        self.alert_manager = AlertManager()

        # Advanced components
        self.signal_engine = AdvancedSignalEngine()
        self.digest_service = DigestService(self.signal_engine, self.exchange_manager)
        self.backtester = Backtester(self.signal_engine)
        self.cross_asset = CrossAssetAnalyzer(self.exchange_manager)

        # Background tasks
        self.background_tasks: List[asyncio.Task] = []

        # Settings
        self.settings = {
            "arbitrage_threshold": config.ARBITRAGE_THRESHOLD,
            "price_update_interval": config.PRICE_UPDATE_INTERVAL,
            "alert_check_interval": config.ALERT_CHECK_INTERVAL,
            "max_arb_pairs": config.MAX_ARB_PAIRS,
            "signal_timeframe": config.SIGNAL_TIMEFRAME,
        }

    # ═══════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════

    async def send_typing(self, update: Update):
        await update.effective_chat.send_action(ChatAction.TYPING)

    def is_authorized(self, user_id: int) -> bool:
        if not config.ALLOWED_USERS:
            return True
        return user_id in config.ALLOWED_USERS

    async def check_auth(self, update: Update) -> bool:
        user_id = update.effective_user.id
        if not self.is_authorized(user_id):
            await update.message.reply_text("❌ Unauthorized")
            return False
        return True

    # ═══════════════════════════════════════════════
    # KEYBOARDS
    # ═══════════════════════════════════════════════

    def get_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("📊 Prices", callback_data="menu_prices"),
                InlineKeyboardButton("💰 Arbitrage", callback_data="menu_arb"),
            ],
            [
                InlineKeyboardButton("📈 Signals", callback_data="menu_signals"),
                InlineKeyboardButton("📰 Digest", callback_data="menu_digest"),
            ],
            [
                InlineKeyboardButton("🐋 Whales", callback_data="menu_whales"),
                InlineKeyboardButton("🔔 Alerts", callback_data="menu_alerts"),
            ],
            [
                InlineKeyboardButton("📊 Backtest", callback_data="menu_backtest"),
                InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
            ],
            [
                InlineKeyboardButton("📊 Status", callback_data="menu_status"),
                InlineKeyboardButton("❓ Help", callback_data="menu_help"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_price_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = []
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

    def get_signal_keyboard(self) -> InlineKeyboardMarkup:
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
        keyboard.extend(
            [
                [InlineKeyboardButton("📊 All Signals", callback_data="signal_all")],
                [InlineKeyboardButton("⬅️ Back", callback_data="menu_main")],
            ]
        )
        return InlineKeyboardMarkup(keyboard)

    def get_arb_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("🔍 Scan All", callback_data="arb_scan_all"),
                InlineKeyboardButton("📊 Top 20", callback_data="arb_scan_top20"),
            ],
            [
                InlineKeyboardButton("▶️ Auto-Scan", callback_data="arb_start"),
                InlineKeyboardButton("⏹ Stop", callback_data="arb_stop"),
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_backtest_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = []
        row = []
        for i, pair in enumerate(config.TRADING_PAIRS[:10]):
            symbol = pair.split("/")[0]
            row.append(InlineKeyboardButton(symbol, callback_data=f"backtest_{pair}"))
            if len(row) == 5:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="menu_main")])
        return InlineKeyboardMarkup(keyboard)

    # ═══════════════════════════════════════════════
    # COMMAND HANDLERS
    # ═══════════════════════════════════════════════

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        welcome_msg = (
            "🤖 **Full-Stack Trading Bot Active!**\n\n"
            "Features:\n"
            "• 📊 Real-time prices from 8+ exchanges\n"
            "• 📈 20+ technical indicators\n"
            "• 💰 Arbitrage scanner (all pairs)\n"
            "• 🐋 Whale detection\n"
            "• 📰 Daily signal digest\n"
            "• 📊 Backtesting engine\n"
            "• 🔔 Smart alerts\n\n"
            "Use buttons below to navigate:"
        )
        await update.message.reply_text(
            welcome_msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_main_menu_keyboard(),
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.start_command(update, context)

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
        await update.message.reply_text(
            "📋 **Main Menu**",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_main_menu_keyboard(),
        )

    # ═══════════════════════════════════════════════
    # CALLBACK HANDLER
    # ═══════════════════════════════════════════════

    async def callback_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        query = update.callback_query
        await query.answer()

        if not self.is_authorized(query.from_user.id):
            await query.edit_message_text("❌ Unauthorized")
            return

        data = query.data

        # Main menu
        if data == "menu_main":
            await query.edit_message_text(
                "📋 **Main Menu**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_main_menu_keyboard(),
            )

        # Prices
        elif data == "menu_prices":
            await query.edit_message_text(
                "📊 **Select pair:**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_price_keyboard(),
            )
        elif data.startswith("price_"):
            await self._handle_price(query, data.replace("price_", ""))

        # Signals
        elif data == "menu_signals":
            await query.edit_message_text(
                "📈 **Select pair for signal:**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_signal_keyboard(),
            )
        elif data.startswith("signal_"):
            if data == "signal_all":
                await self._handle_all_signals(query)
            else:
                await self._handle_signal(query, data.replace("signal_", ""))

        # Arbitrage
        elif data == "menu_arb":
            await query.edit_message_text(
                "💰 **Arbitrage Scanner**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_arb_keyboard(),
            )
        elif data == "arb_scan_all":
            await self._handle_arb_scan(query, all_pairs=True)
        elif data == "arb_scan_top20":
            await self._handle_arb_scan(query, all_pairs=False)
        elif data == "arb_start":
            await self._handle_arb_start(query)
        elif data == "arb_stop":
            await self._handle_arb_stop(query)

        # Digest
        elif data == "menu_digest":
            await self._handle_digest(query)

        # Whales
        elif data == "menu_whales":
            await self._handle_whales(query)

        # Backtest
        elif data == "menu_backtest":
            await query.edit_message_text(
                "📊 **Select pair for backtest:**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_backtest_keyboard(),
            )
        elif data.startswith("backtest_"):
            await self._handle_backtest(query, data.replace("backtest_", ""))

        # Alerts
        elif data == "menu_alerts":
            await self._handle_alerts(query)

        # Settings
        elif data == "menu_settings":
            await query.edit_message_text(
                "⚙️ **Settings**\n\n"
                + "\n".join(f"• {k}: {v}" for k, v in self.settings.items())
                + "\n\nUse `/set <key> <value>` to change",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]
                ),
            )

        # Status
        elif data == "menu_status":
            await self._handle_status(query)

        # Help
        elif data == "menu_help":
            await self._handle_help(query)

    # ═══════════════════════════════════════════════
    # HANDLER METHODS
    # ═══════════════════════════════════════════════

    async def _handle_price(self, query: CallbackQuery, symbol: str):
        await query.edit_message_text(f"⏳ Fetching {symbol}...")

        tickers = await self.exchange_manager.fetch_all_tickers([symbol])
        if not tickers.get(symbol):
            await query.edit_message_text(
                f"❌ Could not fetch {symbol}",
                reply_markup=self.get_price_keyboard(),
            )
            return

        exchange_prices = tickers[symbol]
        prices = []
        for exchange, ticker in exchange_prices.items():
            if exchange.startswith("_"):
                continue
            last = ticker.get("last", 0)
            change = ticker.get("change_24h", 0)
            emoji = "🟢" if change and change >= 0 else "🔴"
            prices.append(f"• **{exchange}**: ${last:,.4f} {emoji} {change:+.2f}%")

        all_prices = [
            t.get("last", 0)
            for e, t in exchange_prices.items()
            if not e.startswith("_") and t.get("last")
        ]
        avg = sum(all_prices) / len(all_prices) if all_prices else 0

        msg = (
            f"💰 **{symbol}**\n{'─' * 25}\n\n"
            + "\n".join(prices)
            + f"\n\n📊 Avg: **${avg:,.4f}**"
        )
        await query.edit_message_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_price_keyboard(),
        )

    async def _handle_signal(self, query: CallbackQuery, symbol: str):
        await query.edit_message_text(f"⏳ Analyzing {symbol}...")

        healthy = self.exchange_manager.get_healthy_exchanges()
        if not healthy:
            await query.edit_message_text(
                "❌ No exchanges available",
                reply_markup=self.get_signal_keyboard(),
            )
            return

        exchange = self.exchange_manager.get_exchange(healthy[0])
        try:
            loop = asyncio.get_event_loop()
            ohlcv = await loop.run_in_executor(
                None,
                lambda: exchange.fetch_ohlcv(
                    symbol, self.settings["signal_timeframe"], limit=100
                ),
            )

            if not ohlcv:
                await query.edit_message_text(
                    f"❌ No data for {symbol}",
                    reply_markup=self.get_signal_keyboard(),
                )
                return

            signal = self.signal_engine.analyze(
                symbol, ohlcv, self.settings["signal_timeframe"]
            )
            if signal:
                await query.edit_message_text(
                    signal.to_message(),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self.get_signal_keyboard(),
                )
            else:
                await query.edit_message_text(
                    f"❌ Could not generate signal",
                    reply_markup=self.get_signal_keyboard(),
                )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Error: {str(e)}",
                reply_markup=self.get_signal_keyboard(),
            )

    async def _handle_all_signals(self, query: CallbackQuery):
        await query.edit_message_text("⏳ Analyzing all pairs...")

        healthy = self.exchange_manager.get_healthy_exchanges()
        if not healthy:
            await query.edit_message_text("❌ No exchanges available")
            return

        exchange = self.exchange_manager.get_exchange(healthy[0])
        signals = []

        for pair in config.TRADING_PAIRS[:10]:
            try:
                loop = asyncio.get_event_loop()
                ohlcv = await loop.run_in_executor(
                    None,
                    lambda p=pair: exchange.fetch_ohlcv(
                        p, self.settings["signal_timeframe"], limit=100
                    ),
                )
                if ohlcv:
                    signal = self.signal_engine.analyze(
                        pair, ohlcv, self.settings["signal_timeframe"]
                    )
                    if signal:
                        signals.append(signal)
            except Exception as e:
                logger.error(f"Error analyzing {pair}: {e}")

        if signals:
            msg = self.signal_engine.format_signal_summary(signals)
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

    async def _handle_arb_scan(self, query: CallbackQuery, all_pairs: bool):
        await query.edit_message_text("🔍 Scanning...")

        if all_pairs:
            opps = await self.arbitrage_scanner.scan(
                symbols=None, max_pairs=self.settings["max_arb_pairs"]
            )
        else:
            opps = await self.arbitrage_scanner.scan(symbols=config.TRADING_PAIRS[:20])

        msg = self.arbitrage_scanner.format_opportunities(opps, max_display=10)
        await query.edit_message_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_arb_keyboard(),
        )

    async def _handle_arb_start(self, query: CallbackQuery):
        if self.background_tasks:
            await query.edit_message_text(
                "⚠️ Already running!",
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
            f"✅ Auto-scan started!\n"
            f"📊 Interval: {self.settings['price_update_interval']}s\n"
            f"🎯 Threshold: {self.settings['arbitrage_threshold']}%",
            reply_markup=self.get_arb_keyboard(),
        )

    async def _handle_arb_stop(self, query: CallbackQuery):
        for task in self.background_tasks:
            task.cancel()
        self.background_tasks.clear()
        await query.edit_message_text(
            "🛑 Stopped",
            reply_markup=self.get_arb_keyboard(),
        )

    async def _arb_callback(self, opportunities):
        if opportunities:
            logger.info(f"[ARB] Found {len(opportunities)} opportunities")

    async def _handle_digest(self, query: CallbackQuery):
        await query.edit_message_text("📰 Generating daily digest...")

        digest = await self.digest_service.generate_digest(
            config.TRADING_PAIRS,
            timeframe=self.settings["signal_timeframe"],
            max_symbols=15,
        )

        if digest:
            await query.edit_message_text(
                digest.to_message(),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]
                ),
            )
        else:
            await query.edit_message_text(
                "❌ Could not generate digest",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]
                ),
            )

    async def _handle_whales(self, query: CallbackQuery):
        await query.edit_message_text("🐋 Scanning for whale activity...")

        alerts = await self.cross_asset.detect_whale_activity(
            config.TRADING_PAIRS[:15],
            volume_threshold=3.0,
            price_impact_threshold=1.0,
        )

        msg = self.cross_asset.format_whale_alerts(alerts)
        await query.edit_message_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]
            ),
        )

    async def _handle_backtest(self, query: CallbackQuery, symbol: str):
        await query.edit_message_text(f"📊 Running backtest for {symbol}...")

        healthy = self.exchange_manager.get_healthy_exchanges()
        if not healthy:
            await query.edit_message_text("❌ No exchanges available")
            return

        exchange = self.exchange_manager.get_exchange(healthy[0])
        try:
            loop = asyncio.get_event_loop()
            ohlcv = await loop.run_in_executor(
                None, lambda: exchange.fetch_ohlcv(symbol, "1h", limit=500)
            )

            if not ohlcv or len(ohlcv) < 100:
                await query.edit_message_text(
                    f"❌ Insufficient data for {symbol}",
                    reply_markup=self.get_backtest_keyboard(),
                )
                return

            result = self.backtester.run_backtest(symbol, ohlcv, "1h")
            await query.edit_message_text(
                result.to_message(),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_backtest_keyboard(),
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Error: {str(e)}",
                reply_markup=self.get_backtest_keyboard(),
            )

    async def _handle_alerts(self, query: CallbackQuery):
        msg = self.alert_manager.format_user_alerts(query.from_user.id)
        await query.edit_message_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]
            ),
        )

    async def _handle_status(self, query: CallbackQuery):
        exchanges = self.exchange_manager.get_available_exchanges()
        healthy = self.exchange_manager.get_healthy_exchanges()
        arb_stats = self.arbitrage_scanner.get_statistics()

        health_map = self.exchange_manager.get_health_map()
        health_lines = []
        for name, health in health_map.items():
            emoji = "🟢" if health["status"] == "UP" else "🔴"
            health_lines.append(f"  {emoji} {name}: {health['status']}")

        msg = (
            f"🤖 **Bot Status**\n{'─' * 25}\n\n"
            f"📡 Exchanges: {len(exchanges)}\n"
            f"✅ Healthy: {len(healthy)}\n"
            f"📊 Pairs: {len(config.TRADING_PAIRS)}\n"
            f"🔄 Scanning: {'Yes' if self.background_tasks else 'No'}\n\n"
            f"💚 **Health**:\n" + "\n".join(health_lines) + "\n\n"
            f"📈 **Arb**: {arb_stats.get('total_opportunities', 0)} found"
        )
        await query.edit_message_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]
            ),
        )

    async def _handle_help(self, query: CallbackQuery):
        help_msg = (
            "❓ **Commands**\n{'─' * 25}\n\n"
            "/start - Main menu\n"
            "/signal `<symbol>` - Get signal\n"
            "/price `<symbol>` - Get price\n"
            "/arb - Arbitrage menu\n"
            "/digest - Daily digest\n"
            "/whales - Whale alerts\n"
            "/backtest `<symbol>` - Backtest\n"
            "/alert `<symbol> above|below <price>`\n"
            "/set `<key> <value>` - Settings\n"
            "/status - Bot status"
        )
        await query.edit_message_text(
            help_msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]
            ),
        )

    # ═══════════════════════════════════════════════
    # TEXT COMMANDS
    # ═══════════════════════════════════════════════

    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        if not context.args:
            await update.message.reply_text(
                "📊 **Select pair:**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_price_keyboard(),
            )
            return

        symbol = context.args[0].upper()
        await self.send_typing(update)

        tickers = await self.exchange_manager.fetch_all_tickers([symbol])
        if not tickers.get(symbol):
            await update.message.reply_text(f"❌ Could not fetch {symbol}")
            return

        exchange_prices = tickers[symbol]
        prices = []
        for exchange, ticker in exchange_prices.items():
            if exchange.startswith("_"):
                continue
            last = ticker.get("last", 0)
            change = ticker.get("change_24h", 0)
            emoji = "🟢" if change and change >= 0 else "🔴"
            prices.append(f"• **{exchange}**: ${last:,.4f} {emoji} {change:+.2f}%")

        all_prices = [
            t.get("last", 0)
            for e, t in exchange_prices.items()
            if not e.startswith("_") and t.get("last")
        ]
        avg = sum(all_prices) / len(all_prices) if all_prices else 0

        msg = (
            f"💰 **{symbol}**\n{'─' * 25}\n\n"
            + "\n".join(prices)
            + f"\n\n📊 Avg: **${avg:,.4f}**"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        if not context.args:
            await update.message.reply_text(
                "📈 **Select pair:**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_signal_keyboard(),
            )
            return

        symbol = context.args[0].upper()
        await self.send_typing(update)

        healthy = self.exchange_manager.get_healthy_exchanges()
        if not healthy:
            await update.message.reply_text("❌ No exchanges available")
            return

        exchange = self.exchange_manager.get_exchange(healthy[0])
        try:
            loop = asyncio.get_event_loop()
            ohlcv = await loop.run_in_executor(
                None,
                lambda: exchange.fetch_ohlcv(
                    symbol, self.settings["signal_timeframe"], limit=100
                ),
            )

            if not ohlcv:
                await update.message.reply_text(f"❌ No data for {symbol}")
                return

            signal = self.signal_engine.analyze(
                symbol, ohlcv, self.settings["signal_timeframe"]
            )
            if signal:
                await update.message.reply_text(
                    signal.to_message(), parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(f"❌ Could not generate signal")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def arb_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
        await update.message.reply_text(
            "💰 **Arbitrage Scanner**",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_arb_keyboard(),
        )

    async def digest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        await self.send_typing(update)
        digest = await self.digest_service.generate_digest(
            config.TRADING_PAIRS,
            timeframe=self.settings["signal_timeframe"],
            max_symbols=15,
        )

        if digest:
            await update.message.reply_text(
                digest.to_message(), parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Could not generate digest")

    async def whales_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        await self.send_typing(update)
        alerts = await self.cross_asset.detect_whale_activity(
            config.TRADING_PAIRS[:15],
            volume_threshold=3.0,
            price_impact_threshold=1.0,
        )

        msg = self.cross_asset.format_whale_alerts(alerts)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    async def backtest_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        if not await self.check_auth(update):
            return

        if not context.args:
            await update.message.reply_text(
                "📊 **Select pair:**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_backtest_keyboard(),
            )
            return

        symbol = context.args[0].upper()
        await self.send_typing(update)

        healthy = self.exchange_manager.get_healthy_exchanges()
        if not healthy:
            await update.message.reply_text("❌ No exchanges available")
            return

        exchange = self.exchange_manager.get_exchange(healthy[0])
        try:
            loop = asyncio.get_event_loop()
            ohlcv = await loop.run_in_executor(
                None, lambda: exchange.fetch_ohlcv(symbol, "1h", limit=500)
            )

            if not ohlcv or len(ohlcv) < 100:
                await update.message.reply_text(f"❌ Insufficient data for {symbol}")
                return

            result = self.backtester.run_backtest(symbol, ohlcv, "1h")
            await update.message.reply_text(
                result.to_message(), parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def alert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        if len(context.args) < 3:
            await update.message.reply_text(
                "Usage: `/alert BTC/USDT above 50000`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        symbol = context.args[0].upper()
        alert_type_str = context.args[1].lower()

        try:
            target_value = float(context.args[2])
        except ValueError:
            await update.message.reply_text("❌ Invalid price")
            return

        alert_type = (
            AlertType.PRICE_ABOVE
            if alert_type_str == "above"
            else AlertType.PRICE_BELOW
        )
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

    async def set_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                "⚙️ **Current Settings**\n\n"
                + "\n".join(f"• {k}: {v}" for k, v in self.settings.items())
                + "\n\nUsage: `/set <key> <value>`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        setting = context.args[0].lower()
        value = context.args[1]

        valid = {
            "arb_threshold": ("arbitrage_threshold", float),
            "update_interval": ("price_update_interval", int),
            "max_pairs": ("max_arb_pairs", int),
            "signal_tf": ("signal_timeframe", str),
        }

        if setting not in valid:
            await update.message.reply_text(f"❌ Unknown: {setting}")
            return

        key, type_func = valid[setting]
        try:
            self.settings[key] = type_func(value)
            if key == "arbitrage_threshold":
                self.arbitrage_scanner.threshold = self.settings[key]
            await update.message.reply_text(f"✅ {key} = {self.settings[key]}")
        except ValueError:
            await update.message.reply_text("❌ Invalid value")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        exchanges = self.exchange_manager.get_available_exchanges()
        healthy = self.exchange_manager.get_healthy_exchanges()
        arb_stats = self.arbitrage_scanner.get_statistics()

        health_map = self.exchange_manager.get_health_map()
        health_lines = []
        for name, health in health_map.items():
            emoji = "🟢" if health["status"] == "UP" else "🔴"
            health_lines.append(f"  {emoji} {name}: {health['status']}")

        msg = (
            f"🤖 **Bot Status**\n{'─' * 25}\n\n"
            f"📡 Exchanges: {len(exchanges)}\n"
            f"✅ Healthy: {len(healthy)}\n"
            f"📊 Pairs: {len(config.TRADING_PAIRS)}\n"
            f"🔄 Scanning: {'Yes' if self.background_tasks else 'No'}\n\n"
            f"💚 **Health**:\n" + "\n".join(health_lines) + "\n\n"
            f"📈 **Arb**: {arb_stats.get('total_opportunities', 0)} found"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    # ═══════════════════════════════════════════════
    # BACKGROUND TASKS
    # ═══════════════════════════════════════════════

    async def monitor_alerts(self, application: Application):
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
                                logger.error(f"Alert send error: {e}")
            except Exception as e:
                logger.error(f"Alert monitor error: {e}")
            await asyncio.sleep(self.settings["alert_check_interval"])


def main():
    """Main entry point."""
    bot = TradingBot()
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    handlers = [
        CommandHandler("start", bot.start_command),
        CommandHandler("help", bot.help_command),
        CommandHandler("menu", bot.menu_command),
        CommandHandler("price", bot.price_command),
        CommandHandler("signal", bot.signal_command),
        CommandHandler("signals", bot.signal_command),
        CommandHandler("arb", bot.arb_command),
        CommandHandler("digest", bot.digest_command),
        CommandHandler("whales", bot.whales_command),
        CommandHandler("backtest", bot.backtest_command),
        CommandHandler("alert", bot.alert_command),
        CommandHandler("alerts", bot.alert_command),
        CommandHandler("set", bot.set_command),
        CommandHandler("status", bot.status_command),
    ]

    for handler in handlers:
        application.add_handler(handler)

    application.add_handler(CallbackQueryHandler(bot.callback_handler))

    application.job_queue.run_once(
        lambda ctx: asyncio.create_task(bot.monitor_alerts(application)),
        when=1,
    )

    logger.info("🤖 Full-Stack Trading Bot starting...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
