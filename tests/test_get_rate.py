import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from valutatrade_hub.core import utils
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
)
from valutatrade_hub.core.usecases import (
    get_cached_rate,
    get_rate,
    is_rate_fresh,
    update_cached_rate,
)


class TestGetRate(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        patcher = patch.object(utils, "DATA_DIR", Path(self.temp_dir.name))
        patcher.start()
        self.addCleanup(patcher.stop)

        self.fresh_time = datetime.now(timezone.utc).isoformat()
        self.old_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()

        utils.save_json(
            "rates.json",
            {
                "BTC_USD": {
                    "rate": 59337.21,
                    "updated_at": self.fresh_time,
                },
                "EUR_USD": {
                    "rate": 1.0786,
                    "updated_at": self.old_time,
                },
                "source": "ParserService",
                "last_refresh": self.fresh_time,
            },
        )

    def test_fresh_rate(self):
        with patch("valutatrade_hub.core.usecases.update_cached_rate") as mock_update:
            result = get_rate("BTC", "USD")

        mock_update.assert_not_called()
        self.assertAlmostEqual(result["rate"], 59337.21)

    def test_reverse_rate(self):
        result = get_rate("USD", "BTC")

        self.assertAlmostEqual(result["rate"], 1 / 59337.21)
        self.assertAlmostEqual(result["reverse_rate"], 59337.21)

    def test_stale_rate_triggers_update(self):
        result = get_rate("EUR", "USD")

        self.assertAlmostEqual(result["rate"], 1.0786)

        rates = utils.load_json("rates.json")
        self.assertTrue(is_rate_fresh(rates["EUR_USD"]["updated_at"]))
        self.assertEqual(rates["source"], "MockParserService")

    def test_missing_rate_triggers_update(self):
        result = get_rate("ETH", "USD")

        self.assertEqual(result["rate"], 3720.0)

        rates = utils.load_json("rates.json")
        self.assertIn("ETH_USD", rates)

    def test_same_currency(self):
        result = get_rate("USD", "USD")

        self.assertEqual(result["rate"], 1.0)
        self.assertEqual(result["reverse_rate"], 1.0)
        self.assertIsNone(result["updated_at"])

    def test_unknown_currency(self):
        with self.assertRaises(CurrencyNotFoundError):
            get_rate("ABC", "USD")

    def test_missing_parser_rate(self):
        with self.assertRaisesRegex(
            ApiRequestError,
            "Ошибка при обращении к внешнему API:",
        ):
            get_rate("BTC", "EUR")

    def test_parser_error_does_not_modify_cache(self):
        before = utils.load_json("rates.json")

        with self.assertRaises(ApiRequestError):
            get_rate("BTC", "EUR")

        after = utils.load_json("rates.json")
        self.assertEqual(before, after)

    def test_freshness_check(self):
        self.assertTrue(is_rate_fresh(self.fresh_time))
        self.assertFalse(is_rate_fresh(self.old_time))

    def test_reverse_cached_rate(self):
        result = get_cached_rate("USD", "BTC")

        self.assertAlmostEqual(result["rate"], 1 / 59337.21)
        self.assertEqual(result["updated_at"], self.fresh_time)

    def test_update_cached_rate(self):
        result = update_cached_rate("BTC", "USD")

        self.assertEqual(result["rate"], 59337.21)
        self.assertTrue(is_rate_fresh(result["updated_at"]))

        rates = utils.load_json("rates.json")
        self.assertEqual(rates["BTC_USD"]["rate"], 59337.21)

    def test_invalid_rate(self):
        rates = utils.load_json("rates.json")
        rates["BTC_USD"]["rate"] = -100
        utils.save_json("rates.json", rates)

        with self.assertRaises(ValueError):
            get_cached_rate("BTC", "USD")

    @patch("valutatrade_hub.core.usecases.SettingsLoader")
    def test_ttl_from_settings(self, mock_settings):
        mock_settings.return_value.get.return_value = 600

        updated_at = (datetime.now(timezone.utc) - timedelta(minutes=7)).isoformat()

        self.assertTrue(is_rate_fresh(updated_at))
        mock_settings.return_value.get.assert_called_once_with("rates_ttl_seconds", 300)
