# core/notifier.py — Telegram уведомления
import requests
import logging
from config.settings import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

logger  = logging.getLogger(__name__)
TG_URL  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


def send(text: str) -> bool:
    try:
        r = requests.post(TG_URL, json={
            "chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML",
        }, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram send: {e}")
        return False


def notify_buy(symbol: str, price: float, qty: float,
               stop: float, take: float) -> None:
    send(
        f"🟢 <b>ВХОД</b>  #{symbol}\n"
        f"Цена  : <b>${price:.2f}</b>\n"
        f"Кол-во: {qty:.4f} акций\n"
        f"Стоп  : ${stop:.2f}\n"
        f"Тейк  : ${take:.2f}\n"
        f"Риск  : ${round((price-stop)*qty, 2):.2f}"
    )


def notify_sell(symbol: str, entry: float, exit_price: float,
                qty: float, reason: str) -> None:
    profit = round((exit_price - entry) * qty, 2)
    emoji  = "🔴" if profit < 0 else "🟡"
    send(
        f"{emoji} <b>ВЫХОД</b>  #{symbol}\n"
        f"Вход  : ${entry:.2f}\n"
        f"Выход : <b>${exit_price:.2f}</b>\n"
        f"P&L   : <b>${profit:+.2f}</b>\n"
        f"Причина: {reason}"
    )


def notify_daily_summary(portfolio_value: float, cash: float,
                          positions: list, daily_pnl: float) -> None:
    pos_lines = "\n".join(
        f"  • {p['symbol']:6s}  ${float(p['unrealized_pl']):+.2f}"
        for p in positions
    ) or "  нет открытых позиций"
    emoji = "📈" if daily_pnl >= 0 else "📉"
    send(
        f"{emoji} <b>Дневной отчёт</b>\n"
        f"Портфель   : <b>${portfolio_value:,.2f}</b>\n"
        f"Кэш        : ${cash:,.2f}\n"
        f"P&L сегодня: <b>${daily_pnl:+,.2f}</b>\n\n"
        f"<b>Позиции:</b>\n{pos_lines}"
    )


def notify_market_filter(bullish: bool) -> None:
    if bullish:
        send("✅ <b>Рынок бычий</b> — все 3 фильтра SPY пройдены")
    else:
        send("🛑 <b>Рынок медвежий</b> — новых входов не будет")


def notify_error(msg: str) -> None:
    send(f"⚠️ <b>ОШИБКА БОТА</b>\n{msg}")
