import tempfile
import unittest
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


class TestSettingsLoader(unittest.TestCase):
    def test_singleton(self):
        settings1 = SettingsLoader()
        settings2 = SettingsLoader()

        self.assertIs(settings1, settings2)

    def test_load_configuration(self):
        settings = SettingsLoader()

        self.assertEqual(settings.get("data_dir"), "data")
        self.assertEqual(settings.get("rates_ttl_seconds"), 300)
        self.assertEqual(settings.get("default_base_currency"), "USD")

    def test_get_existing_key(self):
        settings = SettingsLoader()

        self.assertEqual(settings.get("users_file"), "users.json")
        self.assertEqual(settings.get("rates_file"), "rates.json")

    def test_get_unknown_key(self):
        settings = SettingsLoader()

        self.assertIsNone(settings.get("unknown_key"))
        self.assertEqual(
            settings.get("unknown_key", "default_value"),
            "default_value",
        )

    def test_reload(self):
        settings = SettingsLoader()

        original_path = settings._config_path

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "pyproject.toml"

                temp_path.write_text(
                    "[tool.valutatrade]\n"
                    'data_dir = "test_data"\n'
                    "rates_ttl_seconds = 600\n"
                    'default_base_currency = "EUR"\n',
                    encoding="utf-8",
                )

                settings._config_path = temp_path
                settings.reload()

                self.assertEqual(settings.get("data_dir"), "test_data")
                self.assertEqual(settings.get("rates_ttl_seconds"), 600)
                self.assertEqual(
                    settings.get("default_base_currency"),
                    "EUR",
                )

        finally:
            settings._config_path = original_path
            settings.reload()
