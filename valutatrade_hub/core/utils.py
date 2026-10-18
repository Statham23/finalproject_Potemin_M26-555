from pathlib import Path
from typing import Any

from valutatrade_hub.infra.database import DatabaseManager

DATA_DIR: Path | None = None


def load_json(filename: str) -> Any:
    """Загружает JSON-файл через DatabaseManager."""
    db = DatabaseManager()
    return db.load(filename, data_dir=DATA_DIR)


def save_json(filename: str, data: Any) -> None:
    """Атомарно сохраняет данные в JSON-файл через DatabaseManager."""
    db = DatabaseManager()
    db.save(filename, data, data_dir=DATA_DIR)
