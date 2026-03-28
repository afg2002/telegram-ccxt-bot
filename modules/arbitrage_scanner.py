"""Arbitrage Scanner - Detects price differences across exchanges."""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity."""

    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_percent: float
    timestamp: str

    def to_message(self) -> str:
        """Format as readable message."""
        emoji = "🟢" if self.spread_percent >= 1.0 else "🟡"
        return (
            f"{emoji} **{self.symbol}**\n"
            f"  📥 Buy: {self.buy_exchange} @ ${self.buy_price:,.6f}\n"
            f"  📤 Sell: {self.sell_exchange} @ ${self.sell_price:,.6f}\n"
            f"  💰 Spread: {self.spread_percent:.2f}%\n"
            f"  ⏱️ {self.timestamp}"
        )


class ArbitrageScanner:
    """Scans for arbitrage opportunities across exchanges."""

    def __init__(self, exchange_manager, threshold: float = 0.5):
        self.exchange_manager = exchange_manager
        self.threshold = threshold  # Minimum spread percentage
        self.last_opportunities: Dict[str, ArbitrageOpportunity] = {}
        self.opportunity_history: List[ArbitrageOpportunity] = []
        self._all_pairs_cache: Dict[str, Set[str]] = {}  # exchange -> set of symbols

    async def get_all_available_pairs(
        self, exchange_names: Optional[List[str]] = None
    ) -> Set[str]:
        """Get all available trading pairs across exchanges."""
        if exchange_names is None:
            exchange_names = self.exchange_manager.get_healthy_exchanges()

        all_pairs = set()

        for exchange_name in exchange_names:
            exchange = self.exchange_manager.get_exchange(exchange_name)
            if not exchange:
                continue

            try:
                # Get markets from cache or load
                if hasattr(exchange, "markets") and exchange.markets:
                    markets = exchange.markets
                else:
                    markets = exchange.load_markets()

                # Filter for USDT pairs (most liquid)
                usdt_pairs = [
                    symbol
                    for symbol in markets.keys()
                    if symbol.endswith("/USDT") and markets[symbol].get("active", True)
                ]
                all_pairs.update(usdt_pairs)

                # Cache for this exchange
                self._all_pairs_cache[exchange_name] = set(usdt_pairs)
                logger.info(
                    f"[ARB] {exchange_name}: {len(usdt_pairs)} USDT pairs available"
                )

            except Exception as e:
                logger.error(f"[ARB] Error loading markets from {exchange_name}: {e}")

        logger.info(f"[ARB] Total unique pairs across exchanges: {len(all_pairs)}")
        return all_pairs

    async def scan(
        self,
        symbols: Optional[List[str]] = None,
        exchange_names: Optional[List[str]] = None,
        max_pairs: int = 100,
    ) -> List[ArbitrageOpportunity]:
        """Scan for arbitrage opportunities across exchanges.

        Args:
            symbols: Specific symbols to scan. If None, scans all available pairs.
            exchange_names: Exchanges to scan. If None, uses all healthy exchanges.
            max_pairs: Maximum number of pairs to scan (for performance)

        Returns:
            List of arbitrage opportunities found
        """
        opportunities = []

        if exchange_names is None:
            exchange_names = self.exchange_manager.get_healthy_exchanges()

        if len(exchange_names) < 2:
            logger.warning("[ARB] Need at least 2 exchanges for arbitrage scanning")
            return []

        # If no symbols specified, get all available pairs
        if symbols is None:
            all_pairs = await self.get_all_available_pairs(exchange_names)
            symbols = list(all_pairs)[:max_pairs]  # Limit for performance
            logger.info(
                f"[ARB] Scanning {len(symbols)} pairs across {len(exchange_names)} exchanges"
            )

        # Fetch all tickers concurrently
        tickers = await self.exchange_manager.fetch_all_tickers(symbols, exchange_names)

        for symbol, exchange_tickers in tickers.items():
            opp = self._find_opportunity(symbol, exchange_tickers)
            if opp:
                opportunities.append(opp)

        # Sort by spread percentage (highest first)
        opportunities.sort(key=lambda x: x.spread_percent, reverse=True)

        # Store new opportunities
        for opp in opportunities:
            if opp.symbol not in self.last_opportunities:
                self.opportunity_history.append(opp)
            self.last_opportunities[opp.symbol] = opp

        logger.info(
            f"[ARB] Found {len(opportunities)} opportunities above {self.threshold}%"
        )
        return opportunities

    def _find_opportunity(
        self, symbol: str, exchange_tickers: Dict[str, Dict]
    ) -> Optional[ArbitrageOpportunity]:
        """Find best arbitrage opportunity for a symbol."""
        # Filter out internal keys
        valid_tickers = {
            k: v
            for k, v in exchange_tickers.items()
            if not k.startswith("_") and isinstance(v, dict)
        }

        if len(valid_tickers) < 2:
            return None

        # Extract valid prices
        prices = {}
        for exchange, ticker in valid_tickers.items():
            last_price = ticker.get("last")
            if last_price and last_price > 0:
                prices[exchange] = last_price

        if len(prices) < 2:
            return None

        # Find min and max prices
        buy_exchange = min(prices, key=prices.get)
        sell_exchange = max(prices, key=prices.get)

        buy_price = prices[buy_exchange]
        sell_price = prices[sell_exchange]

        # Calculate spread
        spread_percent = ((sell_price - buy_price) / buy_price) * 100

        # Only return if above threshold
        if spread_percent >= self.threshold:
            return ArbitrageOpportunity(
                symbol=symbol,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                spread_percent=spread_percent,
                timestamp=datetime.now().strftime("%H:%M:%S"),
            )

        return None

    def get_top_opportunities(self, limit: int = 10) -> List[ArbitrageOpportunity]:
        """Get top opportunities by spread."""
        sorted_opps = sorted(
            self.last_opportunities.values(),
            key=lambda x: x.spread_percent,
            reverse=True,
        )
        return sorted_opps[:limit]

    def format_opportunities(
        self, opportunities: List[ArbitrageOpportunity], max_display: int = 10
    ) -> str:
        """Format opportunities as message."""
        if not opportunities:
            return (
                f"❌ No arbitrage opportunities found above {self.threshold}%\n\n"
                f"💡 Try lowering the threshold with /settings"
            )

        display_opps = opportunities[:max_display]

        header = (
            f"📊 **Arbitrage Opportunities** (>{self.threshold}%)\n"
            f"Found: {len(opportunities)} | Showing: {len(display_opps)}\n"
            f"{'─' * 35}\n\n"
        )

        body = "\n\n".join(opp.to_message() for opp in display_opps)

        footer = ""
        if len(opportunities) > max_display:
            footer = f"\n\n... and {len(opportunities) - max_display} more"

        return header + body + footer

    async def continuous_scan(
        self,
        symbols: Optional[List[str]] = None,
        interval: int = 30,
        callback=None,
        max_pairs: int = 100,
    ):
        """Run continuous arbitrage scanning."""
        logger.info(
            f"[ARB] Starting continuous scan every {interval}s (max {max_pairs} pairs)"
        )

        while True:
            try:
                opportunities = await self.scan(symbols=symbols, max_pairs=max_pairs)

                if opportunities and callback:
                    await callback(opportunities)

            except Exception as e:
                logger.error(f"[ARB] Error in continuous scan: {e}")

            await asyncio.sleep(interval)

    def get_statistics(self) -> Dict:
        """Get scanning statistics."""
        if not self.opportunity_history:
            return {
                "total_opportunities": 0,
                "max_spread": 0,
                "avg_spread": 0,
                "active_pairs": len(self.last_opportunities),
            }

        spreads = [opp.spread_percent for opp in self.opportunity_history]
        return {
            "total_opportunities": len(self.opportunity_history),
            "max_spread": max(spreads),
            "avg_spread": sum(spreads) / len(spreads),
            "active_pairs": len(self.last_opportunities),
        }

    def clear_history(self):
        """Clear opportunity history."""
        self.opportunity_history.clear()
        self.last_opportunities.clear()
