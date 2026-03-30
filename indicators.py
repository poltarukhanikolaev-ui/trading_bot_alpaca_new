# strategy/indicators.py — загрузка данных и технические индикаторы
import pandas as pd
import numpy as np
import yfinance as yf


def prepare_data(symbol: str, period: str = "1y",
                 interval: str = "1d") -> pd.DataFrame | None:
    """
    Загружает данные и считает индикаторы.
    interval: "1d" (дневной) или "1h" (часовой) для мультитаймфрейма.
    """
    try:
        data = yf.download(symbol, period=period, interval=interval,
                           progress=False, auto_adjust=True)
    except Exception:
        return None

    min_bars = 210 if interval == "1d" else 50
    if data.empty or len(data) < min_bars:
        return None

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Скользящие средние
    data["MA50"]       = data["Close"].rolling(50).mean()
    data["MA200"]      = data["Close"].rolling(200).mean()
    data["MA50_slope"] = data["MA50"] - data["MA50"].shift(5)

    # RSI (14)
    delta    = data["Close"].diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs       = avg_gain / avg_loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # ATR (14)
    high_low   = data["High"] - data["Low"]
    high_close = (data["High"] - data["Close"].shift()).abs()
    low_close  = (data["Low"]  - data["Close"].shift()).abs()
    tr         = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data["ATR"] = tr.rolling(14).mean()

    # Объём
    data["Volume_MA"] = data["Volume"].rolling(20).mean()

    # MACD (12/26/9)
    ema12            = data["Close"].ewm(span=12, adjust=False).mean()
    ema26            = data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD"]     = ema12 - ema26
    data["MACD_sig"] = data["MACD"].ewm(span=9, adjust=False).mean()

    return data.dropna()
