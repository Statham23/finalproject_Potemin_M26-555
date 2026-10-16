import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Создаём временную папку для каждого теста
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.data_dir = Path(self.temp_dir.name)

        # Подменяем настройку data_dir на временную папку
        self.settings = SettingsLoader()

        patcher = patch.dict(
            self.settings._settings,
            {"data_dir": str(self.data_dir)},
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        self.db = DatabaseManager()

    def test_singleton(self):
        db1 = DatabaseManager()
        db2 = DatabaseManager()

        self.assertIs(db1, db2)

    def test_save_and_load(self):
        users = [
            {"user_id": 1, "username": "alice"},
            {"user_id": 2, "username": "bob"},
        ]

        self.db.save("users.json", users)
        result = self.db.load("users.json")

        self.assertEqual(result, users)

    def test_save_dictionary(self):
        rates = {
            "BTC_USD": {
                "rate": 59337.21,
                "updated_at": "2025-10-09T10:29:42",
            }
        }

        self.db.save("rates.json", rates)
        result = self.db.load("rates.json")

        self.assertEqual(result, rates)

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            self.db.load("missing.json")

    def test_invalid_extension(self):
        with self.assertRaises(ValueError):
            self.db.load("users.txt")

    def test_path_traversal(self):
        with self.assertRaises(ValueError):
            self.db.load("../users.json")

    def test_nested_path(self):
        with self.assertRaises(ValueError):
            self.db.load("other/users.json")

    def test_unicode_data(self):
        users = [{"username": "Александр"}]

        self.db.save("users.json", users)

        file_text = (self.data_dir / "users.json").read_text(encoding="utf-8")

        self.assertIn("Александр", file_text)

    def test_repeated_access(self):
        self.db.save("users.json", [{"user_id": 1}])

        another_db = DatabaseManager()
        result = another_db.load("users.json")

        self.assertEqual(result, [{"user_id": 1}])
