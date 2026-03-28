"""Signal Analyzer - Technical analysis and trading signals."""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Signal types."""

    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class IndicatorSignal:
    """Individual indicator signal."""

    name: str
    value: float
    signal: SignalType
    weight: float = 1.0
    description: str = ""


@dataclass
class TradingSignal:
    """Complete trading signal with all indicators."""

    symbol: str
    timeframe: str
    overall_signal: SignalType
    confidence: float
    indicators: List[IndicatorSignal]
    price: float
    timestamp: str

    def to_message(self) -> str:
        """Format as readable message."""
        signal_emoji = {
            SignalType.STRONG_BUY: "🟢🟢",
            SignalType.BUY: "🟢",
            SignalType.NEUTRAL: "⚪",
            SignalType.SELL: "🔴",
            SignalType.STRONG_SELL: "🔴🔴",
        }

        signal_text = {
            SignalType.STRONG_BUY: "STRONG BUY",
            SignalType.BUY: "BUY",
            SignalType.NEUTRAL: "NEUTRAL",
            SignalType.SELL: "SELL",
            SignalType.STRONG_SELL: "STRONG SELL",
        }

        lines = [
            f"{signal_emoji[self.overall_signal]} **{signal_text[self.overall_signal]}**",
            f"📊 Confidence: {self.confidence:.1f}%",
            f"💰 Price: ${self.price:,.2f}",
            f"⏱️ Timeframe: {self.timeframe}",
            "",
            "**Indicators:**",
        ]

        for ind in self.indicators:
            ind_emoji = {
                SignalType.STRONG_BUY: "🟢🟢",
                SignalType.BUY: "🟢",
                SignalType.NEUTRAL: "⚪",
                SignalType.SELL: "🔴",
                SignalType.STRONG_SELL: "🔴🔴",
            }
            lines.append(
                f"  {ind_emoji[ind.signal]} {ind.name}: {ind.value:.2f} "
                f"({ind.signal.value})"
            )

        return "\n".join(lines)


class SignalAnalyzer:
    """Analyzes market data and generates trading signals."""

    def __init__(self):
        # Indicator weights for overall signal
        self.weights = {
            "RSI": 1.5,
            "MACD": 1.5,
            "Volume": 1.0,
            "MA_Cross": 1.2,
            "Bollinger": 1.0,
            "Stochastic": 1.0,
            "ADX": 0.8,
        }

    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate RSI (Relative Strength Index)."""
        if len(prices) < period + 1:
            return None

        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Smooth with EMA
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_macd(
        self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Optional[Dict]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        if len(prices) < slow + signal:
            return None

        def ema(data: List[float], period: int) -> List[float]:
            """Calculate EMA."""
            multiplier = 2 / (period + 1)
            ema_values = [sum(data[:period]) / period]
            for price in data[period:]:
                ema_values.append(
                    (price - ema_values[-1]) * multiplier + ema_values[-1]
                )
            return ema_values

        fast_ema = ema(prices, fast)
        slow_ema = ema(prices, slow)

        # Align lengths
        diff = len(fast_ema) - len(slow_ema)
        fast_ema = fast_ema[diff:]

        macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
        signal_line = ema(macd_line, signal)

        # Align again
        diff2 = len(macd_line) - len(signal_line)
        macd_line = macd_line[diff2:]

        histogram = [m - s for m, s in zip(macd_line, signal_line)]

        return {
            "macd": macd_line[-1],
            "signal": signal_line[-1],
            "histogram": histogram[-1],
        }

    def calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    def calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period

        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def calculate_bollinger_bands(
        self, prices: List[float], period: int = 20, std_dev: float = 2.0
    ) -> Optional[Dict]:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return None

        sma = sum(prices[-period:]) / period
        variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
        std = math.sqrt(variance)

        return {
            "upper": sma + (std * std_dev),
            "middle": sma,
            "lower": sma - (std * std_dev),
            "bandwidth": (std * std_dev * 2) / sma * 100,
        }

    def calculate_stochastic(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        k_period: int = 14,
        d_period: int = 3,
    ) -> Optional[Dict]:
        """Calculate Stochastic Oscillator."""
        if len(closes) < k_period:
            return None

        recent_high = max(highs[-k_period:])
        recent_low = min(lows[-k_period:])

        if recent_high == recent_low:
            k = 50.0
        else:
            k = ((closes[-1] - recent_low) / (recent_high - recent_low)) * 100

        # Simplified D line
        d = k  # Would need K values history for proper calculation

        return {"k": k, "d": d}

    def calculate_adx(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14,
    ) -> Optional[float]:
        """Calculate ADX (Average Directional Index) - simplified."""
        if len(closes) < period + 1:
            return None

        # Simplified: just return based on trend strength
        changes = [abs(closes[i] - closes[i - 1]) for i in range(1, len(closes))]
        avg_change = sum(changes[-period:]) / period
        avg_price = sum(closes[-period:]) / period

        # Normalize to 0-100
        adx = min(100, (avg_change / avg_price) * 1000)
        return adx

    def calculate_volume_signal(
        self, volumes: List[float], period: int = 20
    ) -> Optional[float]:
        """Calculate volume-based signal."""
        if len(volumes) < period:
            return None

        avg_volume = sum(volumes[-period:]) / period
        current_volume = volumes[-1]

        # Volume ratio
        ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        return ratio

    def get_rsi_signal(self, rsi: float) -> SignalType:
        """Get signal from RSI value."""
        if rsi <= 30:
            return SignalType.STRONG_BUY
        elif rsi <= 40:
            return SignalType.BUY
        elif rsi >= 70:
            return SignalType.STRONG_SELL
        elif rsi >= 60:
            return SignalType.SELL
        return SignalType.NEUTRAL

    def get_macd_signal(self, macd_data: Dict) -> SignalType:
        """Get signal from MACD data."""
        histogram = macd_data.get("histogram", 0)
        macd = macd_data.get("macd", 0)
        signal = macd_data.get("signal", 0)

        if histogram > 0 and macd > signal:
            return SignalType.BUY if histogram > 0.001 else SignalType.NEUTRAL
        elif histogram < 0 and macd < signal:
            return SignalType.SELL if histogram < -0.001 else SignalType.NEUTRAL
        return SignalType.NEUTRAL

    def get_volume_signal(self, ratio: float) -> SignalType:
        """Get signal from volume ratio."""
        if ratio >= 2.0:
            return SignalType.STRONG_BUY
        elif ratio >= 1.5:
            return SignalType.BUY
        elif ratio <= 0.5:
            return SignalType.SELL
        elif ratio <= 0.3:
            return SignalType.STRONG_SELL
        return SignalType.NEUTRAL

    def get_ma_cross_signal(
        self, short_ma: float, long_ma: float, price: float
    ) -> SignalType:
        """Get signal from MA crossover."""
        if short_ma > long_ma and price > short_ma:
            return SignalType.BUY
        elif short_ma < long_ma and price < short_ma:
            return SignalType.SELL
        return SignalType.NEUTRAL

    def get_bollinger_signal(self, price: float, bands: Dict) -> SignalType:
        """Get signal from Bollinger Bands."""
        upper = bands["upper"]
        lower = bands["lower"]
        middle = bands["middle"]

        if price <= lower:
            return SignalType.BUY
        elif price >= upper:
            return SignalType.SELL
        elif price < middle:
            return SignalType.NEUTRAL
        return SignalType.NEUTRAL

    def get_stochastic_signal(self, stoch: Dict) -> SignalType:
        """Get signal from Stochastic."""
        k = stoch.get("k", 50)

        if k <= 20:
            return SignalType.STRONG_BUY
        elif k <= 30:
            return SignalType.BUY
        elif k >= 80:
            return SignalType.STRONG_SELL
        elif k >= 70:
            return SignalType.SELL
        return SignalType.NEUTRAL

    def get_adx_signal(self, adx: float) -> SignalType:
        """Get signal from ADX (trend strength)."""
        if adx >= 50:
            return SignalType.BUY  # Strong trend
        elif adx <= 20:
            return SignalType.NEUTRAL  # Weak trend
        return SignalType.NEUTRAL

    def analyze(
        self, symbol: str, ohlcv: List[List[float]], timeframe: str = "1h"
    ) -> Optional[TradingSignal]:
        """Analyze OHLCV data and generate trading signal.

        Args:
            symbol: Trading pair symbol
            ohlcv: List of [timestamp, open, high, low, close, volume]
            timeframe: Timeframe string

        Returns:
            TradingSignal with all indicators
        """
        if not ohlcv or len(ohlcv) < 30:
            logger.warning(f"Insufficient data for {symbol}")
            return None

        # Extract price data
        timestamps = [candle[0] for candle in ohlcv]
        opens = [candle[1] for candle in ohlcv]
        highs = [candle[2] for candle in ohlcv]
        lows = [candle[3] for candle in ohlcv]
        closes = [candle[4] for candle in ohlcv]
        volumes = [candle[5] for candle in ohlcv]

        current_price = closes[-1]
        indicators = []

        # 1. RSI
        rsi = self.calculate_rsi(closes)
        if rsi is not None:
            signal = self.get_rsi_signal(rsi)
            indicators.append(
                IndicatorSignal(
                    name="RSI",
                    value=rsi,
                    signal=signal,
                    weight=self.weights["RSI"],
                    description=f"RSI at {rsi:.1f}",
                )
            )

        # 2. MACD
        macd_data = self.calculate_macd(closes)
        if macd_data:
            signal = self.get_macd_signal(macd_data)
            indicators.append(
                IndicatorSignal(
                    name="MACD",
                    value=macd_data["histogram"],
                    signal=signal,
                    weight=self.weights["MACD"],
                    description=f"MACD histogram: {macd_data['histogram']:.6f}",
                )
            )

        # 3. Volume
        volume_ratio = self.calculate_volume_signal(volumes)
        if volume_ratio is not None:
            signal = self.get_volume_signal(volume_ratio)
            indicators.append(
                IndicatorSignal(
                    name="Volume",
                    value=volume_ratio,
                    signal=signal,
                    weight=self.weights["Volume"],
                    description=f"Volume ratio: {volume_ratio:.2f}x",
                )
            )

        # 4. MA Cross (9/21)
        ma9 = self.calculate_ema(closes, 9)
        ma21 = self.calculate_ema(closes, 21)
        if ma9 and ma21:
            signal = self.get_ma_cross_signal(ma9, ma21, current_price)
            indicators.append(
                IndicatorSignal(
                    name="MA Cross",
                    value=ma9 - ma21,
                    signal=signal,
                    weight=self.weights["MA_Cross"],
                    description=f"EMA9: {ma9:.2f}, EMA21: {ma21:.2f}",
                )
            )

        # 5. Bollinger Bands
        bollinger = self.calculate_bollinger_bands(closes)
        if bollinger:
            signal = self.get_bollinger_signal(current_price, bollinger)
            indicators.append(
                IndicatorSignal(
                    name="Bollinger",
                    value=(current_price - bollinger["lower"])
                    / (bollinger["upper"] - bollinger["lower"])
                    * 100,
                    signal=signal,
                    weight=self.weights["Bollinger"],
                    description=f"Price at {(current_price - bollinger['lower']) / (bollinger['upper'] - bollinger['lower']) * 100:.1f}% of band",
                )
            )

        # 6. Stochastic
        stoch = self.calculate_stochastic(highs, lows, closes)
        if stoch:
            signal = self.get_stochastic_signal(stoch)
            indicators.append(
                IndicatorSignal(
                    name="Stochastic",
                    value=stoch["k"],
                    signal=signal,
                    weight=self.weights["Stochastic"],
                    description=f"Stoch K: {stoch['k']:.1f}",
                )
            )

        # 7. ADX
        adx = self.calculate_adx(highs, lows, closes)
        if adx is not None:
            signal = self.get_adx_signal(adx)
            indicators.append(
                IndicatorSignal(
                    name="ADX",
                    value=adx,
                    signal=signal,
                    weight=self.weights["ADX"],
                    description=f"Trend strength: {adx:.1f}",
                )
            )

        # Calculate overall signal
        if not indicators:
            return None

        signal_scores = {
            SignalType.STRONG_BUY: 2,
            SignalType.BUY: 1,
            SignalType.NEUTRAL: 0,
            SignalType.SELL: -1,
            SignalType.STRONG_SELL: -2,
        }

        total_weight = sum(ind.weight for ind in indicators)
        weighted_score = (
            sum(signal_scores[ind.signal] * ind.weight for ind in indicators)
            / total_weight
        )

        # Determine overall signal
        if weighted_score >= 1.0:
            overall = SignalType.STRONG_BUY
        elif weighted_score >= 0.3:
            overall = SignalType.BUY
        elif weighted_score <= -1.0:
            overall = SignalType.STRONG_SELL
        elif weighted_score <= -0.3:
            overall = SignalType.SELL
        else:
            overall = SignalType.NEUTRAL

        # Calculate confidence
        buy_count = sum(
            1
            for ind in indicators
            if ind.signal in (SignalType.BUY, SignalType.STRONG_BUY)
        )
        sell_count = sum(
            1
            for ind in indicators
            if ind.signal in (SignalType.SELL, SignalType.STRONG_SELL)
        )
        total = len(indicators)

        if overall in (SignalType.BUY, SignalType.STRONG_BUY):
            confidence = (buy_count / total) * 100
        elif overall in (SignalType.SELL, SignalType.STRONG_SELL):
            confidence = (sell_count / total) * 100
        else:
            confidence = 50

        from datetime import datetime

        return TradingSignal(
            symbol=symbol,
            timeframe=timeframe,
            overall_signal=overall,
            confidence=confidence,
            indicators=indicators,
            price=current_price,
            timestamp=datetime.now().isoformat(),
        )

    def format_signal_summary(self, signals: List[TradingSignal]) -> str:
        """Format multiple signals as summary."""
        if not signals:
            return "❌ No signals available"

        # Sort by confidence
        sorted_signals = sorted(signals, key=lambda s: s.confidence, reverse=True)

        buy_signals = [
            s
            for s in sorted_signals
            if s.overall_signal in (SignalType.BUY, SignalType.STRONG_BUY)
        ]
        sell_signals = [
            s
            for s in sorted_signals
            if s.overall_signal in (SignalType.SELL, SignalType.STRONG_SELL)
        ]

        lines = ["📊 **Trading Signals Summary**\n{'─' * 30}\n"]

        if buy_signals:
            lines.append("🟢 **BUY Signals:**")
            for sig in buy_signals[:5]:
                emoji = "🟢🟢" if sig.overall_signal == SignalType.STRONG_BUY else "🟢"
                lines.append(
                    f"  {emoji} {sig.symbol}: {sig.confidence:.0f}% confidence"
                )

        if sell_signals:
            lines.append("\n🔴 **SELL Signals:**")
            for sig in sell_signals[:5]:
                emoji = "🔴🔴" if sig.overall_signal == SignalType.STRONG_SELL else "🔴"
                lines.append(
                    f"  {emoji} {sig.symbol}: {sig.confidence:.0f}% confidence"
                )

        return "\n".join(lines)
