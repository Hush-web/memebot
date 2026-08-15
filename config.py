"""
config.py
=========
Configuration for memecoin trading bot – tightened filters for safety.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# === MODE SELECTION ===
SIMULATION_MODE = False
PAPER_TRADE = True

# === POSITION & RISK ===
MAX_POSITION_SIZE = 0.05
MAX_DAILY_LOSS = 0.20
MAX_WEEKLY_LOSS = 0.30
MAX_TRADES_PER_DAY = 7
MAX_CONSECUTIVE_LOSSES = 3
CIRCUIT_BREAKER_HOURS = 1
POSITION_SIZE_REDUCTION = 0.50
MAX_CONCURRENT_POSITIONS = 3
BASE_CAPITAL = 100.0

# === EXIT LOGIC ===
TAKE_PROFIT_BUCKET_1 = 0.60
TAKE_PROFIT_BUCKET_2 = 1.50
TRAILING_STOP_PCT = 0.20
HARD_STOP_LOSS = 0.25          # Tighter: exit at -25% instead of -30% to reduce slippage impact
TIMEOUT_MINUTES = 15
SIDEWAYS_THRESHOLD = 0.02

# === ORDER ALLOCATION ===
BUCKET_1_ALLOCATION = 0.35
BUCKET_2_ALLOCATION = 0.35
TRAILING_ALLOCATION = 0.30

# === SLIPPAGE ===
BASE_SLIPPAGE = 0.01
SLIPPAGE_MULTIPLIER = 0.5
SLIPPAGE_WARNING_THRESHOLD = 0.03

# === RETRY LOGIC ===
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2
ORDER_FAILURE_RATE = 0.05

# === GAS FEES ===
GAS_FEE_PER_TX = 0.05

# === FILTERS (Hard) – Tightened for safety ===
MIN_LIQUIDITY_SOL = 1.0               # Increased from 0.5/0.1 – prevents low‑liquidity trades
MAX_HOLDER_CONCENTRATION = 0.30       # Tightened from 0.40 – avoid whale dumps
REQUIRE_MINT_DISABLED = True
REQUIRE_FREEZE_DISABLED = True
MIN_AGE_SECONDS = 60                  # 1 minute old
MAX_AGE_SECONDS = 900                 # 15 minutes old

# === FILTERS (Soft) – Tightened ===
MAX_DEV_HOLDING = 0.05                # Tightened from 0.10 – dev can't hold too much
MIN_24H_VOLUME = 20000                # Increased from 15000 – only tokens with real activity
MIN_HOLDERS = 30                      # Increased from 20 – more community support

# === SIMULATION ONLY ===
SIMULATION_DAYS = 7
MOCK_TOKENS_PER_DAY = 50

# === PAPER TRADING / LIVE ===
RPC_ENDPOINT = "https://solana-rpc.publicnode.com"
BACKUP_RPC_ENDPOINT = "https://api.mainnet-beta.solana.com"
PUMP_FUN_WS = "wss://pumpportal.fun/api/data"

# === TELEGRAM ===
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# === STATE PERSISTENCE ===
CLEAR_STATE_ON_START = True
STATE_FILE = "data/open_positions.json"
LOG_FILE = "data/bot.log"
CSV_EXPORT = "data/simulated_trades.csv"
PAPER_CSV = "data/paper_trades.csv"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(module)s - %(message)s"