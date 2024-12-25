import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файловый обработчик с ротацией
    file_handler = RotatingFileHandler("app.log", maxBytes=10**6, backupCount=5)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)