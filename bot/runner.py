# bot/runner.py — главный цикл: рынок → позиции → входы
import logging
import random
import time

from config.settings import (
    SYMBOLS, PARAMS,
    STOP_JITTER_MIN, STOP_JITTER_MAX,
    ENTRY_DELAY_MIN, ENTRY_DELAY_MAX,
    PARTIAL_CLOSE_PCT, PARTIAL_TARGET, BREAKEVEN_TARGET,
)
from strategy.indicators import prepare_data
from strategy.signals    import check_buy_signal, check_sell_signal, calc_trailing_stop
from strategy.filters    import market_is_bullish, check_mtf_confirm
from exchange            import alpaca as broker
from core                import state, notifier
from bot.validator       import validate_signal

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  УПРАВЛЕНИЕ ПОЗИЦИЕЙ
# ══════════════════════════════════════════════════════════════════════

def manage_position(pos: dict, meta: dict,
                    data, portfolio_value: float) -> None:
    symbol      = pos["symbol"]
    qty_remain  = float(meta.get("qty_remaining", pos["qty"]))
    entry_price = float(meta["entry_price"])
    stop        = float(meta["stop"])
    take        = float(meta["take"])
    close       = float(data.iloc[-1]["Close"])
    atr         = float(data.iloc[-1]["ATR"])
    full_path   = take - entry_price
    current_path = close - entry_price

    # Трейлинг стоп
    new_stop = calc_trailing_stop(stop, close, atr, PARAMS["trailing_atr_mult"])
    if new_stop > stop:
        state.update_stop(symbol, new_stop)
        logger.info(f"{symbol}: стоп ↑ ${stop:.2f} → ${new_stop:.2f}")
        notifier.send(f"🔼 <b>Трейлинг стоп</b>  #{symbol}\n"
                      f"${stop:.2f} → <b>${new_stop:.2f}</b>")
        meta["stop"] = stop = new_stop

    # Breakeven при 50% пути к тейку
    if (not meta.get("breakeven_done") and full_path > 0 and
            current_path >= full_path * BREAKEVEN_TARGET):
        be_stop = entry_price + atr * 0.2
        if be_stop > stop:
            state.set_breakeven_done(symbol, be_stop)
            logger.info(f"{symbol}: breakeven → ${be_stop:.2f}")
            notifier.send(f"🔒 <b>Breakeven</b>  #{symbol}\n"
                          f"Стоп в безубыток: <b>${be_stop:.2f}</b>")
            meta["stop"] = meta["breakeven_done"] = stop = be_stop

    # Частичная фиксация 50% при 50% пути к тейку
    if (not meta.get("partial_done") and full_path > 0 and
            current_path >= full_path * PARTIAL_TARGET and qty_remain > 0):
        qty_close = round(qty_remain * PARTIAL_CLOSE_PCT, 4)
        if qty_close > 0 and broker.place_market_sell(symbol, qty_close):
            profit  = (close - entry_price) * qty_close
            qty_new = qty_remain - qty_close
            state.set_partial_done(symbol, qty_new)
            state.log_trade(symbol, "SELL_PARTIAL", entry_price, close,
                            qty_close, profit, "partial_profit", portfolio_value)
            logger.info(f"{symbol}: частичная фиксация {qty_close:.4f} @ ${close:.2f}")
            notifier.send(f"💰 <b>Частичная фиксация</b>  #{symbol}\n"
                          f"Закрыто {qty_close:.4f} шт. @ <b>${close:.2f}</b>\n"
                          f"P&L: <b>${profit:+.2f}</b>  |  Остаток: {qty_new:.4f}")
            meta["partial_done"]  = True
            meta["qty_remaining"] = qty_new

    # Полный выход по сигналу
    if check_sell_signal(data, meta):
        reason   = _exit_reason(close, meta)
        qty_exit = float(meta.get("qty_remaining", qty_remain))
        if broker.place_market_sell(symbol, qty_exit):
            profit = (close - entry_price) * qty_exit
            state.log_trade(symbol, "SELL", entry_price, close,
                            qty_exit, profit, reason, portfolio_value)
            state.remove_position_meta(symbol)
            notifier.notify_sell(symbol, entry_price, close, qty_exit, reason)
            logger.info(f"{symbol}: выход ({reason}) @ ${close:.2f} P&L=${profit:+.2f}")


def _exit_reason(close: float, meta: dict) -> str:
    if close <= meta["stop"]: return "trailing_stop"
    if close >= meta["take"]: return "take_profit"
    return "signal_exit"


# ══════════════════════════════════════════════════════════════════════
#  ГЛАВНЫЙ ЦИКЛ
# ══════════════════════════════════════════════════════════════════════

def run() -> None:
    """Один часовой цикл: рынок → позиции → входы."""
    logger.info("═" * 60)

    # 1. Аккаунт
    account = broker.get_account()
    if not account:
        notifier.notify_error("Не удалось подключиться к Alpaca API")
        return

    portfolio_value = float(account["portfolio_value"])
    cash            = float(account["cash"])
    logger.info(f"Портфель: ${portfolio_value:,.2f}  |  Кэш: ${cash:,.2f}")

    # 2. Фильтр рынка
    spy_data = prepare_data("SPY", period="1y")
    bullish  = market_is_bullish(spy_data)
    notifier.notify_market_filter(bullish)
    logger.info(f"Рынок бычий: {bullish}")

    # 3. Управление позициями
    for pos in broker.get_positions():
        symbol = pos["symbol"]
        meta   = state.load_positions_meta().get(symbol)
        if not meta:
            logger.warning(f"{symbol}: нет мета-данных")
            continue
        data = prepare_data(symbol, period="1y")
        if data is not None:
            manage_position(pos, meta, data, portfolio_value)

    # 4. Новые входы
    if not bullish:
        logger.info("Рынок медвежий — входов нет")
        return

    symbols_held = {p["symbol"] for p in broker.get_positions()}
    slots_free   = PARAMS["max_positions"] - len(symbols_held)

    if slots_free <= 0:
        logger.info("Все слоты заняты")
        return

    for symbol in SYMBOLS:
        if slots_free <= 0:
            break
        if symbol in symbols_held:
            continue

        data = prepare_data(symbol, period="1y")
        if data is None or not check_buy_signal(data, PARAMS):
            continue

        # MTF подтверждение (анти-бот)
        if not check_mtf_confirm(symbol, PARAMS):
            logger.info(f"{symbol}: MTF не подтвердил")
            continue

        close  = float(data.iloc[-1]["Close"])
        atr    = float(data.iloc[-1]["ATR"])

        # Случайный jitter стопа (анти-бот)
        jitter = random.uniform(STOP_JITTER_MIN, STOP_JITTER_MAX)
        stop   = close - (1.5 + jitter) * atr
        take   = close + 3.0 * (close - stop)

        valid, reason = validate_signal(close, stop, take, atr)
        if not valid:
            logger.info(f"{symbol}: отклонён — {reason}")
            continue

        qty  = (portfolio_value * PARAMS["risk_per_trade"]) / (close - stop)
        cost = qty * close
        if cost > cash * 0.95:
            qty  = (cash * 0.95) / close
            cost = qty * close
        if qty <= 0:
            continue

        # Случайная задержка (анти-бот)
        delay = random.randint(ENTRY_DELAY_MIN, ENTRY_DELAY_MAX)
        logger.info(f"{symbol}: сигнал | ${close:.2f} | задержка {delay}с")
        notifier.send(f"⏳ <b>Сигнал #{symbol}</b> — вход через {delay//60}м {delay%60}с\n"
                      f"${close:.2f}  Стоп: ${stop:.2f}  Тейк: ${take:.2f}")
        time.sleep(delay)

        data_fresh  = prepare_data(symbol, period="1y")
        if data_fresh is None:
            continue
        close_fresh = float(data_fresh.iloc[-1]["Close"])

        if abs(close_fresh - close) / close > 0.005:
            notifier.send(f"❌ <b>Вход отменён #{symbol}</b> — цена ушла")
            continue

        if broker.place_market_buy(symbol, qty):
            state.add_position_meta(symbol, close_fresh, stop, take, qty)
            state.log_trade(symbol, "BUY", close_fresh, 0, qty, 0,
                            "signal", portfolio_value)
            notifier.notify_buy(symbol, close_fresh, qty, stop, take)
            symbols_held.add(symbol)
            cash -= cost
            slots_free -= 1

    logger.info(f"Цикл завершён | позиций: {len(broker.get_positions())}")
