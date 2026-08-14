"""
telegram_alerts.py
==================
Send Telegram alerts for trades only (no spam).
"""

import requests
import config

def send_telegram(message: str) -> None:
    """Send a message to your Telegram channel."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass  # Silent fail – don't crash the bot

def alert_trade_opened(token, entry_price, size):
    msg = f"🟢 <b>TRADE OPENED</b>\nToken: {token[:8]}...\nEntry: ${entry_price:.8f}\nSize: ${size:.2f}"
    send_telegram(msg)

def alert_trade_closed(token, exit_price, reason, pnl_percent, pnl_dollars):
    emoji = "✅" if pnl_percent > 0 else "❌"
    msg = f"{emoji} <b>TRADE CLOSED</b>\nToken: {token[:8]}...\nExit: ${exit_price:.8f}\nReason: {reason}\nPnL: {pnl_percent:.2%} (${pnl_dollars:.2f})"
    send_telegram(msg)

def alert_daily_summary(stats):
    """Send a daily performance summary (end of day)."""
    msg = f"""
📊 <b>DAILY SUMMARY</b>
Trades: {stats.get('total_trades', 0)}
Wins: {stats.get('wins', 0)} | Losses: {stats.get('losses', 0)}
Win Rate: {stats.get('win_rate', 0):.2f}%
Net PnL: ${stats.get('net_pnl', 0):.2f}
Capital: ${stats.get('capital', 0):.2f}
"""
    send_telegram(msg)

def alert_error(error_msg):
    msg = f"⚠️ <b>BOT ERROR</b>\n{error_msg}"
    send_telegram(msg)