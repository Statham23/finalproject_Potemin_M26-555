import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from valutatrade_hub.core import utils
from valutatrade_hub.core.usecases import show_portfolio


class TestShowPortfolio(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.data_dir = Path(self.temp_dir.name)

        patcher = patch.object(utils, "DATA_DIR", self.data_dir)
        patcher.start()
        self.addCleanup(patcher.stop)

        utils.save_json(
            "portfolios.json",
            [
                {
                    "user_id": 1,
                    "wallets": {
                        "USD": {"balance": 150.0},
                        "BTC": {"balance": 0.05},
                        "EUR": {"balance": 200.0},
                    },
                }
            ],
        )

        utils.save_json(
            "rates.json",
            {
                "BTC_USD": {"rate": 59337.21, "updated_at": "2025-10-09T10:29:42"},
                "EUR_USD": {"rate": 1.0786, "updated_at": "2025-10-09T10:30:00"},
                "source": "ParserService",
                "last_refresh": "2025-10-09T10:35:00",
            },
        )

    def test_default_base_usd(self):
        result = show_portfolio(1)

        self.assertEqual(result["base_currency"], "USD")
        self.assertEqual(len(result["wallets"]), 3)
        self.assertAlmostEqual(result["total"], 3332.5805)

    def test_base_eur(self):
        result = show_portfolio(1, "EUR")

        self.assertEqual(result["base_currency"], "EUR")
        self.assertAlmostEqual(result["total"], 3332.5805 / 1.0786)

    def test_wallet_values(self):
        result = show_portfolio(1)
        values = {
            wallet["currency_code"]: wallet["value"] for wallet in result["wallets"]
        }

        self.assertAlmostEqual(values["USD"], 150.0)
        self.assertAlmostEqual(values["BTC"], 2966.8605)
        self.assertAlmostEqual(values["EUR"], 215.72)

    def test_unknown_base_currency(self):
        with self.assertRaisesRegex(ValueError, "Неизвестная базовая валюта 'ABC'"):
            show_portfolio(1, "ABC")

    def test_empty_portfolio(self):
        utils.save_json(
            "portfolios.json",
            [{"user_id": 1, "wallets": {}}],
        )

        result = show_portfolio(1)

        self.assertEqual(result["wallets"], [])
        self.assertEqual(result["total"], 0.0)

    def test_missing_portfolio(self):
        with self.assertRaisesRegex(ValueError, "не найден"):
            show_portfolio(999)

    def test_missing_exchange_rate(self):
        utils.save_json(
            "rates.json",
            {
                "EUR_USD": {"rate": 1.0786},
                "source": "ParserService",
            },
        )

        with self.assertRaises(ValueError):
            show_portfolio(1)

    def test_portfolio_data_is_not_modified(self):
        before = utils.load_json("portfolios.json")

        show_portfolio(1)

        after = utils.load_json("portfolios.json")
        self.assertEqual(before, after)
