# tests/test_signals.py — базовые тесты сигналов
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.signals import calc_trailing_stop


def test_trailing_stop_moves_up():
    assert calc_trailing_stop(90, 100, 3, 2.0) == 94.0

def test_trailing_stop_never_goes_down():
    assert calc_trailing_stop(95, 100, 3, 2.0) == 95

def test_trailing_stop_exact():
    assert calc_trailing_stop(80, 100, 5, 1.5) == 92.5


if __name__ == "__main__":
    tests = [test_trailing_stop_moves_up,
             test_trailing_stop_never_goes_down,
             test_trailing_stop_exact]
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
    print("Done.")
