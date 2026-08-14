"""
logger.py
=========
Sets up file/console logging and handles CSV trade logging + performance
metric aggregation.
"""

from __future__ import annotations

import csv
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

import config


CSV_FIELDS = [
    "timestamp", "token_address", "entry_price", "exit_price", "position_size",
    "pnl_percent", "pnl_dollars", "exit_reason", "hold_time_minutes",
    "bucket_1_filled", "bucket_2_filled", "trailing_filled", "stop_filled",
    "slippage_percent", "execution_latency_ms", "order_retries",
]


def setup_logging() -> logging.Logger:
    """Configure root logger to write to LOG_FILE and stdout."""
    os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)

    logger = logging.getLogger("memebot")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(config.LOG_FORMAT)

    file_handler = logging.FileHandler(config.LOG_FILE)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


class TradeLogger:
    """Writes closed-trade rows to CSV and aggregates performance stats."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.logger = logging.getLogger("memebot")
        self._ensure_csv()
        self.rows: List[dict] = []

    def _ensure_csv(self) -> None:
        os.makedirs(os.path.dirname(self.csv_path) or ".", exist_ok=True)
        if not os.path.exists(self.csv_path):
            try:
                with open(self.csv_path, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                    writer.writeheader()
            except OSError as e:
                self.logger.error(f"Failed to initialize CSV {self.csv_path}: {e}")

    def log_trade(self, row: dict) -> None:
        """Append a single closed-trade row. Missing fields default to empty."""
        try:
            full_row = {field_name: row.get(field_name, "") for field_name in CSV_FIELDS}
            with open(self.csv_path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writerow(full_row)
            self.rows.append(full_row)
        except OSError as e:
            self.logger.error(f"Failed to write trade row: {e}")

    def performance_summary(self) -> dict:
        """Compute win rate, avg win/loss, profit factor, drawdown, etc."""
        if not self.rows:
            return {}

        pnls = [float(r["pnl_percent"]) for r in self.rows if r.get("pnl_percent") not in ("", None)]
        dollars = [float(r["pnl_dollars"]) for r in self.rows if r.get("pnl_dollars") not in ("", None)]

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        win_rate = (len(wins) / len(pnls) * 100) if pnls else 0.0
        avg_win = (sum(wins) / len(wins) * 100) if wins else 0.0
        avg_loss = (sum(losses) / len(losses) * 100) if losses else 0.0

        gross_profit = sum(d for d in dollars if d > 0)
        gross_loss = abs(sum(d for d in dollars if d < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

        # Running drawdown from cumulative PnL
        cumulative = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for d in dollars:
            cumulative += d
            peak = max(peak, cumulative)
            drawdown = cumulative - peak
            max_drawdown = min(max_drawdown, drawdown)

        largest_win = max(pnls) * 100 if pnls else 0.0
        largest_loss = min(pnls) * 100 if pnls else 0.0

        return {
            "total_trades": len(self.rows),
            "win_rate": win_rate,
            "avg_win_pct": avg_win,
            "avg_loss_pct": avg_loss,
            "profit_factor": profit_factor,
            "net_pnl_dollars": sum(dollars),
            "max_drawdown_dollars": max_drawdown,
            "largest_win_pct": largest_win,
            "largest_loss_pct": largest_loss,
            "bucket_1_filled": sum(1 for r in self.rows if r.get("bucket_1_filled") is True),
            "bucket_2_filled": sum(1 for r in self.rows if r.get("bucket_2_filled") is True),
            "trailing_filled": sum(1 for r in self.rows if r.get("trailing_filled") is True),
            "stop_filled": sum(1 for r in self.rows if r.get("stop_filled") is True),
            "avg_slippage": (
                sum(float(r["slippage_percent"]) for r in self.rows if r.get("slippage_percent") not in ("", None))
                / len(self.rows) if self.rows else 0.0
            ),
            "avg_latency_ms": (
                sum(float(r["execution_latency_ms"]) for r in self.rows if r.get("execution_latency_ms") not in ("", None))
                / len(self.rows) if self.rows else 0.0
            ),
            "total_retries": sum(int(r["order_retries"]) for r in self.rows if r.get("order_retries") not in ("", None)),
        }
