"""
config.py
=========
Central configuration for the memecoin trading bot.

Every module imports its settings from here so that behavior can be
changed in one place without touching business logic.
"""

# === MODE SELECTION ===
SIMULATION_MODE = False  # True = use mock data & simulated price paths. False = use live data.
PAPER_TRADE = True       # True = log actions only, no real transactions. False = real execution.

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
SIDEWAYS_THRESHOLD = 0.02             # +/-2% from entry = sideways

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

# === FILTERS (Hard) ===
MIN_LIQUIDITY_SOL = 1.0
MAX_HOLDER_CONCENTRATION = 0.30
REQUIRE_MINT_DISABLED = True
REQUIRE_FREEZE_DISABLED = True
MIN_AGE_SECONDS = 120
MAX_AGE_SECONDS = 900
# === FILTERS (Soft) ===
MAX_DEV_HOLDING = 0.10          # allow up to 10% dev holding
MIN_24H_VOLUME = 20000          # $20k minimum volume
MIN_HOLDERS = 20                # at least 20 holders
# === SIMULATION ONLY ===
SIMULATION_DAYS = 7
MOCK_TOKENS_PER_DAY = 50

# === PAPER TRADING / LIVE ===
RPC_ENDPOINT = "https://solana-rpc.publicnode.com"
BACKUP_RPC_ENDPOINT = "https://api.mainnet-beta.solana.com"   # fallback
# Free, keyless real-time feed for pump.fun token creation + trades.
# pump.fun itself has no official public API; PumpPortal is the widely used
# community data feed. subscribeNewToken is free; subscribeTokenTrade is
# metered at 0.01 SOL per 10,000 events against a linked wallet if you
# attach an api-key — omitting the key uses the free unmetered tier with
# best-effort rate limits. See https://pumpportal.fun/data-api/real-time/
PUMP_FUN_WS = "wss://pumpportal.fun/api/data"

# === STATE PERSISTENCE ===
STATE_FILE = "data/open_positions.json"
LOG_FILE = "data/bot.log"
CSV_EXPORT = "data/simulated_trades.csv"
PAPER_CSV = "data/paper_trades.csv"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(module)s - %(message)s"


def validate_config() -> None:
    """Sanity-check config values at startup. Raises ValueError on bad config."""
    errors = []

    if not (0 < MAX_POSITION_SIZE <= 1):
        errors.append("MAX_POSITION_SIZE must be between 0 and 1")
    if not (0 < MAX_DAILY_LOSS <= 1):
        errors.append("MAX_DAILY_LOSS must be between 0 and 1")
    if not (0 < MAX_WEEKLY_LOSS <= 1):
        errors.append("MAX_WEEKLY_LOSS must be between 0 and 1")
    if MAX_CONCURRENT_POSITIONS < 1:
        errors.append("MAX_CONCURRENT_POSITIONS must be >= 1")
    if BASE_CAPITAL <= 0:
        errors.append("BASE_CAPITAL must be > 0")

    alloc_sum = round(BUCKET_1_ALLOCATION + BUCKET_2_ALLOCATION + TRAILING_ALLOCATION, 6)
    if alloc_sum != 1.0:
        errors.append(f"Bucket allocations must sum to 1.0 (got {alloc_sum})")

    if MIN_AGE_SECONDS >= MAX_AGE_SECONDS:
        errors.append("MIN_AGE_SECONDS must be < MAX_AGE_SECONDS")

    if errors:
        raise ValueError("Config validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
