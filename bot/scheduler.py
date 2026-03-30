# bot/scheduler.py — планировщик: часовые циклы + дневной отчёт
import logging
import schedule
import time
from datetime import datetime

from exchange     import alpaca as broker
from core         import state, notifier
from core.logger  import setup_logger
from bot.runner   import run

logger = logging.getLogger(__name__)

HOURS = ["09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30", "16:00"]
DAYS  = ["monday", "tuesday", "wednesday", "thursday", "friday"]


def hourly_cycle() -> None:
    if not broker.is_market_open():
        logger.info("Рынок закрыт — цикл пропущен")
        return
    logger.info("── Часовой цикл ──")
    run()


def daily_summary() -> None:
    logger.info("── Дневной отчёт ──")
    trades    = state.load_trades()
    today     = datetime.now().strftime("%Y-%m-%d")
    daily_pnl = sum(
        float(t["profit"]) for t in trades
        if t["date"].startswith(today) and t["side"] in ("SELL", "SELL_PARTIAL")
    )
    notifier.notify_daily_summary(
        broker.get_portfolio_value(),
        broker.get_cash(),
        broker.get_positions(),
        daily_pnl,
    )


def start() -> None:
    setup_logger()
    logger.info("Бот запущен | 09:30–16:00 ET каждый час | отчёт 16:45")
    notifier.send(
        "🤖 <b>Торговый бот запущен</b>\n"
        "Проверка: каждый час 09:30–16:00 ET\n"
        "Отчёт: 16:45 ET, Пн–Пт"
    )

    for hour in HOURS:
        for day in DAYS:
            getattr(schedule.every(), day).at(hour).do(hourly_cycle)

    for day in DAYS:
        getattr(schedule.every(), day).at("16:45").do(daily_summary)

    logger.info("Тестовый прогон при старте...")
    run()

    while True:
        schedule.run_pending()
        time.sleep(30)
