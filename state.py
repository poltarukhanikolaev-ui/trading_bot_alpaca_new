# core/state.py — атомарное хранение состояния бота между запусками
import json, csv, os, logging, tempfile, shutil
from datetime import datetime
from config.settings import TRADE_FILE, STATE_FILE

logger = logging.getLogger(__name__)


def _atomic_write_json(filepath: str, data: dict) -> None:
    """Write → rename — атомарная операция, файл никогда не повреждается."""
    dirpath = os.path.dirname(os.path.abspath(filepath)) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, filepath)
    except Exception:
        os.unlink(tmp)
        raise


def _load_json_safe(filepath: str) -> dict:
    """Читает JSON; при повреждении пробует .bak резервную копию."""
    for path in [filepath, filepath + ".bak"]:
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read {path}: {e}")
    return {}


# ── Мета-данные позиций ───────────────────────────────────────────────

def load_positions_meta() -> dict:
    return _load_json_safe(STATE_FILE)


def save_positions_meta(meta: dict) -> None:
    if os.path.exists(STATE_FILE):
        try:
            shutil.copy2(STATE_FILE, STATE_FILE + ".bak")
        except Exception:
            pass
    _atomic_write_json(STATE_FILE, meta)


def add_position_meta(symbol: str, entry_price: float,
                      stop: float, take: float, qty: float) -> None:
    meta = load_positions_meta()
    meta[symbol] = {
        "entry_price":    entry_price,
        "stop":           stop,
        "take":           take,
        "qty":            qty,
        "qty_remaining":  qty,
        "entry_date":     datetime.now().strftime("%Y-%m-%d %H:%M"),
        "breakeven_done": False,
        "partial_done":   False,
    }
    save_positions_meta(meta)


def update_stop(symbol: str, new_stop: float) -> None:
    meta = load_positions_meta()
    if symbol in meta:
        meta[symbol]["stop"] = new_stop
        save_positions_meta(meta)


def set_breakeven_done(symbol: str, breakeven_stop: float) -> None:
    meta = load_positions_meta()
    if symbol in meta:
        meta[symbol]["breakeven_done"] = True
        meta[symbol]["stop"]           = breakeven_stop
        save_positions_meta(meta)


def set_partial_done(symbol: str, qty_remaining: float) -> None:
    meta = load_positions_meta()
    if symbol in meta:
        meta[symbol]["partial_done"]  = True
        meta[symbol]["qty_remaining"] = qty_remaining
        save_positions_meta(meta)


def remove_position_meta(symbol: str) -> None:
    meta = load_positions_meta()
    if symbol in meta:
        del meta[symbol]
        save_positions_meta(meta)


# ── Лог сделок ────────────────────────────────────────────────────────

TRADE_HEADERS = ["date", "symbol", "side", "entry_price", "exit_price",
                 "qty", "profit", "reason", "portfolio_value"]


def log_trade(symbol: str, side: str, entry_price: float, exit_price: float,
              qty: float, profit: float, reason: str, portfolio_value: float) -> None:
    rows: list[dict] = []
    if os.path.exists(TRADE_FILE):
        try:
            with open(TRADE_FILE, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except Exception as e:
            logger.error(f"log_trade read: {e}")

    rows.append({
        "date":            datetime.now().strftime("%Y-%m-%d %H:%M"),
        "symbol":          symbol, "side": side,
        "entry_price":     round(entry_price, 4),
        "exit_price":      round(exit_price, 4),
        "qty":             round(qty, 4),
        "profit":          round(profit, 2),
        "reason":          reason,
        "portfolio_value": round(portfolio_value, 2),
    })

    dirpath = os.path.dirname(os.path.abspath(TRADE_FILE)) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=TRADE_HEADERS)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, TRADE_FILE)
    except Exception as e:
        os.unlink(tmp)
        logger.error(f"log_trade write: {e}")


def load_trades() -> list[dict]:
    if not os.path.exists(TRADE_FILE):
        return []
    try:
        with open(TRADE_FILE, encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        logger.error(f"load_trades: {e}")
        return []
