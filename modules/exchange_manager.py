"""Exchange Manager - Handles all CCXT exchange interactions with health tracking."""

import ccxt
import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ExchangeStatus(Enum):
    """Exchange health status."""

    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


@dataclass
class ExchangeHealth:
    """Health state for an exchange."""

    status: ExchangeStatus = ExchangeStatus.UNKNOWN
    last_checked: Optional[datetime] = None
    failures: int = 0
    last_failure_reason: Optional[str] = None
    down_since: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "last_checked": self.last_checked.isoformat()
            if self.last_checked
            else None,
            "failures": self.failures,
            "last_failure_reason": self.last_failure_reason,
            "down_since": self.down_since.isoformat() if self.down_since else None,
        }


@dataclass
class PriceCache:
    """Cached price data for a symbol."""

    price: float
    source: str
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "price": self.price,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "bid": self.bid,
            "ask": self.ask,
        }


class ExchangeManager:
    """Manages multiple cryptocurrency exchanges via CCXT with health tracking."""

    def __init__(
        self,
        exchange_configs: Dict[str, Dict],
        circuit_breaker_threshold: int = 3,
        circuit_breaker_cooldown: int = 900,  # 15 minutes
    ):
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self._executor = ThreadPoolExecutor(max_workers=10)

        # Health tracking
        self._health_map: Dict[str, ExchangeHealth] = {}
        self._circuit_breaker_threshold = circuit_breaker_threshold
        self._circuit_breaker_cooldown = timedelta(seconds=circuit_breaker_cooldown)

        # Price cache
        self._price_cache: Dict[str, PriceCache] = {}

        # Exchange priority order (for routing)
        self._exchange_priority: List[str] = []

        self._init_exchanges(exchange_configs)

    def _init_exchanges(self, configs: Dict[str, Dict]):
        """Initialize exchange connections - sync only, wrap with async later."""
        exchange_classes = {
            "binance": ccxt.binance,
            "bybit": ccxt.bybit,
            "okx": ccxt.okx,
            "gate": ccxt.gate,
            "kucoin": ccxt.kucoin,
            "bitget": ccxt.bitget,
            "huobi": ccxt.huobi,
            "kraken": ccxt.kraken,
        }

        for name, config in configs.items():
            if name not in exchange_classes:
                continue
            try:
                exchange = exchange_classes[name](config)
                # Test with a simple public call
                exchange.load_markets()
                self.exchanges[name] = exchange
                # Initialize health as UP since load_markets succeeded
                self._health_map[name] = ExchangeHealth(
                    status=ExchangeStatus.UP,
                    last_checked=datetime.now(),
                    failures=0,
                )
                self._exchange_priority.append(name)
                logger.info(f"[INIT] {name}: UP - markets loaded successfully")
            except Exception as e:
                logger.warning(f"[INIT] {name}: DOWN - {type(e).__name__}: {e}")
                self._health_map[name] = ExchangeHealth(
                    status=ExchangeStatus.DOWN,
                    last_checked=datetime.now(),
                    failures=1,
                    last_failure_reason=str(e),
                    down_since=datetime.now(),
                )

        if not self.exchanges:
            logger.error("[INIT] No exchanges initialized! Check network connectivity.")
        else:
            logger.info(f"[INIT] Healthy exchanges: {self._exchange_priority}")

    # ─────────────────────────────────────────────
    # HEALTH CHECK METHODS
    # ─────────────────────────────────────────────

    def is_exchange_healthy(self, exchange_name: str) -> bool:
        """Check if exchange is healthy and available."""
        health = self._health_map.get(exchange_name)
        if not health:
            return False

        # If DOWN, check if cooldown has passed
        if health.status == ExchangeStatus.DOWN:
            if health.down_since:
                elapsed = datetime.now() - health.down_since
                if elapsed >= self._circuit_breaker_cooldown:
                    # Cooldown passed, mark as UNKNOWN for retry
                    health.status = ExchangeStatus.UNKNOWN
                    health.failures = 0
                    health.down_since = None
                    logger.info(
                        f"[HEALTH] {exchange_name}: cooldown expired, ready for retry"
                    )
                    return True
            return False

        return health.status in (ExchangeStatus.UP, ExchangeStatus.UNKNOWN)

    def get_healthy_exchanges(self, symbol: Optional[str] = None) -> List[str]:
        """Get list of healthy exchanges, prioritized by config order."""
        healthy = [
            name
            for name in self._exchange_priority
            if self.is_exchange_healthy(name) and name in self.exchanges
        ]
        return healthy

    def mark_exchange_down(self, exchange_name: str, reason: str = ""):
        """Mark an exchange as DOWN."""
        health = self._health_map.get(exchange_name)
        if not health:
            health = ExchangeHealth()
            self._health_map[exchange_name] = health

        health.failures += 1
        health.last_failure_reason = reason
        health.last_checked = datetime.now()

        # Check if threshold exceeded
        if health.failures >= self._circuit_breaker_threshold:
            if health.status != ExchangeStatus.DOWN:
                health.status = ExchangeStatus.DOWN
                health.down_since = datetime.now()
                logger.warning(
                    f"[CIRCUIT] {exchange_name}: DOWN after {health.failures} failures "
                    f"(reason: {reason})"
                )
        else:
            logger.info(
                f"[HEALTH] {exchange_name}: failure #{health.failures} "
                f"(threshold: {self._circuit_breaker_threshold})"
            )

    def mark_exchange_up(self, exchange_name: str):
        """Mark an exchange as UP."""
        health = self._health_map.get(exchange_name)
        if not health:
            health = ExchangeHealth()
            self._health_map[exchange_name] = health

        was_down = health.status == ExchangeStatus.DOWN
        health.status = ExchangeStatus.UP
        health.failures = 0
        health.last_checked = datetime.now()
        health.last_failure_reason = None
        health.down_since = None

        if was_down:
            logger.info(f"[HEALTH] {exchange_name}: recovered to UP")

    def get_health_map(self) -> Dict[str, Dict]:
        """Get health status for all exchanges."""
        return {name: health.to_dict() for name, health in self._health_map.items()}

    # ─────────────────────────────────────────────
    # PRICE CACHE METHODS
    # ─────────────────────────────────────────────

    def update_price_cache(
        self,
        symbol: str,
        price: float,
        source: str,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
    ):
        """Update cached price for a symbol."""
        self._price_cache[symbol] = PriceCache(
            price=price,
            source=source,
            timestamp=datetime.now(),
            bid=bid,
            ask=ask,
        )
        logger.debug(f"[CACHE] {symbol}: ${price:,.2f} from {source}")

    def get_cached_price(self, symbol: str) -> Optional[Dict]:
        """Get cached price for a symbol."""
        cache = self._price_cache.get(symbol)
        if cache:
            return cache.to_dict()
        return None

    def get_all_cached_prices(self) -> Dict[str, Dict]:
        """Get all cached prices."""
        return {symbol: cache.to_dict() for symbol, cache in self._price_cache.items()}

    # ─────────────────────────────────────────────
    # TICKER FETCHING (with health routing)
    # ─────────────────────────────────────────────

    def _sync_fetch_ticker(self, exchange_name: str, symbol: str) -> Optional[Dict]:
        """Sync ticker fetch - runs in thread pool."""
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            return None

        if not self.is_exchange_healthy(exchange_name):
            logger.debug(f"[FETCH] Skipping {exchange_name}: not healthy")
            return None

        try:
            ticker = exchange.fetch_ticker(symbol)
            result = {
                "symbol": symbol,
                "exchange": exchange_name,
                "last": ticker.get("last"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "high": ticker.get("high"),
                "low": ticker.get("low"),
                "volume": ticker.get("baseVolume"),
                "change_24h": ticker.get("percentage"),
                "timestamp": datetime.now().isoformat(),
                "source": exchange_name,
            }

            # Mark exchange as healthy on success
            self.mark_exchange_up(exchange_name)

            # Update price cache
            if result["last"]:
                self.update_price_cache(
                    symbol=symbol,
                    price=result["last"],
                    source=exchange_name,
                    bid=result.get("bid"),
                    ask=result.get("ask"),
                )
                logger.info(
                    f"[FETCH] {symbol} from {exchange_name}: ${result['last']:,.2f} "
                    f"(bid: {result.get('bid', 'N/A')}, ask: {result.get('ask', 'N/A')})"
                )

            return result
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(f"[FETCH] {symbol} from {exchange_name}: FAILED - {error_msg}")
            self.mark_exchange_down(exchange_name, error_msg)
            return None

    async def fetch_ticker(self, exchange_name: str, symbol: str) -> Optional[Dict]:
        """Fetch ticker for a symbol from specific exchange (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self._sync_fetch_ticker, exchange_name, symbol
        )

    async def fetch_all_tickers(
        self, symbols: List[str], exchange_names: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch tickers for multiple symbols across healthy exchanges."""
        results = {}

        # Get healthy exchanges only
        if exchange_names is None:
            exchange_names = self.get_healthy_exchanges()
        else:
            # Filter to only healthy exchanges from requested list
            exchange_names = [e for e in exchange_names if self.is_exchange_healthy(e)]

        if not exchange_names:
            logger.warning("[FETCH] No healthy exchanges available for price fetch!")
            # Return cached prices as fallback
            for symbol in symbols:
                cached = self.get_cached_price(symbol)
                if cached:
                    results[symbol] = {"_cached": cached}
                    logger.info(
                        f"[FETCH] Using cached price for {symbol}: ${cached['price']:,.2f}"
                    )
            return results

        logger.info(f"[FETCH] Fetching {len(symbols)} symbols from {exchange_names}")

        # Build all tasks
        tasks = []
        for symbol in symbols:
            results[symbol] = {}
            for exchange_name in exchange_names:
                tasks.append(self._fetch_and_store(exchange_name, symbol, results))

        await asyncio.gather(*tasks, return_exceptions=True)

        # Log summary
        for symbol in symbols:
            sources = [e for e in results.get(symbol, {}) if not e.startswith("_")]
            if sources:
                prices = [
                    results[symbol][e].get("last", 0)
                    for e in sources
                    if results[symbol][e].get("last")
                ]
                if prices:
                    avg_price = sum(prices) / len(prices)
                    logger.info(
                        f"[SUMMARY] {symbol}: {len(sources)} sources, avg ${avg_price:,.2f}"
                    )
            else:
                logger.warning(f"[SUMMARY] {symbol}: no price data available")

        return results

    async def _fetch_and_store(self, exchange_name: str, symbol: str, results: Dict):
        """Fetch ticker and store in results dict."""
        ticker = await self.fetch_ticker(exchange_name, symbol)
        if ticker and ticker.get("last"):
            results[symbol][exchange_name] = ticker

    # ─────────────────────────────────────────────
    # ORDERBOOK (with health check)
    # ─────────────────────────────────────────────

    def _sync_fetch_orderbook(
        self, exchange_name: str, symbol: str, limit: int = 10
    ) -> Optional[Dict]:
        """Sync orderbook fetch."""
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            return None

        if not self.is_exchange_healthy(exchange_name):
            logger.debug(f"[ORDERBOOK] Skipping {exchange_name}: not healthy")
            return None

        try:
            orderbook = exchange.fetch_order_book(symbol, limit)
            self.mark_exchange_up(exchange_name)
            return {
                "symbol": symbol,
                "exchange": exchange_name,
                "bids": orderbook.get("bids", [])[:limit],
                "asks": orderbook.get("asks", [])[:limit],
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(f"[ORDERBOOK] Error from {exchange_name}: {error_msg}")
            self.mark_exchange_down(exchange_name, error_msg)
            return None

    async def fetch_orderbook(
        self, exchange_name: str, symbol: str, limit: int = 10
    ) -> Optional[Dict]:
        """Fetch order book for a symbol (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self._sync_fetch_orderbook, exchange_name, symbol, limit
        )

    # ─────────────────────────────────────────────
    # AUTHENTICATED ENDPOINTS
    # ─────────────────────────────────────────────

    def has_credentials(self, exchange_name: str) -> bool:
        """Check if exchange has API credentials configured."""
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            return False
        return bool(
            getattr(exchange, "apiKey", None) and getattr(exchange, "secret", None)
        )

    def _sync_fetch_balance(self, exchange_name: str) -> Optional[Dict]:
        """Sync balance fetch."""
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            return None
        if not self.has_credentials(exchange_name):
            logger.warning(f"[BALANCE] No API credentials for {exchange_name}")
            return None
        if not self.is_exchange_healthy(exchange_name):
            logger.warning(f"[BALANCE] Exchange {exchange_name} not healthy")
            return None
        try:
            balance = exchange.fetch_balance()
            self.mark_exchange_up(exchange_name)
            non_zero = {
                currency: {
                    "free": data.get("free", 0),
                    "used": data.get("used", 0),
                    "total": data.get("total", 0),
                }
                for currency, data in balance.get("total", {}).items()
                if data and data > 0
            }
            return non_zero
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(f"[BALANCE] Error from {exchange_name}: {error_msg}")
            self.mark_exchange_down(exchange_name, error_msg)
            return None

    async def fetch_balance(self, exchange_name: str) -> Optional[Dict]:
        """Fetch account balance from exchange (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self._sync_fetch_balance, exchange_name
        )

    def _sync_create_order(
        self,
        exchange_name: str,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
    ) -> Optional[Dict]:
        """Sync order creation."""
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            return None
        if not self.has_credentials(exchange_name):
            logger.warning(f"[ORDER] No API credentials for {exchange_name}")
            return None
        if not self.is_exchange_healthy(exchange_name):
            logger.warning(f"[ORDER] Exchange {exchange_name} not healthy")
            return None
        try:
            if order_type == "limit" and price:
                order = exchange.create_order(symbol, order_type, side, amount, price)
            else:
                order = exchange.create_order(symbol, "market", side, amount)
            self.mark_exchange_up(exchange_name)
            logger.info(f"[ORDER] Created: {order.get('id')} on {exchange_name}")
            return order
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(f"[ORDER] Error from {exchange_name}: {error_msg}")
            self.mark_exchange_down(exchange_name, error_msg)
            return None

    async def create_order(
        self,
        exchange_name: str,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
    ) -> Optional[Dict]:
        """Create an order on the exchange (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._sync_create_order,
            exchange_name,
            symbol,
            order_type,
            side,
            amount,
            price,
        )

    # ─────────────────────────────────────────────
    # UTILITY METHODS
    # ─────────────────────────────────────────────

    async def close_all(self):
        """Close all exchange connections."""
        # Sync exchanges don't need explicit close
        pass

    def get_available_exchanges(self) -> List[str]:
        """Get list of initialized exchanges."""
        return list(self.exchanges.keys())

    def get_exchange(self, name: str) -> Optional[ccxt.Exchange]:
        """Get exchange instance by name."""
        return self.exchanges.get(name)

    def get_status_summary(self) -> Dict:
        """Get summary of exchange status for logging/debugging."""
        healthy = self.get_healthy_exchanges()
        all_exchanges = list(self._health_map.keys())
        down = [e for e in all_exchanges if not self.is_exchange_healthy(e)]

        return {
            "total_exchanges": len(all_exchanges),
            "healthy_exchanges": healthy,
            "down_exchanges": down,
            "cached_symbols": list(self._price_cache.keys()),
            "health_map": self.get_health_map(),
        }
