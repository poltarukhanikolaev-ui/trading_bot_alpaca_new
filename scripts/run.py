#!/usr/bin/env python3
# scripts/run.py — точка входа
# Запуск: python scripts/run.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.scheduler import start

if __name__ == "__main__":
    start()
