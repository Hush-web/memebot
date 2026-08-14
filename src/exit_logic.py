"""
exit_logic.py
=============
Exit strategy logic – TP1, TP2, Hard Stop, Trailing Stop, Timeout.
"""

import logging
from datetime import datetime
from typing import Optional, Tuple

import config
from src.position_manager import Position


class ExitLogic:
    def __init__(self):
        self.logger = logging.getLogger("memebot")

    def check_all_exits(self, position: Position, current_price: float, current_time: datetime) -> Tuple[Optional[str], Optional[float]]:
        """
        Check all exit conditions in priority order.
        Returns: (exit_reason, exit_price)
        """
        if position is None or current_price <= 0:
            return None, None

        entry = position.entry_price

        # 1. Hard Stop – most urgent
        hard_stop_price = entry * (1 - config.HARD_STOP_LOSS)
        if current_price <= hard_stop_price:
            self.logger.info(f"Hard stop triggered for {position.token[:8]} @ {current_price:.8f}")
            return "HARD_STOP", current_price

        # 2. Bucket 1 – 35% at +60%
        bucket_1_price = entry * (1 + config.TAKE_PROFIT_BUCKET_1)
        if current_price >= bucket_1_price and not position.bucket_1_filled:
            position.bucket_1_filled = True
            self.logger.info(f"Bucket 1 triggered for {position.token[:8]} @ {current_price:.8f}")
            return "BUCKET_1", current_price

        # 3. Bucket 2 – 35% at +150%
        bucket_2_price = entry * (1 + config.TAKE_PROFIT_BUCKET_2)
        if current_price >= bucket_2_price and not position.bucket_2_filled:
            position.bucket_2_filled = True
            self.logger.info(f"Bucket 2 triggered for {position.token[:8]} @ {current_price:.8f}")
            return "BUCKET_2", current_price

        # 4. Trailing Stop – only after Bucket 1 filled, 30% of position
        if position.bucket_1_filled:
            if current_price > position.peak_price:
                position.peak_price = current_price
            trailing_stop_price = position.peak_price * (1 - config.TRAILING_STOP_PCT)
            if current_price <= trailing_stop_price and not position.trailing_filled:
                position.trailing_filled = True
                self.logger.info(f"Trailing stop triggered for {position.token[:8]} @ {current_price:.8f}")
                return "TRAILING_STOP", current_price

        # 5. Timeout – 15 minutes sideways
        hold_time = (current_time - position.entry_time).total_seconds() / 60
        if hold_time >= config.TIMEOUT_MINUTES:
            price_change = (current_price - entry) / entry
            if abs(price_change) <= config.SIDEWAYS_THRESHOLD:
                self.logger.info(f"Timeout triggered for {position.token[:8]} @ {current_price:.8f}")
                return "TIMEOUT", current_price

        return None, None