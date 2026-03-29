"""Cross-Asset Signals - Volume delta, correlation, and market sentiment."""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MarketSentiment:
    """Overall market sentiment."""

    score: float  # 0-100
    label: str  # EXTREME_FEAR, FEAR, NEUTRAL, GREED, EXTREME_GREED
    buy_pressure: float
    sell_pressure: float
    volume_trend: str
    timestamp: str

    def to_message(self) -> str:
        """Format as message."""
        emoji_map = {
            "EXTREME_FEAR": "🔴🔴",
            "FEAR": "🔴",
            "NEUTRAL": "⚪",
            "GREED": "🟢",
            "EXTREME_GREED": "🟢🟢",
        }

        return (
            f"{emoji_map.get(self.label, '⚪')} **Market Sentiment: {self.label}**\n"
            f"📊 Score: {self.score:.1f}/100\n"
            f"🟢 Buy Pressure: {self.buy_pressure:.1f}%\n"
            f"🔴 Sell Pressure: {self.sell_pressure:.1f}%\n"
            f"📈 Volume Trend: {self.volume_trend}\n"
            f"⏰ {self.timestamp}"
        )


@dataclass
class VolumeDelta:
    """Volume delta analysis for a symbol."""

    symbol: str
    buy_volume: float
    sell_volume: float
    net_volume: float
    delta_percent: float
    trend: str  # "BULLISH", "BEARISH", "NEUTRAL"

    def to_message(self) -> str:
        """Format as message."""
        trend_emoji = {
            "BULLISH": "🟢",
            "BEARISH": "🔴",
            "NEUTRAL": "⚪",
        }

        return (
            f"{trend_emoji.get(self.trend, '⚪')} **{self.symbol}** Volume Delta\n"
            f"  📊 Buy Vol: {self.buy_volume:,.0f}\n"
            f"  📊 Sell Vol: {self.sell_volume:,.0f}\n"
            f"  💰 Net: {self.net_volume:+,.0f} ({self.delta_percent:+.2f}%)"
        )


@dataclass
class WhaleAlert:
    """Whale activity detection."""

    symbol: str
    exchange: str
    volume_ratio: float
    price_impact: float
    direction: str  # "BUY", "SELL"
    timestamp: str

    def to_message(self) -> str:
        """Format as message."""
        emoji = "🐋" if self.volume_ratio >= 5.0 else "🦈"

        return (
            f"{emoji} **Whale Alert: {self.symbol}**\n"
            f"  📡 Exchange: {self.exchange}\n"
            f"  📊 Volume: {self.volume_ratio:.1f}x average\n"
            f"  💹 Price Impact: {self.price_impact:+.2f}%\n"
            f"  📈 Direction: {self.direction}\n"
            f"  ⏰ {self.timestamp}"
        )


class CrossAssetAnalyzer:
    """Analyze cross-asset signals and market sentiment."""

    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self._volume_history: Dict[str, List[float]] = {}
        self._price_history: Dict[str, List[float]] = {}

    async def analyze_volume_delta(
        self,
        symbol: str,
        exchange_name: Optional[str] = None,
    ) -> Optional[VolumeDelta]:
        """Analyze volume delta for a symbol.

        This is a simplified estimation based on price movement and volume.
        """
        if exchange_name is None:
            healthy = self.exchange_manager.get_healthy_exchanges()
            if not healthy:
                return None
            exchange_name = healthy[0]

        exchange = self.exchange_manager.get_exchange(exchange_name)
        if not exchange:
            return None

        try:
            loop = asyncio.get_event_loop()
            ohlcv = await loop.run_in_executor(
                None, lambda: exchange.fetch_ohlcv(symbol, "1h", limit=24)
            )

            if not ohlcv or len(ohlcv) < 2:
                return None

            # Estimate buy/sell volume based on price movement
            total_buy_volume = 0
            total_sell_volume = 0

            for candle in ohlcv:
                open_price = candle[1]
                close_price = candle[4]
                volume = candle[5]

                if close_price >= open_price:
                    # Bullish candle - estimate buy volume
                    buy_ratio = 0.5 + (close_price - open_price) / (
                        close_price + open_price
                    )
                    total_buy_volume += volume * buy_ratio
                    total_sell_volume += volume * (1 - buy_ratio)
                else:
                    # Bearish candle - estimate sell volume
                    sell_ratio = 0.5 + (open_price - close_price) / (
                        open_price + close_price
                    )
                    total_sell_volume += volume * sell_ratio
                    total_buy_volume += volume * (1 - sell_ratio)

            total_volume = total_buy_volume + total_sell_volume
            net_volume = total_buy_volume - total_sell_volume
            delta_percent = (net_volume / total_volume) * 100 if total_volume > 0 else 0

            if delta_percent > 10:
                trend = "BULLISH"
            elif delta_percent < -10:
                trend = "BEARISH"
            else:
                trend = "NEUTRAL"

            return VolumeDelta(
                symbol=symbol,
                buy_volume=total_buy_volume,
                sell_volume=total_sell_volume,
                net_volume=net_volume,
                delta_percent=delta_percent,
                trend=trend,
            )

        except Exception as e:
            logger.error(f"Error analyzing volume delta for {symbol}: {e}")
            return None

    async def detect_whale_activity(
        self,
        symbols: List[str],
        volume_threshold: float = 5.0,
        price_impact_threshold: float = 2.0,
    ) -> List[WhaleAlert]:
        """Detect whale activity across symbols."""
        alerts = []
        healthy_exchanges = self.exchange_manager.get_healthy_exchanges()

        if not healthy_exchanges:
            return alerts

        exchange = self.exchange_manager.get_exchange(healthy_exchanges[0])
        if not exchange:
            return alerts

        for symbol in symbols:
            try:
                loop = asyncio.get_event_loop()
                ohlcv = await loop.run_in_executor(
                    None, lambda s=symbol: exchange.fetch_ohlcv(s, "1h", limit=24)
                )

                if not ohlcv or len(ohlcv) < 20:
                    continue

                volumes = [c[5] for c in ohlcv]
                closes = [c[4] for c in ohlcv]

                avg_volume = sum(volumes[:-1]) / len(volumes[:-1])
                current_volume = volumes[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

                # Calculate price impact
                price_change = (
                    ((closes[-1] - closes[-2]) / closes[-2]) * 100
                    if closes[-2] > 0
                    else 0
                )

                if (
                    volume_ratio >= volume_threshold
                    and abs(price_change) >= price_impact_threshold
                ):
                    alerts.append(
                        WhaleAlert(
                            symbol=symbol,
                            exchange=healthy_exchanges[0],
                            volume_ratio=volume_ratio,
                            price_impact=price_change,
                            direction="BUY" if price_change > 0 else "SELL",
                            timestamp=datetime.now().strftime("%H:%M:%S"),
                        )
                    )

            except Exception as e:
                logger.error(f"Error detecting whale activity for {symbol}: {e}")

        return sorted(alerts, key=lambda a: a.volume_ratio, reverse=True)

    async def calculate_market_sentiment(
        self,
        symbols: List[str],
    ) -> Optional[MarketSentiment]:
        """Calculate overall market sentiment."""
        healthy_exchanges = self.exchange_manager.get_healthy_exchanges()
        if not healthy_exchanges:
            return None

        exchange = self.exchange_manager.get_exchange(healthy_exchanges[0])
        if not exchange:
            return None

        buy_signals = 0
        sell_signals = 0
        total_volume_ratio = 0
        count = 0

        for symbol in symbols[:20]:  # Analyze top 20
            try:
                loop = asyncio.get_event_loop()
                ohlcv = await loop.run_in_executor(
                    None, lambda s=symbol: exchange.fetch_ohlcv(s, "1h", limit=24)
                )

                if not ohlcv or len(ohlcv) < 2:
                    continue

                closes = [c[4] for c in ohlcv]
                volumes = [c[5] for c in ohlcv]

                # Price trend
                if closes[-1] > closes[-2]:
                    buy_signals += 1
                elif closes[-1] < closes[-2]:
                    sell_signals += 1

                # Volume trend
                avg_vol = sum(volumes[:-1]) / len(volumes[:-1])
                vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1.0
                total_volume_ratio += vol_ratio

                count += 1

            except Exception as e:
                logger.error(f"Error calculating sentiment for {symbol}: {e}")

        if count == 0:
            return None

        # Calculate sentiment
        buy_pressure = (buy_signals / count) * 100
        sell_pressure = (sell_signals / count) * 100
        avg_volume_ratio = total_volume_ratio / count

        # Sentiment score (0-100)
        score = buy_pressure

        if score >= 80:
            label = "EXTREME_GREED"
        elif score >= 60:
            label = "GREED"
        elif score >= 40:
            label = "NEUTRAL"
        elif score >= 20:
            label = "FEAR"
        else:
            label = "EXTREME_FEAR"

        if avg_volume_ratio >= 1.5:
            volume_trend = "HIGH"
        elif avg_volume_ratio <= 0.7:
            volume_trend = "LOW"
        else:
            volume_trend = "NORMAL"

        return MarketSentiment(
            score=score,
            label=label,
            buy_pressure=buy_pressure,
            sell_pressure=sell_pressure,
            volume_trend=volume_trend,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def format_whale_alerts(self, alerts: List[WhaleAlert]) -> str:
        """Format whale alerts as message."""
        if not alerts:
            return "🐋 No whale activity detected"

        lines = ["🐋 **Whale Activity Detected**\n" + "─" * 30 + "\n"]

        for alert in alerts[:5]:
            lines.append(alert.to_message())
            lines.append("")

        return "\n".join(lines)
