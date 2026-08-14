"""
risk_manager.py
===============
Risk management – position sizing, daily/weekly loss limits, circuit breaker.
"""

import logging
import time
from datetime import datetime
from typing import Optional

import config


class RiskManager:
    def __init__(self):
        self.logger = logging.getLogger("memebot")
        self.base_position_size = config.MAX_POSITION_SIZE

        # Daily counters
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_loss = 0.0

        # Weekly counters
        self.weekly_pnl = 0.0
        self.weekly_loss = 0.0

        # Loss streak
        self.consecutive_losses = 0

        # Circuit breaker
        self.circuit_breaker_active = False
        self.circuit_breaker_end_time = None

        # Track current day/week for resets
        self._current_day = datetime.now().day
        self._current_week = datetime.now().isocalendar()[1]

    def can_trade(self) -> bool:
        """Check if trading is allowed based on all risk limits."""
        if self.circuit_breaker_active:
            if self.circuit_breaker_end_time and time.time() >= self.circuit_breaker_end_time:
                self.circuit_breaker_active = False
                self.logger.info("Circuit breaker lifted")
            else:
                self.logger.debug("Circuit breaker active")
                return False

        # Daily loss check
        if abs(self.daily_loss) >= config.MAX_DAILY_LOSS:
            self.logger.warning(f"Daily loss cap reached: {self.daily_loss:.2%}")
            return False

        # Weekly loss check
        if abs(self.weekly_loss) >= config.MAX_WEEKLY_LOSS:
            self.logger.warning(f"Weekly loss cap reached: {self.weekly_loss:.2%}")
            return False

        # Trades per day limit
        if self.daily_trades >= config.MAX_TRADES_PER_DAY:
            self.logger.info(f"Daily trade limit reached: {self.daily_trades}")
            return False

        return True

    def get_position_size(self, capital: float) -> float:
        """
        Calculate position size based on capital and loss streak.
        Returns position size in dollars.
        """
        base_size = capital * self.base_position_size

        # Reduce position size if consecutive losses >= 3
        if self.consecutive_losses >= config.MAX_CONSECUTIVE_LOSSES:
            base_size *= config.POSITION_SIZE_REDUCTION
            self.logger.info(f"Position size reduced by {config.POSITION_SIZE_REDUCTION*100:.0f}% due to losses")

        return round(base_size, 2)

    def record_trade(self, is_win: bool, pnl_percent: float = 0.0, pnl_dollars: float = 0.0) -> None:
        """
        Record the outcome of a trade.
        Updates daily/weekly PnL, loss streak, and circuit breaker.
        """
        self.daily_trades += 1

        if is_win:
            self.consecutive_losses = 0
            self.daily_pnl += pnl_dollars
            self.weekly_pnl += pnl_dollars
        else:
            self.consecutive_losses += 1
            self.daily_loss += abs(pnl_dollars)  # track loss magnitude
            self.daily_pnl += pnl_dollars
            self.weekly_pnl += pnl_dollars
            # Check if we hit consecutive loss limit
            if self.consecutive_losses >= config.MAX_CONSECUTIVE_LOSSES:
                self._activate_circuit_breaker()

        # Check daily loss cap
        if abs(self.daily_loss) >= config.MAX_DAILY_LOSS:
            self.logger.warning(f"Daily loss cap triggered: {self.daily_loss:.2%}")

        # Check weekly loss cap
        if abs(self.weekly_loss) >= config.MAX_WEEKLY_LOSS:
            self.logger.warning(f"Weekly loss cap triggered: {self.weekly_loss:.2%}")

        self.logger.info(
            f"Trade recorded: {'win' if is_win else 'loss'} | "
            f"PnL=${pnl_dollars:.2f} | Daily PnL=${self.daily_pnl:.2f} | "
            f"Weekly PnL=${self.weekly_pnl:.2f} | Consecutive losses={self.consecutive_losses}"
        )

    def _activate_circuit_breaker(self) -> None:
        """Activate circuit breaker for a specified duration."""
        if not self.circuit_breaker_active:
            self.circuit_breaker_active = True
            self.circuit_breaker_end_time = time.time() + config.CIRCUIT_BREAKER_HOURS * 3600
            self.logger.warning(
                f"Circuit breaker triggered after {self.consecutive_losses} consecutive losses. "
                f"Paused for {config.CIRCUIT_BREAKER_HOURS} hours."
            )

    def reset_daily(self) -> None:
        """Reset daily counters at the start of a new day."""
        self.daily_pnl = 0.0
        self.daily_loss = 0.0
        self.daily_trades = 0
        self.logger.debug("Daily counters reset")

    def reset_weekly(self) -> None:
        """Reset weekly counters at the start of a new week."""
        self.weekly_pnl = 0.0
        self.weekly_loss = 0.0
        self.logger.debug("Weekly counters reset")