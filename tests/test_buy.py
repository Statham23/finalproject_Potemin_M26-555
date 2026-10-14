import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from valutatrade_hub.core import utils
from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.core.usecases import buy


class TestBuy(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        patcher = patch.object(utils, "DATA_DIR", Path(self.temp_dir.name))
        patcher.start()
        self.addCleanup(patcher.stop)

        utils.save_json(
            "portfolios.json",
            [
                {
                    "user_id": 1,
                    "wallets": {
                        "BTC": {"balance": 0.07},
                    },
                }
            ],
        )

        utils.save_json(
            "rates.json",
            {
                "BTC_USD": {"rate": 59337.21},
                "ETH_USD": {"rate": 3720.0},
                "source": "ParserService",
            },
        )

    def test_buy_existing_currency(self):
        result = buy(1, "BTC", 0.05)

        self.assertAlmostEqual(result["old_balance"], 0.07)
        self.assertAlmostEqual(result["new_balance"], 0.12)
        self.assertAlmostEqual(result["estimated_cost"], 2966.8605)

    def test_buy_creates_wallet(self):
        result = buy(1, "ETH", 2)

        self.assertEqual(result["old_balance"], 0.0)
        self.assertEqual(result["new_balance"], 2.0)

        portfolios = utils.load_json("portfolios.json")
        self.assertEqual(portfolios[0]["wallets"]["ETH"]["balance"], 2.0)

    def test_buy_saves_balance(self):
        buy(1, "BTC", 0.05)

        portfolios = utils.load_json("portfolios.json")
        self.assertAlmostEqual(portfolios[0]["wallets"]["BTC"]["balance"], 0.12)

    def test_invalid_amount(self):
        for amount in [0, -1, float("nan"), float("inf"), True]:
            with self.subTest(amount=amount):
                with self.assertRaisesRegex(ValueError, "положительным числом"):
                    buy(1, "BTC", amount)

    def test_unknown_currency(self):
        with self.assertRaises(CurrencyNotFoundError):
            buy(1, "ABC", 1)

    def test_missing_rate_does_not_change_balance(self):
        utils.save_json("rates.json", {})

        before = utils.load_json("portfolios.json")

        with self.assertRaisesRegex(ValueError, "Не удалось получить курс"):
            buy(1, "BTC", 0.05)

        after = utils.load_json("portfolios.json")
        self.assertEqual(before, after)

    def test_invalid_amount_does_not_change_balance(self):
        before = utils.load_json("portfolios.json")

        with self.assertRaises(ValueError):
            buy(1, "BTC", -5)

        after = utils.load_json("portfolios.json")
        self.assertEqual(before, after)

    def test_buy_does_not_debit_usd(self):
        portfolios = utils.load_json("portfolios.json")
        portfolios[0]["wallets"]["USD"] = {"balance": 100.0}
        utils.save_json("portfolios.json", portfolios)

        buy(1, "BTC", 0.05)

        updated = utils.load_json("portfolios.json")
        self.assertEqual(updated[0]["wallets"]["USD"]["balance"], 100.0)
