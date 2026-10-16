from pathlib import Path
from typing import Any

from valutatrade_hub.infra.database import DatabaseManager

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_json(filename: str) -> Any:
    db = DatabaseManager()
    return db.load(filename, data_dir=DATA_DIR)


def save_json(filename: str, data: Any) -> None:
    db = DatabaseManager()
    db.save(filename, data, data_dir=DATA_DIR)
