import unittest
from datetime import datetime

from valutatrade_hub.core.models import Portfolio, User, Wallet


class TestPortfolio(unittest.TestCase):
    def setUp(self):
        self.portfolio = Portfolio(
            user_id=1,
            wallets={
                "USD": Wallet("USD", 1000.0),
                "BTC": Wallet("BTC", 0.05),
                "EUR": Wallet("EUR", 200.0),
            },
        )

    def test_create_portfolio(self):
        self.assertEqual(self.portfolio.user_id, 1)
        self.assertEqual(len(self.portfolio.wallets), 3)

    def test_empty_portfolio(self):
        portfolio = Portfolio(user_id=2)

        self.assertEqual(portfolio.wallets, {})
        self.assertEqual(portfolio.get_total_value(), 0.0)

    def test_invalid_user_id(self):
        with self.assertRaises(ValueError):
            Portfolio(user_id=-1)

    def test_add_currency(self):
        self.portfolio.add_currency("ETH")

        self.assertIn("ETH", self.portfolio.wallets)
        self.assertEqual(self.portfolio.get_wallet("ETH").balance, 0.0)

    def test_duplicate_currency(self):
        with self.assertRaises(ValueError):
            self.portfolio.add_currency("BTC")

    def test_get_wallet(self):
        wallet = self.portfolio.get_wallet("BTC")

        self.assertIsInstance(wallet, Wallet)
        self.assertEqual(wallet.currency_code, "BTC")
        self.assertEqual(wallet.balance, 0.05)

    def test_get_missing_wallet(self):
        with self.assertRaises(ValueError):
            self.portfolio.get_wallet("RUB")

    def test_wallets_returns_copy(self):
        wallets_copy = self.portfolio.wallets
        wallets_copy.pop("BTC")

        self.assertIn("BTC", self.portfolio.wallets)

    def test_wallet_objects_are_shared(self):
        wallet = self.portfolio.get_wallet("USD")
        wallet.deposit(500.0)

        self.assertEqual(self.portfolio.wallets["USD"].balance, 1500.0)

    def test_user_property(self):
        user = User(
            user_id=1,
            username="alice",
            hashed_password="test_hash",
            salt="test_salt",
            registration_date=datetime.now(),
        )

        portfolio = Portfolio(user_id=1, user=user)

        self.assertIs(portfolio.user, user)

        with self.assertRaises(AttributeError):
            portfolio.user = None

    def test_user_id_mismatch(self):
        user = User(
            user_id=2,
            username="bob",
            hashed_password="test_hash",
            salt="test_salt",
            registration_date=datetime.now(),
        )

        with self.assertRaises(ValueError):
            Portfolio(user_id=1, user=user)

    def test_total_value_usd(self):
        self.assertAlmostEqual(
            self.portfolio.get_total_value(),
            5322.0,
        )

    def test_total_value_eur(self):
        self.assertAlmostEqual(
            self.portfolio.get_total_value("EUR"),
            5322.0 / 1.11,
        )

    def test_total_value_custom_rates(self):
        rates = {
            "BTC_USD": 80000.0,
            "EUR_USD": 1.2,
        }

        self.assertAlmostEqual(
            self.portfolio.get_total_value(rates=rates),
            5240.0,
        )

    def test_missing_rate(self):
        with self.assertRaises(ValueError):
            self.portfolio.get_total_value(rates={})

    def test_invalid_base_currency(self):
        with self.assertRaises(ValueError):
            self.portfolio.get_total_value(base_currency="")

    def test_zero_balance_without_rate(self):
        portfolio = Portfolio(user_id=1)
        portfolio.add_currency("UNKNOWN")

        self.assertEqual(
            portfolio.get_total_value(),
            0.0,
        )

    def test_invalid_rate(self):
        rates = {
            "BTC_USD": -100.0,
            "EUR_USD": 1.1,
        }

        with self.assertRaises(ValueError):
            self.portfolio.get_total_value(rates=rates)

    def test_wallets_validation(self):
        with self.assertRaises(TypeError):
            Portfolio(user_id=1, wallets={"USD": 1000.0})

    def test_wallet_currency_mismatch(self):
        with self.assertRaises(ValueError):
            Portfolio(
                user_id=1,
                wallets={"USD": Wallet("BTC")},
            )
