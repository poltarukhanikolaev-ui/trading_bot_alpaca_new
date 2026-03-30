# strategy/filters.py — фильтр рынка, мультитаймфрейм, анти-бот защита
import pandas as pd
from strategy.indicators import prepare_data


def market_is_bullish(spy_data: pd.DataFrame) -> bool:
    """
    3-уровневый фильтр рынка по SPY:
      1. SPY > MA200  — базовый бычий тренд
      2. MA50_slope > 0 — тренд набирает силу
      3. SPY > MA50  — нет краткосрочного слома
    """
    if spy_data is None or spy_data.empty:
        return False

    row = spy_data.iloc[-1]

    if pd.isna(row["MA200"]) or row["Close"] < row["MA200"]:
        return False
    if pd.isna(row["MA50_slope"]) or row["MA50_slope"] <= 0:
        return False
    if pd.isna(row["MA50"]) or row["Close"] < row["MA50"]:
        return False

    return True


def check_mtf_confirm(symbol: str, params: dict) -> bool:
    """
    Мультитаймфреймовое подтверждение (анти-бот, из статьи Хабр):
      - Дневной (1d): MA50 > MA200 + RSI в зоне
      - Часовой (1h): MACD crossover + объём
    Оба таймфрейма должны совпасть для входа.
    """
    # Дневной — тренд
    daily = prepare_data(symbol, period="1y", interval="1d")
    if daily is None or len(daily) < 2:
        return False

    d = daily.iloc[-1]
    if not (d["Close"] > d["MA50"] > d["MA200"] and
            params["rsi_low"] < d["RSI"] < params["rsi_high"]):
        return False

    # Часовой — импульс
    hourly = prepare_data(symbol, period="60d", interval="1h")
    if hourly is None or len(hourly) < 2:
        return False

    h      = hourly.iloc[-1]
    h_prev = hourly.iloc[-2]

    if any(pd.isna(v) for v in [h["MACD"], h["MACD_sig"],
                                  h_prev["MACD"], h_prev["MACD_sig"]]):
        return False

    macd_cross  = h["MACD"] > h["MACD_sig"] and h_prev["MACD"] <= h_prev["MACD_sig"]
    volume_ok   = h["Volume"] > h["Volume_MA"] * params["volume_filter_mult"]

    return macd_cross and volume_ok
