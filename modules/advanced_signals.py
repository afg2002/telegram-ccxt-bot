"""Advanced Signal Engine - Comprehensive technical analysis with 20+ indicators."""

import math
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Signal types with strength levels."""

    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class EntrySignal:
    """Complete entry signal with risk management."""

    symbol: str
    timeframe: str
    signal: SignalType
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_reward_ratio: float
    indicators: Dict[str, Dict]
    volume_spike: bool
    volume_ratio: float
    trend_direction: str
    trend_strength: float
    timestamp: str

    def to_message(self) -> str:
        """Format as Telegram message."""
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

        trend_emoji = (
            "📈"
            if self.trend_direction == "UP"
            else "📉"
            if self.trend_direction == "DOWN"
            else "➡️"
        )

        lines = [
            f"{signal_emoji[self.signal]} **{signal_text[self.signal]}**",
            f"📊 Confidence: {self.confidence:.1f}%",
            f"💰 Entry: ${self.entry_price:,.4f}",
            "",
            "**Risk Management:**",
            f"🛑 Stop Loss: ${self.stop_loss:,.4f}",
            f"🎯 TP1: ${self.take_profit_1:,.4f}",
            f"🎯 TP2: ${self.take_profit_2:,.4f}",
            f"🎯 TP3: ${self.take_profit_3:,.4f}",
            f"📊 R:R = 1:{self.risk_reward_ratio:.2f}",
            "",
            f"{trend_emoji} Trend: {self.trend_direction} ({self.trend_strength:.1f}%)",
        ]

        if self.volume_spike:
            lines.append(f"🔊 Volume Spike: {self.volume_ratio:.1f}x average!")

        lines.extend(["", "**Indicators:**"])

        for name, data in self.indicators.items():
            value = data.get("value", 0)
            signal = data.get("signal", "NEUTRAL")
            ind_emoji = "🟢" if "BUY" in signal else "🔴" if "SELL" in signal else "⚪"
            lines.append(f"  {ind_emoji} {name}: {value:.2f} ({signal})")

        lines.extend(["", f"⏱️ {self.timestamp}"])

        return "\n".join(lines)


class AdvancedSignalEngine:
    """Advanced signal engine with 20+ technical indicators."""

    def __init__(self):
        # Indicator weights
        self.weights = {
            "RSI": 1.2,
            "MACD": 1.3,
            "Stochastic": 1.0,
            "Williams_R": 0.9,
            "CCI": 0.8,
            "MFI": 1.1,
            "OBV": 0.8,
            "VWAP": 1.0,
            "ADX": 1.0,
            "Supertrend": 1.2,
            "Ichimoku": 1.1,
            "Bollinger": 0.9,
            "Keltner": 0.8,
            "ATR": 0.5,
            "CMF": 0.9,
            "EMA_Cross": 1.0,
            "SMA_Cross": 0.8,
            "Parabolic_SAR": 1.0,
            "ROC": 0.7,
            "Momentum": 0.8,
        }

    # ═══════════════════════════════════════════════
    # MOMENTUM INDICATORS
    # ═══════════════════════════════════════════════

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

        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def calculate_macd(
        self,
        prices: List[float],
        fast: int = 12,
        slow: int = 26,
        signal_period: int = 9,
    ) -> Optional[Dict]:
        """Calculate MACD."""
        if len(prices) < slow + signal_period:
            return None

        def ema(data: List[float], period: int) -> List[float]:
            multiplier = 2 / (period + 1)
            ema_values = [sum(data[:period]) / period]
            for price in data[period:]:
                ema_values.append(
                    (price - ema_values[-1]) * multiplier + ema_values[-1]
                )
            return ema_values

        fast_ema = ema(prices, fast)
        slow_ema = ema(prices, slow)

        diff = len(fast_ema) - len(slow_ema)
        fast_ema = fast_ema[diff:]

        macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
        signal_line = ema(macd_line, signal_period)

        diff2 = len(macd_line) - len(signal_line)
        macd_line = macd_line[diff2:]

        histogram = [m - s for m, s in zip(macd_line, signal_line)]

        return {
            "macd": macd_line[-1],
            "signal": signal_line[-1],
            "histogram": histogram[-1],
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
        if len(closes) < k_period + d_period:
            return None

        k_values = []
        for i in range(k_period - 1, len(closes)):
            recent_high = max(highs[i - k_period + 1 : i + 1])
            recent_low = min(lows[i - k_period + 1 : i + 1])

            if recent_high == recent_low:
                k = 50.0
            else:
                k = ((closes[i] - recent_low) / (recent_high - recent_low)) * 100
            k_values.append(k)

        if len(k_values) < d_period:
            return {"k": k_values[-1], "d": k_values[-1]}

        d = sum(k_values[-d_period:]) / d_period
        return {"k": k_values[-1], "d": d}

    def calculate_williams_r(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14,
    ) -> Optional[float]:
        """Calculate Williams %R."""
        if len(closes) < period:
            return None

        highest_high = max(highs[-period:])
        lowest_low = min(lows[-period:])

        if highest_high == lowest_low:
            return -50.0

        return ((highest_high - closes[-1]) / (highest_high - lowest_low)) * -100

    def calculate_cci(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 20,
    ) -> Optional[float]:
        """Calculate Commodity Channel Index."""
        if len(closes) < period:
            return None

        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        sma = sum(typical_prices[-period:]) / period
        mean_deviation = sum(abs(tp - sma) for tp in typical_prices[-period:]) / period

        if mean_deviation == 0:
            return 0.0

        return (typical_prices[-1] - sma) / (0.015 * mean_deviation)

    def calculate_roc(self, prices: List[float], period: int = 12) -> Optional[float]:
        """Calculate Rate of Change."""
        if len(prices) < period + 1:
            return None

        return ((prices[-1] - prices[-period - 1]) / prices[-period - 1]) * 100

    def calculate_momentum(
        self, prices: List[float], period: int = 10
    ) -> Optional[float]:
        """Calculate Momentum."""
        if len(prices) < period + 1:
            return None

        return prices[-1] - prices[-period - 1]

    # ═══════════════════════════════════════════════
    # VOLUME INDICATORS
    # ═══════════════════════════════════════════════

    def calculate_volume_spike(
        self, volumes: List[float], period: int = 20, threshold: float = 2.0
    ) -> Dict:
        """Detect volume spikes."""
        if len(volumes) < period:
            return {"spike": False, "ratio": 1.0}

        avg_volume = sum(volumes[-period:]) / period
        current_volume = volumes[-1]
        ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        return {
            "spike": ratio >= threshold,
            "ratio": ratio,
            "avg_volume": avg_volume,
            "current_volume": current_volume,
        }

    def calculate_obv(
        self, closes: List[float], volumes: List[float]
    ) -> Optional[float]:
        """Calculate On Balance Volume."""
        if len(closes) < 2:
            return None

        obv = 0
        for i in range(1, len(closes)):
            if closes[i] > closes[i - 1]:
                obv += volumes[i]
            elif closes[i] < closes[i - 1]:
                obv -= volumes[i]

        return obv

    def calculate_vwap(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float],
    ) -> Optional[float]:
        """Calculate Volume Weighted Average Price."""
        if len(closes) < 1:
            return None

        cumulative_tp_volume = 0
        cumulative_volume = 0

        for h, l, c, v in zip(highs, lows, closes, volumes):
            tp = (h + l + c) / 3
            cumulative_tp_volume += tp * v
            cumulative_volume += v

        if cumulative_volume == 0:
            return closes[-1]

        return cumulative_tp_volume / cumulative_volume

    def calculate_mfi(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float],
        period: int = 14,
    ) -> Optional[float]:
        """Calculate Money Flow Index."""
        if len(closes) < period + 1:
            return None

        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]

        positive_mf = 0
        negative_mf = 0

        for i in range(1, period + 1):
            idx = -i
            mf = typical_prices[idx] * volumes[idx]

            if typical_prices[idx] > typical_prices[idx - 1]:
                positive_mf += mf
            elif typical_prices[idx] < typical_prices[idx - 1]:
                negative_mf += mf

        if negative_mf == 0:
            return 100.0

        mfr = positive_mf / negative_mf
        return 100 - (100 / (1 + mfr))

    def calculate_cmf(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float],
        period: int = 20,
    ) -> Optional[float]:
        """Calculate Chaikin Money Flow."""
        if len(closes) < period:
            return None

        mf_multiplier = []
        mf_volume = []

        for i in range(len(closes)):
            if highs[i] == lows[i]:
                mf_multiplier.append(0)
            else:
                mf_multiplier.append(
                    ((closes[i] - lows[i]) - (highs[i] - closes[i]))
                    / (highs[i] - lows[i])
                )
            mf_volume.append(mf_multiplier[-1] * volumes[i])

        return (
            sum(mf_volume[-period:]) / sum(volumes[-period:])
            if sum(volumes[-period:]) > 0
            else 0
        )

    # ═══════════════════════════════════════════════
    # TREND INDICATORS
    # ═══════════════════════════════════════════════

    def calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate EMA."""
        if len(prices) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period

        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate SMA."""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    def calculate_adx(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14,
    ) -> Optional[Dict]:
        """Calculate ADX (Average Directional Index)."""
        if len(closes) < period + 1:
            return None

        # Calculate True Range
        tr = []
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i - 1])
            lc = abs(lows[i] - closes[i - 1])
            tr.append(max(hl, hc, lc))

        # Calculate Directional Movement
        plus_dm = []
        minus_dm = []
        for i in range(1, len(highs)):
            up_move = highs[i] - highs[i - 1]
            down_move = lows[i - 1] - lows[i]

            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
            minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)

        if len(tr) < period or len(plus_dm) < period:
            return {"adx": 25.0, "plus_di": 25.0, "minus_di": 25.0}

        # Smooth the values
        atr = sum(tr[-period:]) / period
        plus_di = (sum(plus_dm[-period:]) / atr) * 100 if atr > 0 else 0
        minus_di = (sum(minus_dm[-period:]) / atr) * 100 if atr > 0 else 0

        # Calculate DX
        if plus_di + minus_di == 0:
            dx = 0
        else:
            dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100

        # Simplified ADX
        adx = dx  # Would need more history for proper ADX smoothing

        return {
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
        }

    def calculate_supertrend(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 10,
        multiplier: float = 3.0,
    ) -> Optional[Dict]:
        """Calculate Supertrend indicator."""
        if len(closes) < period:
            return None

        # Calculate ATR
        tr = []
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i - 1])
            lc = abs(lows[i] - closes[i - 1])
            tr.append(max(hl, hc, lc))

        atr = sum(tr[-period:]) / period if len(tr) >= period else tr[-1]

        # Calculate basic upper and lower bands
        hl2 = (highs[-1] + lows[-1]) / 2
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)

        # Determine trend direction
        if closes[-1] > upper_band:
            trend = "UP"
            supertrend = lower_band
        elif closes[-1] < lower_band:
            trend = "DOWN"
            supertrend = upper_band
        else:
            trend = "NEUTRAL"
            supertrend = hl2

        return {
            "supertrend": supertrend,
            "upper_band": upper_band,
            "lower_band": lower_band,
            "trend": trend,
        }

    def calculate_parabolic_sar(
        self,
        highs: List[float],
        lows: List[float],
        af_start: float = 0.02,
        af_increment: float = 0.02,
        af_max: float = 0.2,
    ) -> Optional[float]:
        """Calculate Parabolic SAR."""
        if len(highs) < 2:
            return None

        # Simplified SAR calculation
        sar = lows[0]
        ep = highs[0]
        af = af_start
        trend = 1  # 1 for up, -1 for down

        for i in range(1, len(highs)):
            if trend == 1:
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + af_increment, af_max)
                sar = sar + af * (ep - sar)
                if lows[i] < sar:
                    trend = -1
                    sar = ep
                    ep = lows[i]
                    af = af_start
            else:
                if lows[i] < ep:
                    ep = lows[i]
                    af = min(af + af_increment, af_max)
                sar = sar + af * (ep - sar)
                if highs[i] > sar:
                    trend = 1
                    sar = ep
                    ep = highs[i]
                    af = af_start

        return sar

    # ═══════════════════════════════════════════════
    # VOLATILITY INDICATORS
    # ═══════════════════════════════════════════════

    def calculate_bollinger_bands(
        self, prices: List[float], period: int = 20, std_dev: float = 2.0
    ) -> Optional[Dict]:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return None

        sma = sum(prices[-period:]) / period
        variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
        std = math.sqrt(variance)

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        # Calculate %B (position within bands)
        if upper == lower:
            percent_b = 0.5
        else:
            percent_b = (prices[-1] - lower) / (upper - lower)

        # Calculate bandwidth
        bandwidth = (upper - lower) / sma * 100 if sma > 0 else 0

        return {
            "upper": upper,
            "middle": sma,
            "lower": lower,
            "percent_b": percent_b,
            "bandwidth": bandwidth,
        }

    def calculate_keltner_channel(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 20,
        atr_multiplier: float = 2.0,
    ) -> Optional[Dict]:
        """Calculate Keltner Channel."""
        if len(closes) < period:
            return None

        ema = self.calculate_ema(closes, period)
        if ema is None:
            return None

        # Calculate ATR
        tr = []
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i - 1])
            lc = abs(lows[i] - closes[i - 1])
            tr.append(max(hl, hc, lc))

        atr = sum(tr[-period:]) / period if len(tr) >= period else tr[-1]

        upper = ema + (atr * atr_multiplier)
        lower = ema - (atr * atr_multiplier)

        return {
            "upper": upper,
            "middle": ema,
            "lower": lower,
        }

    def calculate_atr(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14,
    ) -> Optional[float]:
        """Calculate Average True Range."""
        if len(closes) < period + 1:
            return None

        tr = []
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i - 1])
            lc = abs(lows[i] - closes[i - 1])
            tr.append(max(hl, hc, lc))

        return sum(tr[-period:]) / period

    # ═══════════════════════════════════════════════
    # ICHIMOKU CLOUD
    # ═══════════════════════════════════════════════

    def calculate_ichimoku(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        tenkan_period: int = 9,
        kijun_period: int = 26,
        senkou_b_period: int = 52,
    ) -> Optional[Dict]:
        """Calculate Ichimoku Cloud."""
        if len(closes) < senkou_b_period:
            return None

        # Tenkan-sen (Conversion Line)
        tenkan_high = max(highs[-tenkan_period:])
        tenkan_low = min(lows[-tenkan_period:])
        tenkan = (tenkan_high + tenkan_low) / 2

        # Kijun-sen (Base Line)
        kijun_high = max(highs[-kijun_period:])
        kijun_low = min(lows[-kijun_period:])
        kijun = (kijun_high + kijun_low) / 2

        # Senkou Span A (Leading Span A)
        senkou_a = (tenkan + kijun) / 2

        # Senkou Span B (Leading Span B)
        senkou_b_high = max(highs[-senkou_b_period:])
        senkou_b_low = min(lows[-senkou_b_period:])
        senkou_b = (senkou_b_high + senkou_b_low) / 2

        # Chikou Span (Lagging Span)
        chikou = closes[-1]

        # Determine signal
        price = closes[-1]
        if price > senkou_a and price > senkou_b:
            signal = "BULLISH"
        elif price < senkou_a and price < senkou_b:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        return {
            "tenkan": tenkan,
            "kijun": kijun,
            "senkou_a": senkou_a,
            "senkou_b": senkou_b,
            "chikou": chikou,
            "signal": signal,
        }

    # ═══════════════════════════════════════════════
    # SIGNAL GENERATION
    # ═══════════════════════════════════════════════

    def get_rsi_signal(self, rsi: float) -> str:
        """Get signal from RSI."""
        if rsi <= 25:
            return "STRONG_BUY"
        elif rsi <= 35:
            return "BUY"
        elif rsi >= 75:
            return "STRONG_SELL"
        elif rsi >= 65:
            return "SELL"
        return "NEUTRAL"

    def get_macd_signal(self, macd_data: Dict) -> str:
        """Get signal from MACD."""
        histogram = macd_data.get("histogram", 0)
        if histogram > 0:
            return "BUY"
        elif histogram < 0:
            return "SELL"
        return "NEUTRAL"

    def get_stochastic_signal(self, stoch: Dict) -> str:
        """Get signal from Stochastic."""
        k = stoch.get("k", 50)
        if k <= 20:
            return "STRONG_BUY"
        elif k <= 30:
            return "BUY"
        elif k >= 80:
            return "STRONG_SELL"
        elif k >= 70:
            return "SELL"
        return "NEUTRAL"

    def get_williams_r_signal(self, wr: float) -> str:
        """Get signal from Williams %R."""
        if wr <= -80:
            return "STRONG_BUY"
        elif wr <= -70:
            return "BUY"
        elif wr >= -20:
            return "STRONG_SELL"
        elif wr >= -30:
            return "SELL"
        return "NEUTRAL"

    def get_mfi_signal(self, mfi: float) -> str:
        """Get signal from MFI."""
        if mfi <= 20:
            return "STRONG_BUY"
        elif mfi <= 30:
            return "BUY"
        elif mfi >= 80:
            return "STRONG_SELL"
        elif mfi >= 70:
            return "SELL"
        return "NEUTRAL"

    def get_bollinger_signal(self, price: float, bands: Dict) -> str:
        """Get signal from Bollinger Bands."""
        percent_b = bands.get("percent_b", 0.5)
        if percent_b <= 0:
            return "STRONG_BUY"
        elif percent_b <= 0.2:
            return "BUY"
        elif percent_b >= 1:
            return "STRONG_SELL"
        elif percent_b >= 0.8:
            return "SELL"
        return "NEUTRAL"

    def get_adx_signal(self, adx_data: Dict) -> str:
        """Get signal from ADX."""
        adx = adx_data.get("adx", 0)
        plus_di = adx_data.get("plus_di", 0)
        minus_di = adx_data.get("minus_di", 0)

        if adx >= 25:
            if plus_di > minus_di:
                return "BUY"
            else:
                return "SELL"
        return "NEUTRAL"

    def get_supertrend_signal(self, supertrend: Dict) -> str:
        """Get signal from Supertrend."""
        trend = supertrend.get("trend", "NEUTRAL")
        if trend == "UP":
            return "BUY"
        elif trend == "DOWN":
            return "SELL"
        return "NEUTRAL"

    def get_ichimoku_signal(self, ichimoku: Dict) -> str:
        """Get signal from Ichimoku."""
        signal = ichimoku.get("signal", "NEUTRAL")
        if signal == "BULLISH":
            return "BUY"
        elif signal == "BEARISH":
            return "SELL"
        return "NEUTRAL"

    # ═══════════════════════════════════════════════
    # ENTRY/EXIT LEVELS
    # ═══════════════════════════════════════════════

    def calculate_entry_levels(
        self,
        price: float,
        atr: float,
        signal: SignalType,
        bollinger: Optional[Dict] = None,
    ) -> Dict:
        """Calculate entry, stop loss, and take profit levels."""
        if atr == 0:
            atr = price * 0.02  # Default 2% if ATR unavailable

        if signal in (SignalType.BUY, SignalType.STRONG_BUY):
            entry = price
            stop_loss = price - (atr * 1.5)
            tp1 = price + (atr * 1.5)  # 1:1 R:R
            tp2 = price + (atr * 3.0)  # 1:2 R:R
            tp3 = price + (atr * 4.5)  # 1:3 R:R

            # Use Bollinger upper band if available
            if bollinger and bollinger.get("upper"):
                tp2 = max(tp2, bollinger["upper"])

        elif signal in (SignalType.SELL, SignalType.STRONG_SELL):
            entry = price
            stop_loss = price + (atr * 1.5)
            tp1 = price - (atr * 1.5)
            tp2 = price - (atr * 3.0)
            tp3 = price - (atr * 4.5)

            if bollinger and bollinger.get("lower"):
                tp2 = min(tp2, bollinger["lower"])

        else:
            entry = price
            stop_loss = price - (atr * 1.5)
            tp1 = price + (atr * 1.5)
            tp2 = price + (atr * 3.0)
            tp3 = price + (atr * 4.5)

        # Calculate Risk:Reward
        risk = abs(entry - stop_loss)
        reward = abs(tp2 - entry)
        rr_ratio = reward / risk if risk > 0 else 0

        return {
            "entry": entry,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "risk_reward": rr_ratio,
        }

    # ═══════════════════════════════════════════════
    # MAIN ANALYSIS
    # ═══════════════════════════════════════════════

    def analyze(
        self, symbol: str, ohlcv: List[List[float]], timeframe: str = "1h"
    ) -> Optional[EntrySignal]:
        """Comprehensive analysis with all indicators."""
        if not ohlcv or len(ohlcv) < 52:  # Need at least 52 for Ichimoku
            logger.warning(
                f"Insufficient data for {symbol} (need 52+, got {len(ohlcv) if ohlcv else 0})"
            )
            return None

        # Extract data
        timestamps = [c[0] for c in ohlcv]
        opens = [c[1] for c in ohlcv]
        highs = [c[2] for c in ohlcv]
        lows = [c[3] for c in ohlcv]
        closes = [c[4] for c in ohlcv]
        volumes = [c[5] for c in ohlcv]

        current_price = closes[-1]
        indicators = {}
        signal_scores = {
            "STRONG_BUY": 2,
            "BUY": 1,
            "NEUTRAL": 0,
            "SELL": -1,
            "STRONG_SELL": -2,
        }

        # 1. RSI
        rsi = self.calculate_rsi(closes)
        if rsi is not None:
            signal = self.get_rsi_signal(rsi)
            indicators["RSI"] = {"value": rsi, "signal": signal}

        # 2. MACD
        macd_data = self.calculate_macd(closes)
        if macd_data:
            signal = self.get_macd_signal(macd_data)
            indicators["MACD"] = {"value": macd_data["histogram"], "signal": signal}

        # 3. Stochastic
        stoch = self.calculate_stochastic(highs, lows, closes)
        if stoch:
            signal = self.get_stochastic_signal(stoch)
            indicators["Stochastic"] = {"value": stoch["k"], "signal": signal}

        # 4. Williams %R
        wr = self.calculate_williams_r(highs, lows, closes)
        if wr is not None:
            signal = self.get_williams_r_signal(wr)
            indicators["Williams_R"] = {"value": wr, "signal": signal}

        # 5. CCI
        cci = self.calculate_cci(highs, lows, closes)
        if cci is not None:
            if cci <= -100:
                signal = "STRONG_BUY"
            elif cci <= -50:
                signal = "BUY"
            elif cci >= 100:
                signal = "STRONG_SELL"
            elif cci >= 50:
                signal = "SELL"
            else:
                signal = "NEUTRAL"
            indicators["CCI"] = {"value": cci, "signal": signal}

        # 6. MFI
        mfi = self.calculate_mfi(highs, lows, closes, volumes)
        if mfi is not None:
            signal = self.get_mfi_signal(mfi)
            indicators["MFI"] = {"value": mfi, "signal": signal}

        # 7. Volume Analysis
        volume_data = self.calculate_volume_spike(volumes)
        volume_spike = volume_data["spike"]
        volume_ratio = volume_data["ratio"]

        if volume_ratio >= 2.0:
            volume_signal = "STRONG_BUY"
        elif volume_ratio >= 1.5:
            volume_signal = "BUY"
        elif volume_ratio <= 0.5:
            volume_signal = "SELL"
        else:
            volume_signal = "NEUTRAL"
        indicators["Volume"] = {"value": volume_ratio, "signal": volume_signal}

        # 8. OBV
        obv = self.calculate_obv(closes, volumes)
        if obv is not None:
            # Simplified OBV signal based on recent trend
            indicators["OBV"] = {"value": obv, "signal": "NEUTRAL"}

        # 9. VWAP
        vwap = self.calculate_vwap(highs, lows, closes, volumes)
        if vwap is not None:
            if current_price > vwap:
                signal = "BUY"
            elif current_price < vwap:
                signal = "SELL"
            else:
                signal = "NEUTRAL"
            indicators["VWAP"] = {"value": vwap, "signal": signal}

        # 10. CMF
        cmf = self.calculate_cmf(highs, lows, closes, volumes)
        if cmf is not None:
            if cmf >= 0.1:
                signal = "BUY"
            elif cmf <= -0.1:
                signal = "SELL"
            else:
                signal = "NEUTRAL"
            indicators["CMF"] = {"value": cmf, "signal": signal}

        # 11. ADX
        adx_data = self.calculate_adx(highs, lows, closes)
        if adx_data:
            signal = self.get_adx_signal(adx_data)
            indicators["ADX"] = {"value": adx_data["adx"], "signal": signal}

        # 12. Supertrend
        supertrend = self.calculate_supertrend(highs, lows, closes)
        if supertrend:
            signal = self.get_supertrend_signal(supertrend)
            indicators["Supertrend"] = {
                "value": supertrend["supertrend"],
                "signal": signal,
            }

        # 13. Bollinger Bands
        bollinger = self.calculate_bollinger_bands(closes)
        if bollinger:
            signal = self.get_bollinger_signal(current_price, bollinger)
            indicators["Bollinger"] = {
                "value": bollinger["percent_b"] * 100,
                "signal": signal,
            }

        # 14. Keltner Channel
        keltner = self.calculate_keltner_channel(highs, lows, closes)
        if keltner:
            if current_price < keltner["lower"]:
                signal = "BUY"
            elif current_price > keltner["upper"]:
                signal = "SELL"
            else:
                signal = "NEUTRAL"
            indicators["Keltner"] = {"value": current_price, "signal": signal}

        # 15. ATR
        atr = self.calculate_atr(highs, lows, closes)
        if atr is not None:
            indicators["ATR"] = {"value": atr, "signal": "NEUTRAL"}

        # 16. Ichimoku
        ichimoku = self.calculate_ichimoku(highs, lows, closes)
        if ichimoku:
            signal = self.get_ichimoku_signal(ichimoku)
            indicators["Ichimoku"] = {"value": ichimoku["tenkan"], "signal": signal}

        # 17. EMA Cross (9/21)
        ema9 = self.calculate_ema(closes, 9)
        ema21 = self.calculate_ema(closes, 21)
        if ema9 and ema21:
            if ema9 > ema21 and current_price > ema9:
                signal = "BUY"
            elif ema9 < ema21 and current_price < ema9:
                signal = "SELL"
            else:
                signal = "NEUTRAL"
            indicators["EMA_Cross"] = {"value": ema9 - ema21, "signal": signal}

        # 18. Parabolic SAR
        sar = self.calculate_parabolic_sar(highs, lows)
        if sar is not None:
            if current_price > sar:
                signal = "BUY"
            else:
                signal = "SELL"
            indicators["Parabolic_SAR"] = {"value": sar, "signal": signal}

        # 19. ROC
        roc = self.calculate_roc(closes)
        if roc is not None:
            if roc >= 5:
                signal = "BUY"
            elif roc <= -5:
                signal = "SELL"
            else:
                signal = "NEUTRAL"
            indicators["ROC"] = {"value": roc, "signal": signal}

        # 20. Momentum
        momentum = self.calculate_momentum(closes)
        if momentum is not None:
            if momentum > 0:
                signal = "BUY"
            elif momentum < 0:
                signal = "SELL"
            else:
                signal = "NEUTRAL"
            indicators["Momentum"] = {"value": momentum, "signal": signal}

        # Calculate overall signal
        if not indicators:
            return None

        total_weight = sum(self.weights.get(k, 1.0) for k in indicators.keys())
        weighted_score = (
            sum(
                signal_scores.get(indicators[k].get("signal", "NEUTRAL"), 0)
                * self.weights.get(k, 1.0)
                for k in indicators.keys()
            )
            / total_weight
            if total_weight > 0
            else 0
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
            1 for ind in indicators.values() if "BUY" in ind.get("signal", "")
        )
        sell_count = sum(
            1 for ind in indicators.values() if "SELL" in ind.get("signal", "")
        )
        total = len(indicators)

        if overall in (SignalType.BUY, SignalType.STRONG_BUY):
            confidence = (buy_count / total) * 100
        elif overall in (SignalType.SELL, SignalType.STRONG_SELL):
            confidence = (sell_count / total) * 100
        else:
            confidence = 50

        # Calculate trend
        if ema9 and ema21:
            if ema9 > ema21:
                trend_direction = "UP"
                trend_strength = ((ema9 - ema21) / ema21) * 100
            elif ema9 < ema21:
                trend_direction = "DOWN"
                trend_strength = ((ema21 - ema9) / ema21) * 100
            else:
                trend_direction = "NEUTRAL"
                trend_strength = 0
        else:
            trend_direction = "NEUTRAL"
            trend_strength = 0

        # Calculate entry levels
        atr_value = atr if atr else current_price * 0.02
        levels = self.calculate_entry_levels(
            current_price, atr_value, overall, bollinger
        )

        return EntrySignal(
            symbol=symbol,
            timeframe=timeframe,
            signal=overall,
            confidence=confidence,
            entry_price=levels["entry"],
            stop_loss=levels["stop_loss"],
            take_profit_1=levels["tp1"],
            take_profit_2=levels["tp2"],
            take_profit_3=levels["tp3"],
            risk_reward_ratio=levels["risk_reward"],
            indicators=indicators,
            volume_spike=volume_spike,
            volume_ratio=volume_ratio,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def format_signal_summary(self, signals: List[EntrySignal]) -> str:
        """Format multiple signals as summary."""
        if not signals:
            return "❌ No signals available"

        buy_signals = [
            s for s in signals if s.signal in (SignalType.BUY, SignalType.STRONG_BUY)
        ]
        sell_signals = [
            s for s in signals if s.signal in (SignalType.SELL, SignalType.STRONG_SELL)
        ]

        lines = ["📊 **Trading Signals Summary**\n" + "─" * 30 + "\n"]

        if buy_signals:
            buy_signals.sort(key=lambda s: s.confidence, reverse=True)
            lines.append("🟢 **BUY Signals:**")
            for sig in buy_signals[:5]:
                emoji = "🟢🟢" if sig.signal == SignalType.STRONG_BUY else "🟢"
                lines.append(
                    f"  {emoji} **{sig.symbol}**: {sig.confidence:.0f}% | "
                    f"Entry: ${sig.entry_price:,.2f} | "
                    f"R:R 1:{sig.risk_reward_ratio:.1f}"
                )

        if sell_signals:
            sell_signals.sort(key=lambda s: s.confidence, reverse=True)
            lines.append("\n🔴 **SELL Signals:**")
            for sig in sell_signals[:5]:
                emoji = "🔴🔴" if sig.signal == SignalType.STRONG_SELL else "🔴"
                lines.append(
                    f"  {emoji} **{sig.symbol}**: {sig.confidence:.0f}% | "
                    f"Entry: ${sig.entry_price:,.2f} | "
                    f"R:R 1:{sig.risk_reward_ratio:.1f}"
                )

        return "\n".join(lines)
