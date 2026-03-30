# bot/validator.py — валидация сигнала перед отправкой ордера
from config.settings import MIN_RISK_REWARD, MAX_ATR_RATIO


def validate_signal(close: float, stop: float,
                    take: float, atr: float) -> tuple[bool, str]:
    """
    Проверяет корректность сигнала (идея из backtest-kit).
    Возвращает (True, "") или (False, причина_отказа).
    """
    risk = close - stop
    if risk <= 0:
        return False, f"стоп ${stop:.2f} >= цены ${close:.2f}"

    rr = (take - close) / risk
    if rr < MIN_RISK_REWARD:
        return False, f"R/R {rr:.2f} < минимума {MIN_RISK_REWARD}"

    if risk / close > MAX_ATR_RATIO:
        return False, f"риск {risk/close*100:.1f}% > макс {MAX_ATR_RATIO*100:.0f}%"

    if atr <= 0:
        return False, "ATR = 0"

    return True, ""
