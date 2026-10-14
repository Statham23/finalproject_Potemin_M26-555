import unittest

from valutatrade_hub.core.models import Wallet


class TestWallet(unittest.TestCase):
    def setUp(self):
        self.wallet = Wallet("USD", 100.0)

    def test_create_wallet(self):
        self.assertEqual(self.wallet.currency_code, "USD")
        self.assertEqual(self.wallet.balance, 100.0)

    def test_default_balance(self):
        wallet = Wallet("BTC")
        self.assertEqual(wallet.balance, 0.0)

    def test_deposit(self):
        self.wallet.deposit(50.0)
        self.assertAlmostEqual(self.wallet.balance, 150.0)

    def test_withdraw(self):
        self.wallet.withdraw(30.0)
        self.assertAlmostEqual(self.wallet.balance, 70.0)

    def test_withdraw_all(self):
        self.wallet.withdraw(100.0)
        self.assertEqual(self.wallet.balance, 0.0)

    def test_insufficient_funds(self):
        with self.assertRaises(ValueError):
            self.wallet.withdraw(150.0)

        self.assertEqual(self.wallet.balance, 100.0)

    def test_invalid_deposit(self):
        for amount in [-10, 0, float("nan"), float("inf")]:
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    self.wallet.deposit(amount)

        self.assertEqual(self.wallet.balance, 100.0)

    def test_invalid_withdraw(self):
        for amount in [-10, 0, float("nan"), float("inf")]:
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    self.wallet.withdraw(amount)

        self.assertEqual(self.wallet.balance, 100.0)

    def test_invalid_amount_type(self):
        for amount in ["100", None, True]:
            with self.subTest(amount=amount):
                with self.assertRaises(TypeError):
                    self.wallet.deposit(amount)

                with self.assertRaises(TypeError):
                    self.wallet.withdraw(amount)

    def test_negative_balance(self):
        with self.assertRaises(ValueError):
            self.wallet.balance = -100.0

        self.assertEqual(self.wallet.balance, 100.0)

    def test_invalid_balance_type(self):
        with self.assertRaises(TypeError):
            self.wallet.balance = "hello"

    def test_invalid_initial_balance(self):
        with self.assertRaises(ValueError):
            Wallet("USD", -50.0)

    def test_empty_currency_code(self):
        with self.assertRaises(ValueError):
            Wallet("")

    def test_get_balance_info(self):
        expected = {
            "currency_code": "USD",
            "balance": 100.0,
        }

        self.assertEqual(self.wallet.get_balance_info(), expected)
