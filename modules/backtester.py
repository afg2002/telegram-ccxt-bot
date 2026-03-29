"""Simple Backtesting Framework - Test trading signals against historical data."""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Represents a single trade."""

    symbol: str
    entry_time: str
    entry_price: float
    direction: str  # "LONG" or "SHORT"
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    stop_loss: float = 0
    take_profit: float = 0
    pnl: float = 0
    pnl_percent: float = 0
    status: str = "OPEN"  # "OPEN", "CLOSED", "STOPPED"
    exit_reason: str = ""


@dataclass
class BacktestResult:
    """Backtest results."""

    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_percent: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_percent: float
    sharpe_ratio: float
    trades: List[Trade]

    def to_message(self) -> str:
        """Format as Telegram message."""
        profit_emoji = "📈" if self.total_pnl >= 0 else "📉"

        lines = [
            f"📊 **Backtest Results**",
            f"🏷️ {self.symbol} ({self.timeframe})",
            f"📅 {self.start_date} → {self.end_date}",
            "─" * 30,
            "",
            f"{profit_emoji} **Performance:**",
            f"  Total P&L: ${self.total_pnl:,.2f} ({self.total_pnl_percent:+.2f}%)",
            f"  Win Rate: {self.win_rate:.1f}%",
            f"  Profit Factor: {self.profit_factor:.2f}",
            "",
            f"📈 **Trade Stats:**",
            f"  Total Trades: {self.total_trades}",
            f"  Winning: {self.winning_trades} | Losing: {self.losing_trades}",
            f"  Avg Win: ${self.avg_win:,.2f}",
            f"  Avg Loss: ${self.avg_loss:,.2f}",
            "",
            f"📉 **Risk Metrics:**",
            f"  Max Drawdown: ${self.max_drawdown:,.2f} ({self.max_drawdown_percent:.2f}%)",
            f"  Sharpe Ratio: {self.sharpe_ratio:.2f}",
        ]

        if self.total_trades == 0:
            lines.extend(["", "⚠️ No trades executed during backtest period"])

        return "\n".join(lines)


class Backtester:
    """Simple backtesting engine."""

    def __init__(self, signal_engine):
        self.signal_engine = signal_engine

    def run_backtest(
        self,
        symbol: str,
        ohlcv: List[List[float]],
        timeframe: str = "1h",
        initial_capital: float = 10000,
        risk_per_trade: float = 0.02,  # 2% risk per trade
        use_stop_loss: bool = True,
        use_take_profit: bool = True,
    ) -> BacktestResult:
        """Run backtest on historical data.

        Args:
            symbol: Trading pair
            ohlcv: List of [timestamp, open, high, low, close, volume]
            timeframe: Timeframe string
            initial_capital: Starting capital
            risk_per_trade: Risk per trade as fraction of capital
            use_stop_loss: Enable stop loss
            use_take_profit: Enable take profit

        Returns:
            BacktestResult with performance metrics
        """
        from modules.advanced_signals import SignalType

        if not ohlcv or len(ohlcv) < 100:
            return self._empty_result(symbol, timeframe, ohlcv)

        trades: List[Trade] = []
        capital = initial_capital
        peak_capital = initial_capital
        max_drawdown = 0
        max_drawdown_percent = 0
        current_trade: Optional[Trade] = None

        # Use sliding window for signals
        window_size = 100
        for i in range(window_size, len(ohlcv)):
            window = ohlcv[i - window_size : i + 1]
            current_candle = ohlcv[i]
            current_price = current_candle[4]  # close price
            current_time = datetime.fromtimestamp(current_candle[0] / 1000).strftime(
                "%Y-%m-%d %H:%M"
            )

            # Generate signal
            signal = self.signal_engine.analyze(symbol, window, timeframe)
            if not signal:
                continue

            # Check existing trade
            if current_trade:
                exit_trade = False
                exit_price = current_price
                exit_reason = ""

                # Check stop loss
                if use_stop_loss and current_trade.direction == "LONG":
                    if current_candle[3] <= current_trade.stop_loss:  # low <= SL
                        exit_price = current_trade.stop_loss
                        exit_trade = True
                        exit_reason = "Stop Loss"
                elif use_stop_loss and current_trade.direction == "SHORT":
                    if current_candle[2] >= current_trade.stop_loss:  # high >= SL
                        exit_price = current_trade.stop_loss
                        exit_trade = True
                        exit_reason = "Stop Loss"

                # Check take profit
                if use_take_profit and current_trade.direction == "LONG":
                    if current_candle[2] >= current_trade.take_profit:  # high >= TP
                        exit_price = current_trade.take_profit
                        exit_trade = True
                        exit_reason = "Take Profit"
                elif use_take_profit and current_trade.direction == "SHORT":
                    if current_candle[3] <= current_trade.take_profit:  # low <= TP
                        exit_price = current_trade.take_profit
                        exit_trade = True
                        exit_reason = "Take Profit"

                # Exit on opposite signal
                if (
                    signal.signal in (SignalType.SELL, SignalType.STRONG_SELL)
                    and current_trade.direction == "LONG"
                ):
                    exit_trade = True
                    exit_reason = "Signal Reversal"
                elif (
                    signal.signal in (SignalType.BUY, SignalType.STRONG_BUY)
                    and current_trade.direction == "SHORT"
                ):
                    exit_trade = True
                    exit_reason = "Signal Reversal"

                if exit_trade:
                    current_trade.exit_time = current_time
                    current_trade.exit_price = exit_price
                    current_trade.status = (
                        "STOPPED" if "Stop" in exit_reason else "CLOSED"
                    )
                    current_trade.exit_reason = exit_reason

                    # Calculate P&L
                    if current_trade.direction == "LONG":
                        current_trade.pnl = (
                            (exit_price - current_trade.entry_price)
                            / current_trade.entry_price
                            * capital
                            * risk_per_trade
                        )
                    else:
                        current_trade.pnl = (
                            (current_trade.entry_price - exit_price)
                            / current_trade.entry_price
                            * capital
                            * risk_per_trade
                        )

                    current_trade.pnl_percent = (current_trade.pnl / capital) * 100
                    capital += current_trade.pnl

                    trades.append(current_trade)
                    current_trade = None

            # Open new trade on signal
            if current_trade is None:
                if signal.signal in (SignalType.BUY, SignalType.STRONG_BUY):
                    current_trade = Trade(
                        symbol=symbol,
                        entry_time=current_time,
                        entry_price=current_price,
                        direction="LONG",
                        stop_loss=signal.stop_loss,
                        take_profit=signal.take_profit_2,
                    )
                elif signal.signal in (SignalType.SELL, SignalType.STRONG_SELL):
                    current_trade = Trade(
                        symbol=symbol,
                        entry_time=current_time,
                        entry_price=current_price,
                        direction="SHORT",
                        stop_loss=signal.stop_loss,
                        take_profit=signal.take_profit_2,
                    )

            # Track drawdown
            if capital > peak_capital:
                peak_capital = capital

            current_drawdown = peak_capital - capital
            current_drawdown_percent = (current_drawdown / peak_capital) * 100

            if current_drawdown > max_drawdown:
                max_drawdown = current_drawdown
                max_drawdown_percent = current_drawdown_percent

        # Close any remaining trade
        if current_trade:
            current_trade.exit_time = datetime.fromtimestamp(
                ohlcv[-1][0] / 1000
            ).strftime("%Y-%m-%d %H:%M")
            current_trade.exit_price = ohlcv[-1][4]
            current_trade.status = "CLOSED"
            current_trade.exit_reason = "End of Data"

            if current_trade.direction == "LONG":
                current_trade.pnl = (
                    (current_trade.exit_price - current_trade.entry_price)
                    / current_trade.entry_price
                    * capital
                    * risk_per_trade
                )
            else:
                current_trade.pnl = (
                    (current_trade.entry_price - current_trade.exit_price)
                    / current_trade.entry_price
                    * capital
                    * risk_per_trade
                )

            current_trade.pnl_percent = (current_trade.pnl / capital) * 100
            capital += current_trade.pnl
            trades.append(current_trade)

        # Calculate metrics
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]

        total_pnl = capital - initial_capital
        total_pnl_percent = (total_pnl / initial_capital) * 100

        win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0

        avg_win = (
            sum(t.pnl for t in winning_trades) / len(winning_trades)
            if winning_trades
            else 0
        )
        avg_loss = (
            abs(sum(t.pnl for t in losing_trades) / len(losing_trades))
            if losing_trades
            else 0
        )

        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Simplified Sharpe Ratio
        if trades:
            returns = [t.pnl_percent for t in trades]
            avg_return = sum(returns) / len(returns)
            std_return = (
                sum((r - avg_return) ** 2 for r in returns) / len(returns)
            ) ** 0.5
            sharpe_ratio = (
                (avg_return / std_return) * (252**0.5) if std_return > 0 else 0
            )
        else:
            sharpe_ratio = 0

        start_date = datetime.fromtimestamp(ohlcv[0][0] / 1000).strftime("%Y-%m-%d")
        end_date = datetime.fromtimestamp(ohlcv[-1][0] / 1000).strftime("%Y-%m-%d")

        return BacktestResult(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            sharpe_ratio=sharpe_ratio,
            trades=trades,
        )

    def _empty_result(self, symbol: str, timeframe: str, ohlcv: List) -> BacktestResult:
        """Return empty result."""
        start_date = (
            datetime.fromtimestamp(ohlcv[0][0] / 1000).strftime("%Y-%m-%d")
            if ohlcv
            else "N/A"
        )
        end_date = (
            datetime.fromtimestamp(ohlcv[-1][0] / 1000).strftime("%Y-%m-%d")
            if ohlcv
            else "N/A"
        )

        return BacktestResult(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0,
            total_pnl=0,
            total_pnl_percent=0,
            avg_win=0,
            avg_loss=0,
            profit_factor=0,
            max_drawdown=0,
            max_drawdown_percent=0,
            sharpe_ratio=0,
            trades=[],
        )
