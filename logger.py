# core/logger.py — настройка логирования
import logging
from config.settings import LOG_FILE


def setup_logger() -> None:
    """Инициализирует корневой логгер: файл + консоль."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ]
    )
