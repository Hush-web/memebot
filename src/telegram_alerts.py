"""
telegram_alerts.py
==================
Send Telegram alerts for trades, daily summaries, and errors.
"""

import logging
import requests
import config

logger = logging.getLogger("memebot")


def send_telegram(message: str) -> bool:
    """
    Send a message to your Telegram channel.
    Returns True if successful, False otherwise.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("⚠️ Telegram credentials missing – alerts disabled")
        return False

    try:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            logger.info("✅ Telegram alert sent successfully")
            return True
        else:
            logger.error(f"❌ Telegram error: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.Timeout:
        logger.error("❌ Telegram timeout – check your internet connection")
        return False
    except Exception as e:
        logger.error(f"❌ Telegram exception: {e}")
        return False


def alert_trade_opened(token: str, entry_price: float, size: float) -> None:
    """Send a trade opened alert."""
    msg = (
        f"🟢 <b>TRADE OPENED</b>\n"
        f"Token: <code>{token[:8]}...</code>\n"
        f"Entry: <b>${entry_price:.8f}</b>\n"
        f"Size: <b>${size:.2f}</b>"
    )
    send_telegram(msg)


def alert_trade_closed(
    token: str,
    exit_price: float,
    reason: str,
    pnl_percent: float,
    pnl_dollars: float
) -> None:
    """Send a trade closed alert."""
    emoji = "✅" if pnl_percent > 0 else "❌"
    msg = (
        f"{emoji} <b>TRADE CLOSED</b>\n"
        f"Token: <code>{token[:8]}...</code>\n"
        f"Exit: <b>${exit_price:.8f}</b>\n"
        f"Reason: <b>{reason}</b>\n"
        f"PnL: <b>{pnl_percent:+.2%}</b> (${pnl_dollars:+.2f})"
    )
    send_telegram(msg)


def alert_daily_summary(stats: dict) -> None:
    """Send a daily performance summary."""
    if not stats:
        return

    msg = (
        f"📊 <b>DAILY SUMMARY</b>\n"
        f"─────────────────\n"
        f"Trades: <b>{stats.get('total_trades', 0)}</b>\n"
        f"Wins: <b>{stats.get('wins', 0)}</b> | Losses: <b>{stats.get('losses', 0)}</b>\n"
        f"Win Rate: <b>{stats.get('win_rate', 0):.2f}%</b>\n"
        f"Net PnL: <b>${stats.get('net_pnl', 0):.2f}</b>\n"
        f"Capital: <b>${stats.get('capital', 0):.2f}</b>"
    )
    send_telegram(msg)


def alert_error(error_msg: str) -> None:
    """Send an error alert."""
    msg = f"⚠️ <b>BOT ERROR</b>\n<code>{error_msg}</code>"
    send_telegram(msg)


def alert_system_started() -> None:
    """Send a system started alert – useful for testing connectivity."""
    msg = (
        "🤖 <b>MEMEBOT STARTED</b>\n"
        f"Mode: {'PAPER' if config.PAPER_TRADE else 'LIVE'}\n"
        f"Simulation: {'ON' if config.SIMULATION_MODE else 'OFF'}\n"
        f"Capital: <b>${config.BASE_CAPITAL:.2f}</b>"
    )
    send_telegram(msg)