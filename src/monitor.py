"""
monitor.py
==========
Token data feed – REST discovery + real-time price polling via DexScreener.
"""

from __future__ import annotations

import json
import logging
import queue
import random
import threading
import time
import uuid
from typing import Iterator, Optional

import requests
import config

# Try to import websocket (optional, only used if WebSocket is available)
try:
    import websocket
except ImportError:
    websocket = None

PUMP_FUN_TOTAL_SUPPLY = 1_000_000_000


class TokenMonitor:
    """Yields token_data dicts – REST fallback with real-time price polling."""

    def __init__(self):
        self.logger = logging.getLogger("memebot")
        self._new_token_queue: "queue.Queue[dict]" = queue.Queue()
        self._price_cache: dict = {}          # token_address -> (price, timestamp)
        self._price_lock = threading.Lock()
        self._seen_addresses: set = set()
        self._rest_thread_started = False
        self._running = False
        self._price_ttl = 5  # seconds – refresh price every 5s

    def connect(self) -> None:
        if config.SIMULATION_MODE:
            return
        self.logger.info("Paper trading mode – REST discovery + real-time price polling")
        self._start_rest_fallback()

    def _start_rest_fallback(self) -> None:
        if self._rest_thread_started:
            return
        self._rest_thread_started = True
        self._running = True
        threading.Thread(target=self._rest_poll_loop, daemon=True).start()
        self.logger.info("REST fallback thread started (polls every 10 seconds for new tokens)")
        self._fetch_via_rest()

    def _rest_poll_loop(self) -> None:
        while self._running:
            try:
                self._fetch_via_rest()
                time.sleep(10)
            except Exception as e:
                self.logger.warning(f"REST poll loop error: {e}")
                time.sleep(30)

    def _fetch_via_rest(self) -> None:
        """Fetch new pump.fun tokens from DexScreener API with multiple queries."""
        try:
            # Use multiple search terms to catch more tokens
            queries = ["pump.fun", "solana", "raydium", "pump"]
            found = 0
            for query in queries:
                if found >= 20:
                    break
                resp = requests.get(
                    f"https://api.dexscreener.com/latest/dex/search?q={query}",
                    timeout=10
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                pairs = data.get("pairs", [])
                if not pairs:
                    continue

                for pair in pairs[:20]:
                    if found >= 20:
                        break
                    base_token = pair.get("baseToken", {})
                    if not base_token:
                        continue

                    address = base_token.get("address")
                    if not address or len(address) < 10:
                        continue

                    if address in self._seen_addresses:
                        continue
                    self._seen_addresses.add(address)

                    price = float(pair.get("priceUsd", 0.0001))
                    liquidity_usd = float(pair.get("liquidity", {}).get("usd", 0))
                    liquidity_sol = liquidity_usd / 150

                    # Lower threshold to catch more tokens
                    if liquidity_sol < 0.1:
                        continue

                    token_data = {
                        "address": address,
                        "liquidity_sol": max(liquidity_sol, 0.1),
                        "holder_concentration": 0.15,   # Conservative default
                        "mint_authority": None,         # pump.fun revokes
                        "freeze_authority": None,       # pump.fun revokes
                        "created_at": time.time() - 30, # assume recent
                        "dev_holding": 0.01,
                        "volume_24h": float(pair.get("volume", {}).get("h24", 10000)),
                        "holders": 20,
                        "price": price,
                    }
                    enriched = self._enrich_token_data(token_data)
                    self._new_token_queue.put(enriched)
                    found += 1
                    self.logger.info(f"REST added token: {address[:8]}... @ ${price:.8f}")

                if found > 0:
                    self.logger.info(f"REST added {found} token(s) to queue")

        except Exception as e:
            self.logger.debug(f"REST fallback error: {e}")

    def _enrich_token_data(self, token_data: dict) -> dict:
        """Fill missing fields with conservative defaults (paper trading friendly)."""
        enriched = token_data.copy()
        if enriched.get("holder_concentration") is None:
            enriched["holder_concentration"] = 0.15
        if enriched.get("dev_holding") is None:
            enriched["dev_holding"] = 0.01
        if enriched.get("volume_24h") is None:
            enriched["volume_24h"] = 10000
        if enriched.get("holders") is None:
            enriched["holders"] = 20
        return enriched

    def get_next_token(self) -> Iterator[dict]:
        if config.SIMULATION_MODE:
            while True:
                yield self.generate_mock_token()
        else:
            while True:
                try:
                    token = self._new_token_queue.get(timeout=5)
                    yield token
                except queue.Empty:
                    self.logger.info("Queue empty, forcing REST fetch...")
                    self._fetch_via_rest()
                    continue

    def _fetch_price_from_dex(self, token_address: str) -> Optional[float]:
        """Fetch current price for a token from DexScreener API."""
        try:
            resp = requests.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_address}",
                timeout=3
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            pairs = data.get("pairs", [])
            if not pairs:
                return None
            # Take the first pair (usually the most liquid)
            price_usd = float(pairs[0].get("priceUsd", 0))
            if price_usd > 0:
                return price_usd
            return None
        except Exception as e:
            self.logger.debug(f"Price fetch error for {token_address[:8]}: {e}")
            return None

    def get_current_price(self, token_address: str, last_known_price: Optional[float] = None) -> float:
        """
        Get real-time price from DexScreener (cached with TTL).
        Falls back to last_known_price if fetch fails.
        """
        if config.SIMULATION_MODE:
            base = last_known_price or 0.0001
            return max(0.0000001, base * (1 + random.gauss(0, 0.05)))

        now = time.time()
        # Check cache
        with self._price_lock:
            cached = self._price_cache.get(token_address)
            if cached and (now - cached[1]) < self._price_ttl:
                return cached[0]

        # Fetch fresh price
        price = self._fetch_price_from_dex(token_address)
        if price is not None and price > 0:
            with self._price_lock:
                self._price_cache[token_address] = (price, now)
            return price

        # Fallback to last known price
        if last_known_price is not None and last_known_price > 0:
            return last_known_price

        # Ultimate fallback
        self.logger.warning(f"No price for {token_address[:8]}, using fallback")
        return 0.0001

    def generate_mock_token(self) -> dict:
        """Generate mock token data for simulation mode."""
        is_good = random.random() < 0.20
        if is_good:
            liquidity_sol = random.uniform(1.0, 20.0)
            holder_concentration = random.uniform(0.02, 0.28)
            mint_authority = None
            freeze_authority = None
            dev_holding = random.uniform(0.0, 0.05)
            volume_24h = random.uniform(100000, 2000000)
            holders = random.randint(100, 3000)
        else:
            liquidity_sol = random.uniform(0.05, 5.0)
            holder_concentration = random.uniform(0.15, 0.90)
            mint_authority = random.choice([None, "Auth" + uuid.uuid4().hex[:8]])
            freeze_authority = random.choice([None, "Auth" + uuid.uuid4().hex[:8]])
            dev_holding = random.uniform(0.03, 0.60)
            volume_24h = random.uniform(0, 300000)
            holders = random.randint(5, 500)

        age_seconds = random.randint(0, 1800)
        return {
            "address": uuid.uuid4().hex,
            "liquidity_sol": round(liquidity_sol, 4),
            "holder_concentration": round(holder_concentration, 4),
            "mint_authority": mint_authority,
            "freeze_authority": freeze_authority,
            "created_at": time.time() - age_seconds,
            "dev_holding": round(dev_holding, 4),
            "volume_24h": round(volume_24h, 2),
            "holders": holders,
            "price": round(random.uniform(0.00001, 0.001), 8),
        }

    def simulate_price_path(self, entry_price: float, steps: int = 60,
                             volatility: float = 0.08) -> list:
        path = [entry_price]
        price = entry_price
        for _ in range(steps):
            shock = random.gauss(0, volatility)
            if random.random() < 0.03:
                shock += random.choice([1.5, -0.9])
            price = max(0.0000001, price * (1 + shock))
            path.append(price)
        return path

    # WebSocket methods (stubbed for compatibility)
    def subscribe_token_trade(self, token_address: str) -> None:
        pass

    def unsubscribe_token_trade(self, token_address: str) -> None:
        pass