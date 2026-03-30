# strategy/signals.py — сигналы входа и выхода
import pandas as pd
from strategy.indicators import prepare_data


def check_buy_signal(data: pd.DataFrame, params: dict) -> bool:
    """Проверяет сигнал на покупку на последней свече."""
    if len(data) < 2:
        return False

    row      = data.iloc[-1]
    prev_row = data.iloc[-2]
    close    = row["Close"]

    if any(pd.isna(v) for v in [close, row["MA50"], row["MA200"], row["RSI"],
                                  row["MACD"], row["MACD_sig"],
                                  prev_row["MACD"], prev_row["MACD_sig"]]):
        return False

    macd_cross = (
        row["MACD"]      > row["MACD_sig"] and
        prev_row["MACD"] <= prev_row["MACD_sig"]
    )

    return (
        close > row["MA50"]                                             and
        row["MA50"]  > row["MA200"]                                     and
        params["rsi_low"] < row["RSI"] < params["rsi_high"]            and
        close > prev_row["Close"]                                       and
        row["Volume"] > row["Volume_MA"] * params["volume_filter_mult"] and
        macd_cross
    )


def check_sell_signal(data: pd.DataFrame, position: dict) -> bool:
    """Проверяет сигнал на продажу."""
    row   = data.iloc[-1]
    close = row["Close"]

    if any(pd.isna(v) for v in [close, row["MA50"], row["RSI"]]):
        return False

    return (
        close <= position["stop"] or
        close >= position["take"] or
        close <  row["MA50"]      or
        row["RSI"] < 50
    )


def calc_trailing_stop(current_stop: float, close: float,
                        atr: float, mult: float) -> float:
    """Возвращает новый стоп — только вверх, никогда вниз."""
    return max(close - mult * atr, current_stop)
