import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from valutatrade_hub.core import utils
from valutatrade_hub.core.exceptions import (
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import sell


class TestSell(unittest.TestCase):
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
                        "BTC": {"balance": 0.05},
                        "USD": {"balance": 150.0},
                    },
                }
            ],
        )

        utils.save_json(
            "rates.json",
            {
                "BTC_USD": {"rate": 59337.21},
                "source": "ParserService",
            },
        )

    def test_successful_sell(self):
        result = sell(1, "BTC", 0.01)

        self.assertEqual(result["currency_code"], "BTC")
        self.assertAlmostEqual(result["old_balance"], 0.05)
        self.assertAlmostEqual(result["new_balance"], 0.04)
        self.assertAlmostEqual(result["estimated_revenue"], 593.3721)

    def test_sell_saves_balance(self):
        sell(1, "BTC", 0.01)

        portfolios = utils.load_json("portfolios.json")

        self.assertAlmostEqual(
            portfolios[0]["wallets"]["BTC"]["balance"],
            0.04,
        )

    def test_sell_entire_balance(self):
        result = sell(1, "BTC", 0.05)

        self.assertAlmostEqual(result["new_balance"], 0.0)

    def test_missing_wallet(self):
        before = utils.load_json("portfolios.json")

        with self.assertRaisesRegex(ValueError, "У вас нет кошелька"):
            sell(1, "ETH", 1)

        after = utils.load_json("portfolios.json")
        self.assertEqual(before, after)

    def test_insufficient_funds(self):
        with self.assertRaisesRegex(
            InsufficientFundsError,
            "Недостаточно средств",
        ):
            sell(1, "BTC", 0.06)

    def test_insufficient_funds_does_not_change_balance(self):
        before = utils.load_json("portfolios.json")

        with self.assertRaises(InsufficientFundsError):
            sell(1, "BTC", 0.06)

        after = utils.load_json("portfolios.json")
        self.assertEqual(before, after)

    def test_invalid_amount(self):
        for amount in [0, -1, float("nan"), float("inf"), True]:
            with self.subTest(amount=amount):
                with self.assertRaisesRegex(
                    ValueError,
                    "положительным числом",
                ):
                    sell(1, "BTC", amount)

    def test_unknown_currency(self):
        with self.assertRaises(CurrencyNotFoundError):
            sell(1, "ABC", 1)

    def test_missing_rate_does_not_change_balance(self):
        utils.save_json("rates.json", {})

        before = utils.load_json("portfolios.json")

        with self.assertRaisesRegex(ValueError, "Не удалось получить курс"):
            sell(1, "BTC", 0.01)

        after = utils.load_json("portfolios.json")
        self.assertEqual(before, after)

    def test_sell_does_not_credit_usd(self):
        sell(1, "BTC", 0.01)

        portfolios = utils.load_json("portfolios.json")

        self.assertEqual(
            portfolios[0]["wallets"]["USD"]["balance"],
            150.0,
        )

    def test_sell_usd(self):
        result = sell(1, "USD", 100)

        self.assertEqual(result["rate"], 1.0)
        self.assertEqual(result["estimated_revenue"], 100.0)
        self.assertEqual(result["new_balance"], 50.0)
