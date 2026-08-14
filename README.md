# Memebot — Solana Memecoin Trading Bot (Simulation / Paper Trading)

A modular bot implementing:

1. **Filter Pipeline** — liquidity, holder concentration, mint/freeze authority, dev wallet, age.
2. **Risk Manager** — position sizing, daily/weekly loss limits, consecutive-loss size reduction, circuit breaker.
3. **3-Bucket Exit Strategy** — 35% at +60%, 35% at +150%, 30% trailing stop at -20% from peak.
4. **Hard Stop-Loss** — -30% on the full position.

Two modes, controlled by `config.py`:

- `SIMULATION_MODE = True` — mock tokens, simulated price paths. Always forces `PAPER_TRADE = True`.
- `SIMULATION_MODE = False`, `PAPER_TRADE = True` — **(the default)** real pump.fun token discovery + real market prices via PumpPortal's WebSocket, no real transactions (logs "would have" trades).
- `SIMULATION_MODE = False`, `PAPER_TRADE = False` — real entries via Jupiter swap. **Not recommended without further testing and your own risk review.**

## Data source for paper/live trading

Pump.fun has no official public API. This bot uses **PumpPortal**
(`wss://pumpportal.fun/api/data`), a free, keyless, widely used community
WebSocket feed:

- `subscribeNewToken` (free, always on) — fires the moment a new pump.fun token
  is created; `monitor.py` turns each event into a candidate token for the filter
  pipeline.
- `subscribeTokenTrade` — the bot subscribes per-token only for positions it has
  actually opened, and unsubscribes when the position fully closes. This is what
  drives `get_current_price()`, which is what makes your exit logic (TP1/TP2/
  trailing stop/hard stop) actually trigger against real price movement. This
  stream is metered (0.01 SOL / 10,000 events) if you attach an API key and
  linked wallet; without a key it runs on PumpPortal's free best-effort tier.

Price is derived from bonding-curve reserves (`vSolInBondingCurve / vTokensInBondingCurve`),
denominated in SOL — the same unit used everywhere else in the bot (entry price,
CSV, config thresholds).

**Data completeness caveat:** the free feed gives you mint address, bonding-curve
liquidity, and price — but *not* holder count, holder concentration, dev wallet %,
or 24h volume, which `filters.py`'s soft filters also check. Pump.fun's launch
mechanism does revoke mint/freeze authority for every token, so those two hard
filters are safe to treat as always-passing. For the rest, `monitor.py`'s
`_enrich_token_data()` is a clearly marked stub — it defaults to conservative
values (so the bot fails-safe rather than trading on unknown data) and logs a
one-time warning. To make holder/volume-based scoring meaningful, plug a real
token-analytics API (Solana Tracker, Birdeye, Codex, etc. — all require their own
API key) into that function.

## Jupiter integration note

Jupiter is a swap aggregator, not a limit/stop-order book. Only the **entry** (buy)
is ever sent to Jupiter live. All **exits** (TP1, TP2, trailing stop, hard stop) are
simulated conditional price checks evaluated every loop iteration against the
PumpPortal price feed described above; when a condition triggers, a market sell is
sent (live) or logged (paper).

## Setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running the simulation (backtesting / tuning)

Ensure `config.py` has `SIMULATION_MODE = True`, then:

```bash
python -m src.main
```

This scans `SIMULATION_DAYS * MOCK_TOKENS_PER_DAY` mock tokens, walks a simulated
price path for every position taken, and prints a full performance summary at the
end. Results are written to `data/simulated_trades.csv` and `data/open_positions.json`.

## Running paper trading (real data, no real orders) — the default

`config.py` already ships with `SIMULATION_MODE = False`, `PAPER_TRADE = True`. Just run:

```bash
python -m src.main
```

What happens:
1. Connects to PumpPortal (with retry/backoff) and subscribes to new-token creation events.
2. Every new token goes through the filter pipeline (`filters.py`) in real time.
3. Tokens that pass get a simulated buy logged, a `Position` opened, and the bot
   subscribes to that token's live trade stream.
4. Every 2 seconds, all open positions are checked against the real price feed for
   TP1/TP2/trailing-stop/hard-stop/timeout — logging simulated sells as conditions trigger.
5. Every action is written to `data/paper_trades.csv`; state is saved after every
   position change and on shutdown, and restored (with re-subscription to live prices)
   on the next run.

Stop with `Ctrl+C`. Note: since pump.fun launches dozens of tokens a minute, expect
a lot of log output — increase your filter strictness in `config.py` if you want
fewer, higher-conviction trades.

## Going live

Set `SIMULATION_MODE = False` and `PAPER_TRADE = False` only after you have:

- Reviewed and tuned every threshold in `config.py` against paper-trading results.
- Filled in real Jupiter swap parameters in `src/execution.py` (`_get_jupiter_client`,
  `execute_buy`, `execute_sell`) for your specific input mint / wallet / slippage settings.
- Funded and secured a dedicated trading wallet, and understand that memecoin
  trading carries a high risk of total capital loss.

## Project layout

```
memebot/
├── src/
│   ├── monitor.py          # WebSocket listener / mock data feed
│   ├── filters.py          # Token filter pipeline
│   ├── execution.py        # Execution (real or mock)
│   ├── risk_manager.py     # Position sizing, daily limits, circuit breakers
│   ├── exit_logic.py       # TP/SL, trailing stop, timeout logic
│   ├── position_manager.py # Concurrent positions tracking
│   ├── state_manager.py    # Persistence across restarts
│   ├── logger.py           # CSV logging, performance tracking
│   └── main.py             # Orchestrator
├── data/                    # CSVs, state file, bot.log (generated at runtime)
├── config.py
├── requirements.txt
└── README.md
```

## Known limitation: circuit breaker in simulation mode

`RiskManager`'s circuit breaker (`CIRCUIT_BREAKER_HOURS`) and daily/weekly resets
are keyed off real wall-clock time (`datetime.now()`), since the same
`RiskManager` is shared by live/paper trading where that's the correct behavior.
In `SIMULATION_MODE`, thousands of mock trades can be processed in seconds, so a
single circuit-breaker trip (e.g. 3 consecutive losses) will pause trading for the
rest of that simulation run, since real time hasn't advanced. If you want the
circuit breaker to reset between simulated days, either lower `CIRCUIT_BREAKER_HOURS`
for tuning runs, or extend `RiskManager` to accept an injectable clock.

## Disclaimer

This project is provided for educational and research purposes. Memecoin trading is
highly speculative and the large majority of new tokens are scams or go to zero.
Nothing here is financial advice; you are responsible for your own risk management,
capital, and compliance with the laws that apply to you.
