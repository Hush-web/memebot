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
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

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
    alert_error,
    alert_system_started
)

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class HealthHandler(BaseHTTPRequestHandler):
    """Simple health check endpoint for Render."""
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def start_health_server():
    """Run health check server in a background thread."""
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


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
        self._validate_config()

        self.monitor = TokenMonitor()
        self.filter_engine = TokenFilter()
        self.execution = MockExecution()
        self.risk_manager = RiskManager()
        self.exit_logic = ExitLogic()
        self.position_manager = PositionManager()
        self.state_manager = StateManager()

        csv_path = config.PAPER_CSV if not config.SIMULATION_MODE else config.CSV_EXPORT
        self.logger_obj = TradeLogger(csv_path)

        self.capital = config.BASE_CAPITAL
        self.running = True
        self._daily_summary_sent = False

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._restore_state()

    def _validate_config(self):
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
        positions = self.state_manager.load_state()
        for pos in positions:
            self.position_manager.add_position(pos)
            self.logger.info(f"Restored position {pos.token[:8]} @ {pos.entry_price:.8f}")

    def run(self):
        if config.SIMULATION_MODE:
            self._run_simulation()
        else:
            self._run_paper_trading()
        self._print_summary()

    def _run_simulation(self):
        self.logger.info("Starting SIMULATION for %d days", config.SIMULATION_DAYS)
        self.monitor.connect()
        # ... (keep your existing simulation code – unchanged) ...

    def _run_paper_trading(self):
        self.logger.info("Starting PAPER trading loop (real data)")
        self.monitor.connect()
        alert_system_started()

        price_thread = threading.Thread(target=self._price_monitor_loop, daemon=True)
        price_thread.start()

        self._daily_summary_sent = False
        for token in self.monitor.get_next_token():
            if not self.running:
                break

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
            alert_trade_opened(pos.token, pos.entry_price, pos.size)

    def _price_monitor_loop(self):
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
                    alert_trade_closed(
                        pos.token,
                        pos.exit_price,
                        pos.exit_reason,
                        pos.pnl_percent,
                        pnl_dollars
                    )
            time.sleep(2)

    def _send_daily_summary(self):
        try:
            stats = self.logger_obj.get_summary()
            stats['capital'] = self.capital
            alert_daily_summary(stats)
            self.logger.info("Daily summary sent to Telegram")
        except Exception as e:
            self.logger.error(f"Failed to send daily summary: {e}")

    def _print_summary(self):
        # ... keep your existing summary code (unchanged) ...
        pass


if __name__ == "__main__":
    # Start health check server in a background thread (Render needs this)
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()

    # Run the bot – wrap in try/except to keep process alive on crash
    try:
        bot = MemeBot()
        bot.run()
    except Exception as e:
        import traceback
        traceback.print_exc()
        alert_error(f"Bot crashed: {str(e)}")
        # Keep the process alive so Render doesn't 502
        time.sleep(3600)