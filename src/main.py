"""
main.py
========
Orchestrator for memecoin trading bot – simulation and paper trading modes.
"""

import logging
import sys
import time
import signal
import threading
from datetime import datetime

import config
from src.monitor import TokenMonitor
from src.filters import TokenFilter
from src.execution import MockExecution
from src.risk_manager import RiskManager
from src.exit_logic import ExitLogic
from src.position_manager import PositionManager, Position
from src.state_manager import StateManager
from src.logger import TradeLogger
from src.telegram_alerts import (
    alert_trade_opened,
    alert_trade_closed,
    alert_daily_summary,
    alert_error
)


class MemeBot:
    def __init__(self):
        self.logger = logging.getLogger("memebot")
        logging.basicConfig(
            level=logging.INFO,
            format=config.LOG_FORMAT,
            handlers=[
                logging.FileHandler(config.LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.logger.info("Initializing MemeBot...")

        # Validate config
        self._validate_config()

        # Modules
        self.monitor = TokenMonitor()
        self.filter_engine = TokenFilter()
        self.execution = MockExecution()
        self.risk_manager = RiskManager()
        self.exit_logic = ExitLogic()
        self.position_manager = PositionManager()
        self.state_manager = StateManager()

        # Choose CSV path based on mode
        csv_path = config.PAPER_CSV if not config.SIMULATION_MODE else config.CSV_EXPORT
        self.logger_obj = TradeLogger(csv_path)

        self.capital = config.BASE_CAPITAL
        self.running = True
        self._daily_summary_sent = False

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Restore state
        self._restore_state()

    def _validate_config(self):
        """Validate config parameters."""
        total = (config.BUCKET_1_ALLOCATION + config.BUCKET_2_ALLOCATION +
                 config.TRAILING_ALLOCATION)
        if abs(total - 1.0) > 0.001:
            self.logger.warning(f"Bucket allocations sum to {total:.2f}, should be 1.0")
        if config.MAX_DAILY_LOSS > 0.5 or config.MAX_WEEKLY_LOSS > 0.5:
            self.logger.warning("Loss caps are high – consider lowering them")

    def _signal_handler(self, signum, frame):
        self.logger.info("Received shutdown signal, saving state...")
        self.running = False
        self.state_manager.save_state(self.position_manager.get_all_positions())
        self.logger.info("State saved. Exiting.")
        sys.exit(0)

    def _restore_state(self):
        """Load open positions from previous session."""
        positions = self.state_manager.load_state()
        for pos in positions:
            self.position_manager.add_position(pos)
            self.logger.info(f"Restored position {pos.token[:8]} @ {pos.entry_price:.8f}")

    def run(self):
        """Main entry point."""
        if config.SIMULATION_MODE:
            self._run_simulation()
        else:
            self._run_paper_trading()

        self._print_summary()

    def _run_simulation(self):
        """Simulation mode – uses mock data and simulated price paths."""
        self.logger.info("Starting SIMULATION for %d days", config.SIMULATION_DAYS)
        self.monitor.connect()

        tokens_per_day = config.MOCK_TOKENS_PER_DAY
        tokens_scanned = 0
        tokens_passed = 0
        trades_executed = 0

        for day in range(config.SIMULATION_DAYS):
            self.risk_manager.reset_daily()
            if day % 7 == 0 and day > 0:
                self.risk_manager.reset_weekly()

            for _ in range(tokens_per_day):
                if not self.running or not self.risk_manager.can_trade():
                    break

                token = self.monitor.generate_mock_token()
                tokens_scanned += 1

                passed, reason, score = self.filter_engine.run_all_filters(token)
                if not passed:
                    continue
                tokens_passed += 1

                if self.position_manager.get_count() >= config.MAX_CONCURRENT_POSITIONS:
                    continue

                position_size = self.risk_manager.get_position_size(self.capital)
                entry_price = token["price"]
                slippage = self.execution.calculate_slippage(position_size, token["liquidity_sol"])
                entry_price *= (1 + slippage)

                self.execution.simulate_buy(token["address"], entry_price, position_size)
                self.capital -= config.GAS_FEE_PER_TX

                pos = Position(
                    token=token["address"],
                    entry_price=entry_price,
                    size=position_size,
                    entry_time=datetime.now()
                )
                self.position_manager.add_position(pos)
                self.state_manager.save_state(self.position_manager.get_all_positions())
                trades_executed += 1

                price_path = self.monitor.simulate_price_path(entry_price, steps=60)
                for current_price in price_path:
                    exit_reason, exit_price = self.exit_logic.check_all_exits(
                        pos, current_price, datetime.now()
                    )
                    if exit_reason:
                        self.execution.simulate_sell(pos.token, exit_price, pos.size, exit_reason)
                        pos.exit_price = exit_price
                        pos.exit_reason = exit_reason
                        pos.pnl_percent = (exit_price - entry_price) / entry_price
                        pnl_dollars = pos.size * pos.pnl_percent
                        self.capital -= config.GAS_FEE_PER_TX
                        self.capital += pos.size * pos.pnl_percent
                        self.risk_manager.record_trade(
                            is_win=pos.pnl_percent > 0,
                            pnl_percent=pos.pnl_percent,
                            pnl_dollars=pnl_dollars
                        )
                        self.position_manager.remove_position(pos.token)
                        self.state_manager.save_state(self.position_manager.get_all_positions())
                        self.logger_obj.log_trade(pos.__dict__)
                        break
                else:
                    exit_price = price_path[-1] * (1 - 0.01)
                    self.execution.simulate_sell(pos.token, exit_price, pos.size, "TIMEOUT")
                    pos.exit_price = exit_price
                    pos.exit_reason = "TIMEOUT"
                    pos.pnl_percent = (exit_price - entry_price) / entry_price
                    pnl_dollars = pos.size * pos.pnl_percent
                    self.capital -= config.GAS_FEE_PER_TX
                    self.capital += pos.size * pos.pnl_percent
                    self.risk_manager.record_trade(
                        is_win=False,
                        pnl_percent=pos.pnl_percent,
                        pnl_dollars=pnl_dollars
                    )
                    self.position_manager.remove_position(pos.token)
                    self.state_manager.save_state(self.position_manager.get_all_positions())
                    self.logger_obj.log_trade(pos.__dict__)

                self.state_manager.save_state(self.position_manager.get_all_positions())

            if not self.running:
                break

        self.logger.info("Simulation complete.")
        self.state_manager.save_state(self.position_manager.get_all_positions())

    def _run_paper_trading(self):
        """Paper trading mode – live data, no real execution."""
        self.logger.info("Starting PAPER trading loop (real data)")
        self.monitor.connect()

        # Start price monitoring thread
        price_thread = threading.Thread(target=self._price_monitor_loop, daemon=True)
        price_thread.start()

        # Reset daily summary flag at midnight (simplified: check every loop)
        self._daily_summary_sent = False

        for token in self.monitor.get_next_token():
            if not self.running:
                break

            # Check daily summary (send once per day)
            current_hour = datetime.now().hour
            if current_hour == 23 and not self._daily_summary_sent:
                self._send_daily_summary()
                self._daily_summary_sent = True
            elif current_hour != 23:
                self._daily_summary_sent = False

            if not self.risk_manager.can_trade():
                self.logger.info("Risk limit reached, pausing discovery")
                time.sleep(10)
                continue
            if self.position_manager.get_count() >= config.MAX_CONCURRENT_POSITIONS:
                self.logger.info("Max concurrent positions reached, waiting...")
                time.sleep(5)
                continue

            passed, reason, score = self.filter_engine.run_all_filters(token)
            if not passed:
                self.logger.debug(f"Token {token['address'][:8]} rejected: {reason}")
                continue

            position_size = self.risk_manager.get_position_size(self.capital)
            entry_price = token["price"]
            slippage = self.execution.calculate_slippage(position_size, token["liquidity_sol"])
            entry_price *= (1 + slippage)

            self.execution.simulate_buy(token["address"], entry_price, position_size)
            self.capital -= config.GAS_FEE_PER_TX

            pos = Position(
                token=token["address"],
                entry_price=entry_price,
                size=position_size,
                entry_time=datetime.now()
            )
            self.position_manager.add_position(pos)
            self.state_manager.save_state(self.position_manager.get_all_positions())
            self.logger.info(f"Opened position {pos.token[:8]} @ {entry_price:.8f} size=${position_size:.2f}")

            # Send Telegram alert for trade opened
            alert_trade_opened(pos.token, pos.entry_price, pos.size)

    def _price_monitor_loop(self):
        """Background thread: monitor open positions and check exits using real prices."""
        self.logger.info("Price monitor loop started (every 2s)")
        while self.running:
            positions = self.position_manager.get_all_positions()
            for pos in positions:
                current_price = self.monitor.get_current_price(
                    pos.token,
                    last_known_price=pos.entry_price
                )
                exit_reason, exit_price = self.exit_logic.check_all_exits(
                    pos, current_price, datetime.now()
                )
                if exit_reason:
                    self.execution.simulate_sell(pos.token, exit_price, pos.size, exit_reason)
                    pos.exit_price = exit_price
                    pos.exit_reason = exit_reason
                    pos.pnl_percent = (exit_price - pos.entry_price) / pos.entry_price
                    pnl_dollars = pos.size * pos.pnl_percent
                    self.capital -= config.GAS_FEE_PER_TX
                    self.capital += pos.size * pos.pnl_percent
                    self.risk_manager.record_trade(
                        is_win=pos.pnl_percent > 0,
                        pnl_percent=pos.pnl_percent,
                        pnl_dollars=pnl_dollars
                    )
                    self.position_manager.remove_position(pos.token)
                    self.state_manager.save_state(self.position_manager.get_all_positions())
                    self.logger_obj.log_trade(pos.__dict__)
                    self.logger.info(
                        f"Closed {pos.token[:8]} @ {exit_price:.8f} "
                        f"reason={exit_reason} PnL={pos.pnl_percent:.2%}"
                    )
                    # Send Telegram alert for trade closed
                    alert_trade_closed(
                        pos.token,
                        pos.exit_price,
                        pos.exit_reason,
                        pos.pnl_percent,
                        pnl_dollars
                    )
            time.sleep(2)

    def _send_daily_summary(self):
        """Send daily performance summary to Telegram."""
        try:
            stats = self.logger_obj.get_summary()
            stats['capital'] = self.capital
            alert_daily_summary(stats)
            self.logger.info("Daily summary sent to Telegram")
        except Exception as e:
            self.logger.error(f"Failed to send daily summary: {e}")

    def _print_summary(self):
        """Print final summary."""
        print("\n" + "="*50)
        print("=== Memecoin Bot Paper Trading (Option A) ===")
        print("="*50)
        print(f"\nStarting capital: ${config.BASE_CAPITAL:.2f}")
        print(f"Final capital: ${self.capital:.2f}")
        print(f"Net PnL: ${self.capital - config.BASE_CAPITAL:.2f}")

        stats = self.logger_obj.get_summary()
        if stats:
            print(f"\nTotal tokens scanned: {stats.get('total_scanned', 0)}")
            print(f"Tokens passed filters: {stats.get('passed_filters', 0)}")
            print(f"Trades executed: {stats.get('trades_executed', 0)}")
            print(f"Trades closed: {stats.get('trades_closed', 0)}")
            print(f"\nWin rate: {stats.get('win_rate', 0):.2f}%")
            print(f"Average win: {stats.get('avg_win', 0):.2f}%")
            print(f"Average loss: {stats.get('avg_loss', 0):.2f}%")
            print(f"Net PnL: ${stats.get('net_pnl', 0):.2f}")

        print("\n--- State ---")
        print(f"Open positions restored: {len(self.position_manager.get_all_positions())}")
        print(f"Max concurrent positions reached: {config.MAX_CONCURRENT_POSITIONS}")

        csv_path = config.PAPER_CSV if not config.SIMULATION_MODE else config.CSV_EXPORT
        print(f"\nCSV saved to: {csv_path}")
        print(f"State saved to: {config.STATE_FILE}")
        print("="*50)

        # Send final summary to Telegram (if in paper trading and not simulation)
        if not config.SIMULATION_MODE:
            try:
                stats = self.logger_obj.get_summary()
                stats['capital'] = self.capital
                alert_daily_summary(stats)
            except Exception:
                pass

if __name__ == "__main__":
    bot = MemeBot()
    bot.run()