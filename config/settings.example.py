# config/settings.example.py — шаблон
# cp config/settings.example.py config/settings.py

ALPACA_API_KEY    = "YOUR_ALPACA_API_KEY"
ALPACA_SECRET_KEY = "YOUR_ALPACA_SECRET_KEY"
ALPACA_BASE_URL   = "https://paper-api.alpaca.markets"

TELEGRAM_TOKEN   = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "AMD", "NFLX", "INTC",
]

PARAMS = {
    "risk_per_trade":     0.02,
    "trailing_atr_mult":  2.0,
    "volume_filter_mult": 1.5,
    "max_positions":      5,
    "rsi_low":            60,
    "rsi_high":           75,
}

INITIAL_CAPITAL   = 100_000
MIN_TRADES        = 5
STOP_JITTER_MIN   = 0.0
STOP_JITTER_MAX   = 0.35
ENTRY_DELAY_MIN   = 60
ENTRY_DELAY_MAX   = 300
MIN_RISK_REWARD   = 2.0
MAX_ATR_RATIO     = 0.05
PARTIAL_CLOSE_PCT = 0.50
PARTIAL_TARGET    = 0.50
BREAKEVEN_TARGET  = 0.50
LOG_FILE          = "bot.log"
TRADE_FILE        = "trades.csv"
STATE_FILE        = "positions_meta.json"
