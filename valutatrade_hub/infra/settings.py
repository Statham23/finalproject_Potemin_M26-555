import threading
import tomllib
from pathlib import Path
from typing import Any


class SettingsLoader:
    """Singleton для загрузки и кеширования настроек проекта."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):
        if not hasattr(self, "_settings"):
            self._config_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
            self.reload()

    def reload(self) -> None:
        """Перечитывает настройки из pyproject.toml."""
        with self._config_path.open("rb") as file:
            config = tomllib.load(file)

        self._settings = config["tool"]["valutatrade"]

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает настройку или значение по умолчанию."""
        return self._settings.get(key, default)
