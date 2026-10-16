import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from valutatrade_hub.core import utils
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


class TestSingletonIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.data_dir = Path(self.temp_dir.name)

        patcher = patch.object(utils, "DATA_DIR", self.data_dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_utils_save_and_load(self):
        users = [{"user_id": 1, "username": "alice"}]

        utils.save_json("users.json", users)
        result = utils.load_json("users.json")

        self.assertEqual(result, users)
        self.assertTrue((self.data_dir / "users.json").exists())

    def test_utils_uses_database_manager(self):
        users = [{"user_id": 1}]

        with patch.object(DatabaseManager, "save") as mock_save:
            utils.save_json("users.json", users)

        mock_save.assert_called_once_with(
            "users.json",
            users,
            data_dir=self.data_dir,
        )

    def test_database_uses_settings_singleton(self):
        db1 = DatabaseManager()
        db2 = DatabaseManager()

        self.assertIs(db1, db2)
        self.assertIs(db1._settings, SettingsLoader())

    def test_json_data_is_preserved(self):
        portfolio = [
            {
                "user_id": 1,
                "wallets": {
                    "BTC": {"balance": 0.05},
                    "USD": {"balance": 150.0},
                },
            }
        ]

        utils.save_json("portfolios.json", portfolio)
        loaded = utils.load_json("portfolios.json")

        self.assertEqual(loaded, portfolio)
