# exchange/alpaca.py — взаимодействие с Alpaca Paper Trading API
import requests
import logging
from config.settings import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL

logger = logging.getLogger(__name__)

HEADERS = {
    "APCA-API-KEY-ID":     ALPACA_API_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
    "Content-Type":        "application/json",
}


def _get(endpoint: str) -> dict | None:
    try:
        r = requests.get(f"{ALPACA_BASE_URL}{endpoint}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"GET {endpoint}: {e}")
        return None


def _post(endpoint: str, payload: dict) -> dict | None:
    try:
        r = requests.post(f"{ALPACA_BASE_URL}{endpoint}",
                          headers=HEADERS, json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"POST {endpoint}: {e}")
        return None


def _delete(endpoint: str) -> bool:
    try:
        r = requests.delete(f"{ALPACA_BASE_URL}{endpoint}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"DELETE {endpoint}: {e}")
        return False


# ── Аккаунт ───────────────────────────────────────────────────────────

def get_account() -> dict | None:
    return _get("/v2/account")

def get_portfolio_value() -> float:
    acc = get_account()
    return float(acc["portfolio_value"]) if acc else 0.0

def get_cash() -> float:
    acc = get_account()
    return float(acc["cash"]) if acc else 0.0

def is_market_open() -> bool:
    clock = _get("/v2/clock")
    return clock.get("is_open", False) if clock else False


# ── Позиции ───────────────────────────────────────────────────────────

def get_positions() -> list[dict]:
    result = _get("/v2/positions")
    return result if isinstance(result, list) else []

def get_position(symbol: str) -> dict | None:
    return _get(f"/v2/positions/{symbol}")

def close_position(symbol: str) -> bool:
    ok = _delete(f"/v2/positions/{symbol}")
    if ok:
        logger.info(f"Position closed: {symbol}")
    return ok


# ── Ордера ────────────────────────────────────────────────────────────

def place_market_buy(symbol: str, qty: float) -> dict | None:
    qty = round(qty, 4)
    if qty <= 0:
        return None
    order = _post("/v2/orders", {
        "symbol": symbol, "qty": str(qty),
        "side": "buy", "type": "market", "time_in_force": "day",
    })
    if order:
        logger.info(f"BUY {symbol} qty={qty} | id={order.get('id')}")
    return order

def place_market_sell(symbol: str, qty: float) -> dict | None:
    qty = round(qty, 4)
    if qty <= 0:
        return None
    order = _post("/v2/orders", {
        "symbol": symbol, "qty": str(qty),
        "side": "sell", "type": "market", "time_in_force": "day",
    })
    if order:
        logger.info(f"SELL {symbol} qty={qty} | id={order.get('id')}")
    return order
