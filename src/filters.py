"""
filters.py
==========
Hard and soft filter pipeline applied to each candidate token before a
trade is considered.
"""

from __future__ import annotations

import logging
import time
from typing import Tuple

import config


class TokenFilter:
    """Applies hard (pass/fail) and soft (scored) filters to token data."""

    def __init__(self):
        self.logger = logging.getLogger("memebot")

    # -- hard filters ---------------------------------------------------------
    def check_liquidity(self, token_data: dict) -> Tuple[bool, str]:
        liq = token_data.get("liquidity_sol", 0)
        if liq < config.MIN_LIQUIDITY_SOL:
            return False, f"liquidity {liq} SOL < min {config.MIN_LIQUIDITY_SOL} SOL"
        return True, "ok"

    def check_holder_concentration(self, token_data: dict) -> Tuple[bool, str]:
        conc = token_data.get("holder_concentration", 1.0)
        if conc > config.MAX_HOLDER_CONCENTRATION:
            return False, f"holder concentration {conc:.2%} > max {config.MAX_HOLDER_CONCENTRATION:.0%}"
        return True, "ok"

    def check_mint_freeze_authority(self, token_data: dict) -> Tuple[bool, str]:
        if config.REQUIRE_MINT_DISABLED and token_data.get("mint_authority") is not None:
            return False, "mint authority not disabled"
        if config.REQUIRE_FREEZE_DISABLED and token_data.get("freeze_authority") is not None:
            return False, "freeze authority not disabled"
        return True, "ok"

    def check_age(self, token_data: dict) -> Tuple[bool, str]:
        created_at = token_data.get("created_at", 0)
        age = time.time() - created_at
        if age < config.MIN_AGE_SECONDS:
            return False, f"token too young ({age:.0f}s < {config.MIN_AGE_SECONDS}s)"
        if age > config.MAX_AGE_SECONDS:
            return False, f"token too old ({age:.0f}s > {config.MAX_AGE_SECONDS}s)"
        return True, "ok"

    # -- soft filters (scored, not blocking) -----------------------------------
    def check_dev_holding(self, token_data: dict) -> float:
        dev_holding = token_data.get("dev_holding", 1.0)
        return max(0.0, 1 - (dev_holding / config.MAX_DEV_HOLDING)) if config.MAX_DEV_HOLDING else 0.0

    def check_volume(self, token_data: dict) -> float:
        volume = token_data.get("volume_24h", 0)
        return min(1.0, volume / config.MIN_24H_VOLUME) if config.MIN_24H_VOLUME else 0.0

    def check_holders(self, token_data: dict) -> float:
        holders = token_data.get("holders", 0)
        return min(1.0, holders / config.MIN_HOLDERS) if config.MIN_HOLDERS else 0.0

    def score_token(self, token_data: dict) -> float:
        """0-100 composite score from soft-filter sub-scores."""
        dev_score = self.check_dev_holding(token_data)
        vol_score = self.check_volume(token_data)
        holder_score = self.check_holders(token_data)
        # Equal weighting across the three soft signals.
        composite = (dev_score + vol_score + holder_score) / 3
        return round(composite * 100, 2)

    # -- pipeline entrypoint ----------------------------------------------------
    def run_all_filters(self, token_data: dict) -> Tuple[bool, str, float]:
        """Run hard filters first (fail-fast), then score. Returns (passed, reason, score)."""
        try:
            hard_checks = [
                self.check_liquidity,
                self.check_holder_concentration,
                self.check_mint_freeze_authority,
                self.check_age,
            ]
            for check in hard_checks:
                passed, reason = check(token_data)
                if not passed:
                    # Log the rejection with the token address
                    self.logger.debug(f"Token {token_data.get('address', 'unknown')[:8]} rejected: {reason}")
                    return False, reason, 0.0

            score = self.score_token(token_data)
            # Use configurable threshold (default 20 if not set)
            threshold = getattr(config, 'SOFT_SCORE_THRESHOLD', 20)
            if score < threshold:
                return False, f"soft score too low ({score} < {threshold})", score

            return True, "passed all filters", score
        except Exception as e:
            self.logger.error(f"Filter error for token {token_data.get('address')}: {e}")
            return False, f"filter_error: {e}", 0.0