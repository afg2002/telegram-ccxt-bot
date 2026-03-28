"""Alert Manager - Price and movement alerts system."""

import asyncio
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Alert type definitions."""

    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PERCENT_CHANGE = "percent_change"
    VOLUME_SPIKE = "volume_spike"


@dataclass
class PriceAlert:
    """Represents a price alert."""

    id: str
    user_id: int
    symbol: str
    alert_type: AlertType
    target_value: float
    exchange: Optional[str] = None
    is_active: bool = True
    triggered_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "alert_type": self.alert_type.value,
            "target_value": self.target_value,
            "exchange": self.exchange,
            "is_active": self.is_active,
            "triggered_at": self.triggered_at,
            "created_at": self.created_at,
        }

    def to_message(self) -> str:
        """Format alert as readable message."""
        type_emoji = {
            AlertType.PRICE_ABOVE: "📈",
            AlertType.PRICE_BELOW: "📉",
            AlertType.PERCENT_CHANGE: "📊",
            AlertType.VOLUME_SPIKE: "🔊",
        }

        type_text = {
            AlertType.PRICE_ABOVE: f"Above ${self.target_value:,.2f}",
            AlertType.PRICE_BELOW: f"Below ${self.target_value:,.2f}",
            AlertType.PERCENT_CHANGE: f"Change > {self.target_value}%",
            AlertType.VOLUME_SPIKE: f"Volume spike > {self.target_value}%",
        }

        exchange_text = f" ({self.exchange})" if self.exchange else ""
        status = "✅ Active" if self.is_active else "❌ Triggered"

        return (
            f"{type_emoji[self.alert_type]} **{self.symbol}**{exchange_text}\n"
            f"  {type_text[self.alert_type]}\n"
            f"  {status}"
        )


class AlertManager:
    """Manages price alerts for users."""

    def __init__(self):
        self.alerts: Dict[str, PriceAlert] = {}
        self.user_alerts: Dict[int, List[str]] = {}
        self._alert_counter = 0

    def create_alert(
        self,
        user_id: int,
        symbol: str,
        alert_type: AlertType,
        target_value: float,
        exchange: Optional[str] = None,
    ) -> PriceAlert:
        """Create a new price alert."""
        self._alert_counter += 1
        alert_id = f"alert_{self._alert_counter}"

        alert = PriceAlert(
            id=alert_id,
            user_id=user_id,
            symbol=symbol,
            alert_type=alert_type,
            target_value=target_value,
            exchange=exchange,
        )

        self.alerts[alert_id] = alert

        if user_id not in self.user_alerts:
            self.user_alerts[user_id] = []
        self.user_alerts[user_id].append(alert_id)

        logger.info(f"Created alert {alert_id} for user {user_id}")
        return alert

    def remove_alert(self, alert_id: str, user_id: int) -> bool:
        """Remove an alert."""
        alert = self.alerts.get(alert_id)
        if not alert or alert.user_id != user_id:
            return False

        alert.is_active = False
        if alert_id in self.user_alerts.get(user_id, []):
            self.user_alerts[user_id].remove(alert_id)

        del self.alerts[alert_id]
        logger.info(f"Removed alert {alert_id}")
        return True

    def get_user_alerts(self, user_id: int) -> List[PriceAlert]:
        """Get all alerts for a user."""
        alert_ids = self.user_alerts.get(user_id, [])
        return [self.alerts[aid] for aid in alert_ids if aid in self.alerts]

    async def check_alerts(self, tickers: Dict[str, Dict[str, Dict]]) -> List[Dict]:
        """Check all alerts against current prices.

        Args:
            tickers: {symbol: {exchange: ticker_data}}

        Returns:
            List of triggered alert messages
        """
        triggered = []

        for alert_id, alert in list(self.alerts.items()):
            if not alert.is_active:
                continue

            symbol_tickers = tickers.get(alert.symbol, {})
            if not symbol_tickers:
                continue

            # Get price from specific exchange or best price
            if alert.exchange:
                ticker = symbol_tickers.get(alert.exchange)
                if not ticker:
                    continue
                current_price = ticker.get("last")
            else:
                # Use average price across exchanges
                prices = [
                    t.get("last") for t in symbol_tickers.values() if t.get("last")
                ]
                current_price = sum(prices) / len(prices) if prices else None

            if not current_price:
                continue

            # Check alert conditions
            is_triggered = False

            if alert.alert_type == AlertType.PRICE_ABOVE:
                is_triggered = current_price >= alert.target_value
            elif alert.alert_type == AlertType.PRICE_BELOW:
                is_triggered = current_price <= alert.target_value
            elif alert.alert_type == AlertType.PERCENT_CHANGE:
                # Would need historical data for this
                pass
            elif alert.alert_type == AlertType.VOLUME_SPIKE:
                # Would need historical volume data
                pass

            if is_triggered:
                alert.is_active = False
                alert.triggered_at = datetime.now().isoformat()

                triggered.append(
                    {
                        "alert": alert,
                        "current_price": current_price,
                        "message": self._format_triggered_alert(alert, current_price),
                    }
                )

        return triggered

    def _format_triggered_alert(self, alert: PriceAlert, current_price: float) -> str:
        """Format triggered alert message."""
        return (
            f"🚨 **ALERT TRIGGERED!** 🚨\n\n"
            f"📌 {alert.symbol}\n"
            f"💰 Current Price: ${current_price:,.2f}\n"
            f"🎯 Target: ${alert.target_value:,.2f}\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )

    def format_user_alerts(self, user_id: int) -> str:
        """Format all user alerts as message."""
        alerts = self.get_user_alerts(user_id)

        if not alerts:
            return "📭 You have no active alerts.\n\nUse `/alert BTC/USDT above 50000` to create one."

        header = f"📋 **Your Active Alerts** ({len(alerts)})\n{'─' * 35}\n\n"
        body = "\n\n".join(alert.to_message() for alert in alerts)

        return header + body

    def get_active_count(self) -> int:
        """Get count of active alerts."""
        return sum(1 for a in self.alerts.values() if a.is_active)
