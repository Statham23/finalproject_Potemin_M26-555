import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Singleton для работы с JSON-хранилищем."""

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
            self._settings = SettingsLoader()

    def _get_file_path(
        self,
        filename: str,
        data_dir: Path | None = None,
    ) -> Path:
        """Возвращает безопасный путь к JSON-файлу."""
        project_root = Path(__file__).resolve().parents[2]

        if data_dir is None:
            data_dir = Path(self._settings.get("data_dir"))

        if not data_dir.is_absolute():
            data_dir = project_root / data_dir

        data_dir = data_dir.resolve()
        file_path = (data_dir / filename).resolve()

        if file_path.parent != data_dir or file_path.suffix != ".json":
            raise ValueError("Недопустимое имя JSON-файла")

        return file_path

    def load(
        self,
        filename: str,
        data_dir: Path | None = None,
    ) -> Any:
        """Загружает данные из JSON-файла."""
        file_path = self._get_file_path(filename, data_dir)

        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def save(
        self,
        filename: str,
        data: Any,
        data_dir: Path | None = None,
    ) -> None:
        """Атомарно сохраняет данные в JSON-файл."""
        file_path = self._get_file_path(filename, data_dir)

        json_text = json.dumps(
            data,
            ensure_ascii=False,
            indent=4,
        )

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=file_path.parent,
                prefix=f".{file_path.stem}_",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                temp_file.write(json_text)
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(temp_path, file_path)

        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
