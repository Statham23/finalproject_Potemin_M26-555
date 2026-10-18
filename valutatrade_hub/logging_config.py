import logging
import sys
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


class ISOFormatter(logging.Formatter):
    """Форматирует время записи в ISO 8601."""

    def formatTime(self, record, datefmt=None):
        return (
            datetime.fromtimestamp(record.created)
            .astimezone()
            .isoformat(timespec="seconds")
        )


class ParserConsoleFormatter(logging.Formatter):
    """Выводит краткие сообщения без traceback."""

    def format(self, record: logging.LogRecord) -> str:
        return f"{record.levelname}: {record.getMessage()}"


def setup_logging() -> logging.Logger:
    """Настраивает логирование доменных операций."""
    settings = SettingsLoader()

    logger = logging.getLogger("valutatrade.actions")

    level_name = settings.get("log_level", "INFO")
    level = logging.getLevelNamesMapping().get(level_name.upper())

    if level is None:
        raise ValueError(f"Неизвестный уровень логирования: {level_name}")

    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        return logger

    project_root = Path(__file__).resolve().parents[1]

    log_dir = Path(settings.get("log_dir", "logs"))

    if not log_dir.is_absolute():
        log_dir = project_root / log_dir

    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / settings.get("log_file", "actions.log")

    handler = RotatingFileHandler(
        log_file,
        maxBytes=settings.get("log_max_bytes", 1_048_576),
        backupCount=settings.get("log_backup_count", 3),
        encoding="utf-8",
    )

    formatter = ISOFormatter(
        settings.get(
            "log_format",
            "%(levelname)s %(asctime)s %(message)s",
        )
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def setup_parser_logging() -> logging.Logger:
    """Настраивает отдельное файловое логирование Parser Service."""

    settings = SettingsLoader()

    logger = logging.getLogger("valutatrade.parser")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if any(isinstance(handler, RotatingFileHandler) for handler in logger.handlers):
        return logger

    project_root = Path(__file__).resolve().parents[1]

    log_dir = Path(settings.get("log_dir", "logs"))

    if not log_dir.is_absolute():
        log_dir = project_root / log_dir

    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "parser.log"

    handler = RotatingFileHandler(
        log_file,
        maxBytes=settings.get("log_max_bytes", 1_048_576),
        backupCount=settings.get("log_backup_count", 3),
        encoding="utf-8",
    )

    handler.setLevel(logging.DEBUG)

    handler.setFormatter(
        ISOFormatter("%(levelname)s %(asctime)s [%(name)s] %(message)s")
    )

    logger.addHandler(handler)

    return logger


@contextmanager
def parser_console_logging() -> Generator[None, None, None]:
    """Временно выводит сообщения Parser Service в консоль."""

    logger = setup_parser_logging()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    console_handler.setFormatter(ParserConsoleFormatter())

    logger.addHandler(console_handler)

    try:
        yield
    finally:
        logger.removeHandler(console_handler)
        console_handler.close()
