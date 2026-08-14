"""
state_manager.py
================
Persists open positions across restarts using JSON.
"""

import json
import os
from datetime import datetime
from typing import List

import config
from src.position_manager import Position


class StateManager:
    def __init__(self, state_file: str = config.STATE_FILE):
        self.state_file = state_file

    def save_state(self, positions: List[Position]) -> None:
        """Save all open positions to JSON."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "positions": [self._position_to_dict(p) for p in positions]
        }
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def load_state(self) -> List[Position]:
        """Load open positions from JSON."""
        if not os.path.exists(self.state_file):
            return []

        try:
            with open(self.state_file, "r") as f:
                payload = json.load(f)

            positions = []
            for p_data in payload.get("positions", []):
                # CRITICAL: Parse entry_time back to datetime
                entry_time = datetime.fromisoformat(p_data["entry_time"])
                pos = Position(
                    token=p_data["token"],
                    entry_price=p_data["entry_price"],
                    size=p_data["size"],
                    entry_time=entry_time  # Now it's a datetime object
                )
                # Restore all other fields
                if "exit_price" in p_data and p_data["exit_price"] is not None:
                    pos.exit_price = p_data["exit_price"]
                if "exit_reason" in p_data:
                    pos.exit_reason = p_data["exit_reason"]
                if "pnl_percent" in p_data:
                    pos.pnl_percent = p_data["pnl_percent"]
                if "bucket_1_filled" in p_data:
                    pos.bucket_1_filled = p_data["bucket_1_filled"]
                if "bucket_2_filled" in p_data:
                    pos.bucket_2_filled = p_data["bucket_2_filled"]
                if "trailing_filled" in p_data:
                    pos.trailing_filled = p_data["trailing_filled"]
                if "stop_filled" in p_data:
                    pos.stop_filled = p_data["stop_filled"]
                if "peak_price" in p_data:
                    pos.peak_price = p_data["peak_price"]

                positions.append(pos)

            return positions

        except Exception as e:
            # If state is corrupted, return empty list and log
            return []

    def _position_to_dict(self, pos: Position) -> dict:
        """Convert Position to dict for JSON serialization."""
        return {
            "token": pos.token,
            "entry_price": pos.entry_price,
            "size": pos.size,
            "entry_time": pos.entry_time.isoformat(),  # Convert datetime to string
            "exit_price": pos.exit_price,
            "exit_reason": pos.exit_reason,
            "pnl_percent": pos.pnl_percent,
            "bucket_1_filled": pos.bucket_1_filled,
            "bucket_2_filled": pos.bucket_2_filled,
            "trailing_filled": pos.trailing_filled,
            "stop_filled": pos.stop_filled,
            "peak_price": pos.peak_price,
        }

    def clear_state(self) -> None:
        """Delete the state file."""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
            # Also create an empty state file
            self.save_state([])