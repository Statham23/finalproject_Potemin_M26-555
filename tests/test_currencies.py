import unittest

from valutatrade_hub.core.currencies import (
    CryptoCurrency,
    Currency,
    FiatCurrency,
    get_currency,
)
from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class TestCurrency(unittest.TestCase):
    def test_abstract_class(self):
        with self.assertRaises(TypeError):
            Currency("US Dollar", "USD")

    def test_invalid_name(self):
        with self.assertRaises(ValueError):
            FiatCurrency("", "USD", "United States")

    def test_invalid_code(self):
        for code in ["usd", "A", "ABCDEF", "US D"]:
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    FiatCurrency("US Dollar", code, "United States")


class TestFiatCurrency(unittest.TestCase):
    def test_attributes(self):
        usd = FiatCurrency("US Dollar", "USD", "United States")

        self.assertEqual(usd.name, "US Dollar")
        self.assertEqual(usd.code, "USD")
        self.assertEqual(usd.issuing_country, "United States")

    def test_display_info(self):
        usd = FiatCurrency("US Dollar", "USD", "United States")

        self.assertEqual(
            usd.get_display_info(),
            "[FIAT] USD — US Dollar (Issuing: United States)",
        )

    def test_invalid_country(self):
        with self.assertRaises(ValueError):
            FiatCurrency("US Dollar", "USD", "")


class TestCryptoCurrency(unittest.TestCase):
    def test_attributes(self):
        btc = CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12)

        self.assertEqual(btc.name, "Bitcoin")
        self.assertEqual(btc.code, "BTC")
        self.assertEqual(btc.algorithm, "SHA-256")
        self.assertEqual(btc.market_cap, 1.12e12)

    def test_display_info(self):
        btc = CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12)

        self.assertEqual(
            btc.get_display_info(),
            "[CRYPTO] BTC — Bitcoin (Algo: SHA-256, MCAP: 1.12e12)",
        )

    def test_invalid_algorithm(self):
        with self.assertRaises(ValueError):
            CryptoCurrency("Bitcoin", "BTC", "", 1.12e12)

    def test_invalid_market_cap(self):
        for market_cap in [-100, float("nan"), float("inf"), True]:
            with self.subTest(market_cap=market_cap):
                with self.assertRaises(ValueError):
                    CryptoCurrency("Bitcoin", "BTC", "SHA-256", market_cap)


class TestCurrencyRegistry(unittest.TestCase):
    def test_supported_currencies(self):
        for code in ["USD", "EUR", "RUB", "BTC", "ETH"]:
            with self.subTest(code=code):
                currency = get_currency(code)

                self.assertIsInstance(currency, Currency)
                self.assertEqual(currency.code, code)

    def test_fiat_and_crypto_types(self):
        self.assertIsInstance(get_currency("USD"), FiatCurrency)
        self.assertIsInstance(get_currency("BTC"), CryptoCurrency)

    def test_unknown_currency(self):
        with self.assertRaises(CurrencyNotFoundError):
            get_currency("ABC")

    def test_lowercase_currency(self):
        with self.assertRaises(CurrencyNotFoundError):
            get_currency("usd")
