# tests/test_validator.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.validator import validate_signal


def test_valid_signal():
    ok, reason = validate_signal(close=100, stop=97, take=106, atr=2.0)
    assert ok, reason

def test_rr_too_low():
    ok, reason = validate_signal(close=100, stop=98, take=101, atr=2.0)
    assert not ok
    assert "R/R" in reason

def test_stop_above_close():
    ok, reason = validate_signal(close=100, stop=101, take=110, atr=2.0)
    assert not ok

def test_atr_zero():
    ok, reason = validate_signal(close=100, stop=97, take=106, atr=0)
    assert not ok
    assert "ATR" in reason

def test_risk_too_large():
    # стоп 10% от цены — выше MAX_ATR_RATIO=5%
    ok, reason = validate_signal(close=100, stop=89, take=133, atr=11.0)
    assert not ok


if __name__ == "__main__":
    tests = [test_valid_signal, test_rr_too_low, test_stop_above_close,
             test_atr_zero, test_risk_too_large]
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
    print("Done.")
