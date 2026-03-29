"""Daily Signal Digest Service - Automated daily market analysis."""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DailyDigest:
    """Daily market digest."""

    date: str
    top_buys: List[Dict]
    top_sells: List[Dict]
    volume_spikes: List[Dict]
    market_sentiment: str
    sentiment_score: float
    total_signals: int
    buy_count: int
    sell_count: int
    neutral_count: int

    def to_message(self) -> str:
        """Format as Telegram message."""
        sentiment_emoji = {
            "VERY_BULLISH": "🟢🟢",
            "BULLISH": "🟢",
            "NEUTRAL": "⚪",
            "BEARISH": "🔴",
            "VERY_BEARISH": "🔴🔴",
        }

        lines = [
            f"📰 **Daily Signal Digest**",
            f"📅 {self.date}",
            "─" * 30,
            "",
            f"📊 **Market Sentiment**: {sentiment_emoji.get(self.market_sentiment, '⚪')} {self.market_sentiment} ({self.sentiment_score:.1f}%)",
            "",
            f"📈 **Summary**: {self.total_signals} signals analyzed",
            f"  🟢 Buy: {self.buy_count} | 🔴 Sell: {self.sell_count} | ⚪ Neutral: {self.neutral_count}",
        ]

        if self.top_buys:
            lines.extend(["", "🟢 **Top Buy Signals:**"])
            for i, sig in enumerate(self.top_buys[:3], 1):
                lines.append(
                    f"  {i}. **{sig['symbol']}** - {sig['confidence']:.0f}% confidence\n"
                    f"     Entry: ${sig['entry']:,.4f} | R:R 1:{sig['rr']:.1f}"
                )

        if self.top_sells:
            lines.extend(["", "🔴 **Top Sell Signals:**"])
            for i, sig in enumerate(self.top_sells[:3], 1):
                lines.append(
                    f"  {i}. **{sig['symbol']}** - {sig['confidence']:.0f}% confidence\n"
                    f"     Entry: ${sig['entry']:,.4f} | R:R 1:{sig['rr']:.1f}"
                )

        if self.volume_spikes:
            lines.extend(["", "🔊 **Volume Spikes:**"])
            for spike in self.volume_spikes[:5]:
                lines.append(
                    f"  • **{spike['symbol']}**: {spike['ratio']:.1f}x average volume"
                )

        lines.extend(
            [
                "",
                "💡 **Action Items:**",
                "  • Review top signals for entry opportunities",
                "  • Monitor volume spikes for momentum plays",
                "  • Set alerts for key price levels",
            ]
        )

        return "\n".join(lines)


class DigestService:
    """Service for generating daily market digests."""

    def __init__(self, signal_engine, exchange_manager):
        self.signal_engine = signal_engine
        self.exchange_manager = exchange_manager
        self.digest_history: List[DailyDigest] = []

    async def generate_digest(
        self,
        symbols: List[str],
        timeframe: str = "1h",
        max_symbols: int = 20,
    ) -> Optional[DailyDigest]:
        """Generate daily digest for given symbols."""
        logger.info(
            f"[DIGEST] Generating daily digest for {len(symbols[:max_symbols])} symbols..."
        )

        signals = []
        volume_spikes = []

        healthy_exchanges = self.exchange_manager.get_healthy_exchanges()
        if not healthy_exchanges:
            logger.error("[DIGEST] No healthy exchanges available")
            return None

        exchange = self.exchange_manager.get_exchange(healthy_exchanges[0])
        if not exchange:
            return None

        for symbol in symbols[:max_symbols]:
            try:
                # Fetch OHLCV
                loop = asyncio.get_event_loop()
                ohlcv = await loop.run_in_executor(
                    None, lambda s=symbol: exchange.fetch_ohlcv(s, timeframe, limit=100)
                )

                if not ohlcv or len(ohlcv) < 52:
                    continue

                # Analyze
                signal = self.signal_engine.analyze(symbol, ohlcv, timeframe)
                if signal:
                    signals.append(signal)

                    # Check for volume spikes
                    if signal.volume_spike:
                        volume_spikes.append(
                            {
                                "symbol": symbol,
                                "ratio": signal.volume_ratio,
                                "signal": signal.signal.value,
                            }
                        )

            except Exception as e:
                logger.error(f"[DIGEST] Error analyzing {symbol}: {e}")

        if not signals:
            return None

        # Categorize signals
        from modules.advanced_signals import SignalType

        buy_signals = [
            s for s in signals if s.signal in (SignalType.BUY, SignalType.STRONG_BUY)
        ]
        sell_signals = [
            s for s in signals if s.signal in (SignalType.SELL, SignalType.STRONG_SELL)
        ]
        neutral_signals = [s for s in signals if s.signal == SignalType.NEUTRAL]

        # Sort by confidence
        buy_signals.sort(key=lambda s: s.confidence, reverse=True)
        sell_signals.sort(key=lambda s: s.confidence, reverse=True)

        # Calculate market sentiment
        buy_score = sum(s.confidence for s in buy_signals)
        sell_score = sum(s.confidence for s in sell_signals)
        total_score = buy_score + sell_score

        if total_score > 0:
            sentiment_score = (buy_score / total_score) * 100
        else:
            sentiment_score = 50

        if sentiment_score >= 75:
            market_sentiment = "VERY_BULLISH"
        elif sentiment_score >= 60:
            market_sentiment = "BULLISH"
        elif sentiment_score <= 25:
            market_sentiment = "VERY_BEARISH"
        elif sentiment_score <= 40:
            market_sentiment = "BEARISH"
        else:
            market_sentiment = "NEUTRAL"

        # Create digest
        digest = DailyDigest(
            date=datetime.now().strftime("%Y-%m-%d"),
            top_buys=[
                {
                    "symbol": s.symbol,
                    "confidence": s.confidence,
                    "entry": s.entry_price,
                    "rr": s.risk_reward_ratio,
                }
                for s in buy_signals[:5]
            ],
            top_sells=[
                {
                    "symbol": s.symbol,
                    "confidence": s.confidence,
                    "entry": s.entry_price,
                    "rr": s.risk_reward_ratio,
                }
                for s in sell_signals[:5]
            ],
            volume_spikes=volume_spikes,
            market_sentiment=market_sentiment,
            sentiment_score=sentiment_score,
            total_signals=len(signals),
            buy_count=len(buy_signals),
            sell_count=len(sell_signals),
            neutral_count=len(neutral_signals),
        )

        self.digest_history.append(digest)
        logger.info(
            f"[DIGEST] Generated: {len(buy_signals)} buys, {len(sell_signals)} sells, {len(volume_spikes)} volume spikes"
        )

        return digest

    async def continuous_digest(
        self,
        symbols: List[str],
        interval_hours: int = 24,
        callback=None,
    ):
        """Run continuous daily digest generation."""
        logger.info(f"[DIGEST] Starting continuous digest every {interval_hours} hours")

        while True:
            try:
                digest = await self.generate_digest(symbols)
                if digest and callback:
                    await callback(digest)
            except Exception as e:
                logger.error(f"[DIGEST] Error in continuous digest: {e}")

            await asyncio.sleep(interval_hours * 3600)

    def get_last_digest(self) -> Optional[DailyDigest]:
        """Get the most recent digest."""
        return self.digest_history[-1] if self.digest_history else None
