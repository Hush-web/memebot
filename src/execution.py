"""
execution.py
============
Handles order placement. In SIMULATION_MODE or PAPER_TRADE, every buy/sell
is logged only ("paper"); real execution only happens when both flags are
False, via a Jupiter swap.

NOTE: Jupiter is a swap aggregator, not a limit/stop-order book. Only the
entry (buy) is ever sent to Jupiter live. All exits (TP1, TP2, trailing
stop, hard stop) are simulated conditional checks evaluated in the
monitoring loop (see exit_logic.py / main.py); when triggered, a market
sell is issued through the same execution path.
"""

from __future__ import annotations

import logging
import random
import time
import uuid
from typing import Optional

import config


class MockExecution:
    """Simulated (paper) and real (Jupiter) order execution."""

    def __init__(self):
        self.logger = logging.getLogger("memebot")
        self._jupiter_client = None  # lazily constructed only for real trades

    # -- slippage / latency / fills ---------------------------------------------
    def calculate_slippage(self, position_size: float, liquidity: float) -> float:
        """Slippage grows as position size becomes large relative to liquidity."""
        if liquidity <= 0:
            return config.SLIPPAGE_WARNING_THRESHOLD * 3
        size_ratio = position_size / liquidity
        # Each 100% of liquidity consumed adds SLIPPAGE_MULTIPLIER on top of base.
        slippage = config.BASE_SLIPPAGE + (size_ratio * config.SLIPPAGE_MULTIPLIER)
        if slippage > config.SLIPPAGE_WARNING_THRESHOLD:
            self.logger.warning(f"High slippage estimated: {slippage:.2%}")
        return round(slippage, 6)

    def simulate_latency(self) -> int:
        """Simulated network/execution latency in milliseconds."""
        latency_ms = random.randint(100, 500)
        time.sleep(latency_ms / 1000 / 20)  # scaled-down sleep so sims run fast
        return latency_ms

    def simulate_partial_fill(self, order: dict) -> float:
        """Returns a fill fraction (0.5-1.0) influenced by liquidity."""
        liquidity = order.get("liquidity_sol", 1.0)
        base_fill = random.uniform(0.5, 1.0)
        # Deeper liquidity nudges fill rate up toward 100%.
        liquidity_bonus = min(0.2, liquidity / 100)
        return round(min(1.0, base_fill + liquidity_bonus), 4)

    def _maybe_fail(self) -> bool:
        """Simulated random order failure, used by paper trading only."""
        return random.random() < config.ORDER_FAILURE_RATE

    def _with_retries(self, fn, *args, **kwargs):
        last_err: Optional[Exception] = None
        for attempt in range(config.MAX_RETRIES):
            try:
                return fn(*args, **kwargs), attempt
            except Exception as e:
                last_err = e
                wait_time = config.RETRY_BACKOFF_BASE ** attempt
                self.logger.warning(f"Order attempt {attempt + 1} failed ({e}); retrying in {wait_time}s")
                time.sleep(min(wait_time, 2))  # capped so sims stay fast
        raise RuntimeError(f"Order failed after {config.MAX_RETRIES} retries: {last_err}")

    # -- simulated / paper orders ------------------------------------------------
    def simulate_buy(self, token_address: str, entry_price: float, position_size: float) -> dict:
        latency = self.simulate_latency()
        order_id = f"SIM-{uuid.uuid4().hex[:8]}"
        self.logger.info(f"[PAPER] BUY {token_address} @ {entry_price} size=${position_size:.2f}")
        return {
            "order_id": order_id,
            "status": "filled",
            "price": entry_price,
            "size": position_size,
            "latency_ms": latency,
        }

    def simulate_sell(self, token_address: str, exit_price: float, amount: float, reason: str) -> dict:
        latency = self.simulate_latency()
        order_id = f"SIM-{uuid.uuid4().hex[:8]}"
        self.logger.info(f"[PAPER] SELL {token_address} @ {exit_price} amount=${amount:.2f} reason={reason}")
        return {
            "order_id": order_id,
            "status": "filled",
            "price": exit_price,
            "size": amount,
            "reason": reason,
            "latency_ms": latency,
        }

    # -- real execution (Jupiter) ------------------------------------------------
    def _get_jupiter_client(self):
        """Lazily import/construct the Jupiter swap client. Only used live."""
        if self._jupiter_client is None:
            try:
                import jupiter_py  # type: ignore
                self._jupiter_client = jupiter_py.Client(rpc_endpoint=config.RPC_ENDPOINT)
            except ImportError as e:
                raise RuntimeError(
                    "jupiter-py is required for live execution. Install requirements.txt."
                ) from e
        return self._jupiter_client

    def execute_buy(self, token_address: str, amount: float) -> dict:
        """Real Jupiter swap buy. Only called when PAPER_TRADE=False and SIMULATION_MODE=False."""
        if config.PAPER_TRADE or config.SIMULATION_MODE:
            raise RuntimeError("execute_buy called while PAPER_TRADE/SIMULATION_MODE active")

        def _do_buy():
            client = self._get_jupiter_client()
            # NOTE: Real swap parameters (input mint, slippage bps, etc.) must be
            # supplied by the caller/config for a specific deployment; this is the
            # integration point.
            return client.swap(output_mint=token_address, amount=amount)

        result, retries = self._with_retries(_do_buy)
        self.logger.info(f"[LIVE] BUY {token_address} amount={amount} order={result}")
        return {"order_id": getattr(result, "id", str(result)), "status": "filled", "retries": retries}

    def execute_sell(self, token_address: str, amount: float) -> dict:
        """Real Jupiter market sell. Only called when PAPER_TRADE=False and SIMULATION_MODE=False."""
        if config.PAPER_TRADE or config.SIMULATION_MODE:
            raise RuntimeError("execute_sell called while PAPER_TRADE/SIMULATION_MODE active")

        def _do_sell():
            client = self._get_jupiter_client()
            return client.swap(input_mint=token_address, amount=amount)

        result, retries = self._with_retries(_do_sell)
        self.logger.info(f"[LIVE] SELL {token_address} amount={amount} order={result}")
        return {"order_id": getattr(result, "id", str(result)), "status": "filled", "retries": retries}

    # -- unified entrypoints used by main.py --------------------------------------
    def place_buy(self, token: str, entry_price: float, amount: float, liquidity_sol: float = 1.0) -> dict:
        if config.SIMULATION_MODE or config.PAPER_TRADE:
            result = self.simulate_buy(token, entry_price, amount)
        else:
            result = self.execute_buy(token, amount)
        result["slippage"] = self.calculate_slippage(amount, liquidity_sol)
        return result

    def place_sell(self, token: str, exit_price: float, amount: float, reason: str,
                    liquidity_sol: float = 1.0) -> dict:
        if config.SIMULATION_MODE or config.PAPER_TRADE:
            result = self.simulate_sell(token, exit_price, amount, reason)
        else:
            result = self.execute_sell(token, amount)
            result["reason"] = reason
        result["slippage"] = self.calculate_slippage(amount, liquidity_sol)
        return result
