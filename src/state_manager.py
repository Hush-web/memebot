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
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def load_state(self) -> List[Position]:
        """Load open positions from JSON, handling missing or corrupted files."""
        if not os.path.exists(self.state_file):
            return []

        try:
            with open(self.state_file, "r") as f:
                payload = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # If file is missing or corrupted, treat as empty
            return []

        positions = []
        for p_data in payload.get("positions", []):
            try:
                entry_time = datetime.fromisoformat(p_data["entry_time"])
                pos = Position(
                    token=p_data["token"],
                    entry_price=p_data["entry_price"],
                    size=p_data["size"],
                    entry_time=entry_time
                )
                # Restore optional fields if present
                for key, value in p_data.items():
                    if hasattr(pos, key):
                        setattr(pos, key, value)
                positions.append(pos)
            except (KeyError, ValueError):
                # Skip corrupted entries
                continue

        return positions

    def _position_to_dict(self, pos: Position) -> dict:
        """Convert a Position object to a dict for JSON serialization."""
        return {
            "token": pos.token,
            "entry_price": pos.entry_price,
            "size": pos.size,
            "entry_time": pos.entry_time.isoformat(),
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