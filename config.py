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

# === FILTERS (Hard) – Balanced ===
MIN_LIQUIDITY_SOL = 0.5               # Between 1.0 and 0.3
MAX_HOLDER_CONCENTRATION = 0.40       # Between 0.30 and 0.50
REQUIRE_MINT_DISABLED = True
REQUIRE_FREEZE_DISABLED = True
MIN_AGE_SECONDS = 60                  # 1 minute old
MAX_AGE_SECONDS = 1200                # 20 minutes old

# === FILTERS (Soft) – Balanced ===
MAX_DEV_HOLDING = 0.10                # Dev < 10%
MIN_24H_VOLUME = 15000                # $15k volume
MIN_HOLDERS = 20                      # At least 20 holders

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
STATE_FILE = "data/open_positions.json"
LOG_FILE = "data/bot.log"
CSV_EXPORT = "data/simulated_trades.csv"
PAPER_CSV = "data/paper_trades.csv"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(module)s - %(message)s"