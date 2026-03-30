# 📈 Alpaca Trading Bot

Momentum trading bot для paper trading на акциях через Alpaca API.
Стратегия: MA50/MA200 + RSI + MACD + ATR + мультитаймфрейм + анти-бот защита.

## Структура

```
trading-bot/
├── config/
│   ├── settings.example.py   ← скопируй в settings.py и заполни
│   └── settings.py           ← (в .gitignore — не попадёт в репо)
│
├── strategy/                 ← логика стратегии
│   ├── indicators.py         ← RSI, MACD, ATR, MA
│   ├── signals.py            ← check_buy / check_sell / trailing stop
│   └── filters.py            ← фильтр рынка SPY, мультитаймфрейм
│
├── exchange/
│   └── alpaca.py             ← Alpaca API (ордера, позиции, аккаунт)
│
├── core/                     ← инфраструктура
│   ├── state.py              ← атомарное хранение, лог сделок
│   ├── notifier.py           ← Telegram уведомления
│   └── logger.py             ← настройка логирования
│
├── bot/                      ← оркестрация
│   ├── runner.py             ← главный цикл (рынок → позиции → входы)
│   ├── scheduler.py          ← расписание (каждый час + дневной отчёт)
│   └── validator.py          ← валидация сигнала перед ордером
│
├── research/                 ← бэктест и оптимизация
│   ├── backtest.py
│   ├── grid_search.py
│   └── walk_forward.py
│
├── scripts/
│   └── run.py                ← точка входа
│
└── tests/
    ├── test_validator.py
    └── test_signals.py
```

## Быстрый старт

```bash
git clone https://github.com/YOUR_USERNAME/trading-bot.git
cd trading-bot
cp config/settings.example.py config/settings.py
# заполни config/settings.py своими ключами
pip install -r requirements.txt
python scripts/run.py
```

## Получение ключей

**Alpaca:** alpaca.markets → Paper Trading → API Keys → Generate

**Telegram:** `@BotFather` → `/newbot` → токен. Chat ID → `@userinfobot`

## Запуск тестов

```bash
python tests/test_validator.py
python tests/test_signals.py
```

## ⚠️ Только paper trading. Не использовать для реальной торговли без дополнительного тестирования.
