"""
position_manager.py
===================
Manages open positions and defines the Position dataclass.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Position:
    """Represents an open trading position."""
    token: str
    entry_price: float
    size: float
    entry_time: datetime

    # Exit tracking
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl_percent: Optional[float] = None

    # Bucket fill tracking
    bucket_1_filled: bool = False
    bucket_2_filled: bool = False
    trailing_filled: bool = False
    stop_filled: bool = False

    # Trailing stop peak
    peak_price: float = 0.0


class PositionManager:
    def __init__(self):
        self.positions: List[Position] = []

    def add_position(self, position: Position) -> None:
        self.positions.append(position)

    def remove_position(self, token: str) -> None:
        self.positions = [p for p in self.positions if p.token != token]

    def get_position(self, token: str) -> Optional[Position]:
        for p in self.positions:
            if p.token == token:
                return p
        return None

    def get_all_positions(self) -> List[Position]:
        return self.positions

    def get_count(self) -> int:
        return len(self.positions)

    def get_total_exposure(self) -> float:
        return sum(p.size for p in self.positions)