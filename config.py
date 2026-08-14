"""
config.py
=========
Configuration for memecoin trading bot.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# === MODE SELECTION ===
SIMULATION_MODE = False   # True = mock data, False = live data
PAPER_TRADE = True        # True = log only, False = real execution

# === POSITION & RISK ===
MAX_POSITION_SIZE = 0.05              # 5% of portfolio per trade
MAX_DAILY_LOSS = 0.20                 # -20% daily loss cap
MAX_WEEKLY_LOSS = 0.30                # -30% weekly loss cap
MAX_TRADES_PER_DAY = 7
MAX_CONSECUTIVE_LOSSES = 3
CIRCUIT_BREAKER_HOURS = 1             # Pause after 3 losses
POSITION_SIZE_REDUCTION = 0.50        # Reduce by 50% after 3 losses
MAX_CONCURRENT_POSITIONS = 3          # Maximum simultaneous open positions
BASE_CAPITAL = 100.0                  # Starting capital in USD

# === EXIT LOGIC (Option A) ===
TAKE_PROFIT_BUCKET_1 = 0.60           # +60%: sell 35%
TAKE_PROFIT_BUCKET_2 = 1.50           # +150%: sell 35%
TRAILING_STOP_PCT = 0.20              # 20% trailing from peak
HARD_STOP_LOSS = 0.30                 # -30%: sell everything
TIMEOUT_MINUTES = 15                  # Exit if sideways for 15 mins
SIDEWAYS_THRESHOLD = 0.02             # ±2% from entry = sideways

# === ORDER ALLOCATION ===
BUCKET_1_ALLOCATION = 0.35            # 35% of position
BUCKET_2_ALLOCATION = 0.35            # 35% of position
TRAILING_ALLOCATION = 0.30            # 30% of position

# === SLIPPAGE ===
BASE_SLIPPAGE = 0.01                  # 1% base slippage
SLIPPAGE_MULTIPLIER = 0.5             # 0.5x per 100% liquidity decrease
SLIPPAGE_WARNING_THRESHOLD = 0.03     # Warn if slippage > 3%

# === RETRY LOGIC ===
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2                # Exponential backoff: 2^attempt seconds
ORDER_FAILURE_RATE = 0.05             # 5% chance of order failure (simulated)

# === GAS FEES ===
GAS_FEE_PER_TX = 0.05                 # $0.05 per transaction

# === FILTERS (Hard) – Loosened to get trades ===
MIN_LIQUIDITY_SOL = 0.1               # Was 0.5 – much looser
MAX_HOLDER_CONCENTRATION = 0.60       # Was 0.40 – looser
REQUIRE_MINT_DISABLED = True
REQUIRE_FREEZE_DISABLED = True
MIN_AGE_SECONDS = 15                  # Was 60 – faster entry
MAX_AGE_SECONDS = 2400                # Was 1200 – allow older tokens

# === FILTERS (Soft) – Loosened ===
MAX_DEV_HOLDING = 0.25                # Was 0.10 – dev can hold more
MIN_24H_VOLUME = 2000                 # Was 15000 – lower volume threshold
MIN_HOLDERS = 5                       # Was 20 – fewer holders allowed

# === SIMULATION ONLY ===
SIMULATION_DAYS = 7
MOCK_TOKENS_PER_DAY = 50

# === PAPER TRADING / LIVE ===
RPC_ENDPOINT = "https://solana-rpc.publicnode.com"
BACKUP_RPC_ENDPOINT = "https://api.mainnet-beta.solana.com"
PUMP_FUN_WS = "wss://pumpportal.fun/api/data"

# === TELEGRAM (from environment variables) ===
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# === STATE PERSISTENCE ===
CLEAR_STATE_ON_START = True           # Clear state on each startup to avoid stuck positions
STATE_FILE = "data/open_positions.json"
LOG_FILE = "data/bot.log"
CSV_EXPORT = "data/simulated_trades.csv"
PAPER_CSV = "data/paper_trades.csv"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(module)s - %(message)s"