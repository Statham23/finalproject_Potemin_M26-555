import unittest
from io import StringIO
from unittest.mock import Mock, patch

from valutatrade_hub.cli.interface import (
    handle_buy,
    handle_login,
    handle_register,
    handle_sell,
    handle_show_portfolio,
)
from valutatrade_hub.core.exceptions import (
    CurrencyNotFoundError,
    InsufficientFundsError,
)


class TestRegisterCLI(unittest.TestCase):
    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.register_user")
    def test_successful_register(self, mock_register, mock_stdout):
        mock_user = Mock()
        mock_user.username = "alice"
        mock_user.user_id = 1
        mock_register.return_value = mock_user

        handle_register(["--username", "alice", "--password", "1234"])

        mock_register.assert_called_once_with("alice", "1234")
        self.assertIn("зарегистрирован", mock_stdout.getvalue())
        self.assertNotIn("1234", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.register_user")
    def test_duplicate_username(self, mock_register, mock_stdout):
        mock_register.side_effect = ValueError("Имя пользователя 'alice' уже занято")

        handle_register(["--username", "alice", "--password", "1234"])

        self.assertIn("уже занято", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.register_user")
    def test_invalid_arguments(self, mock_register, mock_stdout):
        handle_register(["--username", "alice"])

        mock_register.assert_not_called()
        self.assertIn("Использование:", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.register_user")
    def test_short_password(self, mock_register, mock_stdout):
        mock_register.side_effect = ValueError(
            "Пароль должен быть не короче 4 символов"
        )

        handle_register(["--username", "alice", "--password", "123"])

        self.assertIn("Пароль должен быть не короче", mock_stdout.getvalue())


class TestLoginCLI(unittest.TestCase):
    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.login_user")
    def test_successful_login(self, mock_login, mock_stdout):
        mock_user = Mock()
        mock_user.username = "alice"
        mock_login.return_value = mock_user

        result = handle_login(["--username", "alice", "--password", "1234"])

        mock_login.assert_called_once_with("alice", "1234")
        self.assertIs(result, mock_user)
        self.assertIn("Вы вошли как 'alice'", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.login_user")
    def test_wrong_password(self, mock_login, mock_stdout):
        mock_login.side_effect = ValueError("Неверный пароль")

        result = handle_login(["--username", "alice", "--password", "wrong"])

        self.assertIsNone(result)
        self.assertIn("Неверный пароль", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.login_user")
    def test_invalid_arguments(self, mock_login, mock_stdout):
        result = handle_login(["--username", "alice"])

        self.assertIsNone(result)
        mock_login.assert_not_called()
        self.assertIn("Использование:", mock_stdout.getvalue())


class TestShowPortfolioCLI(unittest.TestCase):
    def setUp(self):
        self.user = Mock()
        self.user.user_id = 1
        self.user.username = "alice"

        self.portfolio_result = {
            "base_currency": "USD",
            "wallets": [
                {
                    "currency_code": "USD",
                    "balance": 150.0,
                    "value": 150.0,
                },
                {
                    "currency_code": "BTC",
                    "balance": 0.05,
                    "value": 2966.8605,
                },
                {
                    "currency_code": "EUR",
                    "balance": 200.0,
                    "value": 215.72,
                },
            ],
            "total": 3332.5805,
        }

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.show_portfolio")
    def test_successful_display(self, mock_show, mock_stdout):
        mock_show.return_value = self.portfolio_result

        handle_show_portfolio([], self.user)

        mock_show.assert_called_once_with(
            user_id=1,
            base_currency="USD",
        )

        output = mock_stdout.getvalue()

        self.assertIn("Портфель пользователя 'alice'", output)
        self.assertIn("BTC: 0.0500", output)
        self.assertIn("2,966.86 USD", output)
        self.assertIn("ИТОГО: 3,332.58 USD", output)

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.show_portfolio")
    def test_not_logged_in(self, mock_show, mock_stdout):
        handle_show_portfolio([], None)

        mock_show.assert_not_called()
        self.assertIn("Сначала выполните login", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.show_portfolio")
    def test_custom_base(self, mock_show, mock_stdout):
        mock_show.return_value = {
            "base_currency": "EUR",
            "wallets": [],
            "total": 0.0,
        }

        handle_show_portfolio(["--base", "EUR"], self.user)

        mock_show.assert_called_once_with(
            user_id=1,
            base_currency="EUR",
        )
        self.assertIn("база: EUR", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.show_portfolio")
    def test_unknown_currency(self, mock_show, mock_stdout):
        mock_show.side_effect = ValueError("Неизвестная базовая валюта 'ABC'")

        handle_show_portfolio(["--base", "ABC"], self.user)

        self.assertIn(
            "Неизвестная базовая валюта 'ABC'",
            mock_stdout.getvalue(),
        )

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.show_portfolio")
    def test_invalid_arguments(self, mock_show, mock_stdout):
        handle_show_portfolio(["--base"], self.user)

        mock_show.assert_not_called()
        self.assertIn("Использование:", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.show_portfolio")
    def test_empty_portfolio(self, mock_show, mock_stdout):
        mock_show.return_value = {
            "base_currency": "USD",
            "wallets": [],
            "total": 0.0,
        }

        handle_show_portfolio([], self.user)

        self.assertIn("Портфель пуст", mock_stdout.getvalue())


class TestBuyCLI(unittest.TestCase):
    def setUp(self):
        self.user = Mock()
        self.user.user_id = 1
        self.user.username = "alice"

        self.buy_result = {
            "currency_code": "BTC",
            "amount": 0.05,
            "rate": 59337.21,
            "old_balance": 0.07,
            "new_balance": 0.12,
            "estimated_cost": 2966.8605,
        }

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.buy")
    def test_successful_buy(self, mock_buy, mock_stdout):
        mock_buy.return_value = self.buy_result

        handle_buy(
            ["--currency", "BTC", "--amount", "0.05"],
            self.user,
        )

        mock_buy.assert_called_once_with(
            user_id=1,
            currency_code="BTC",
            amount=0.05,
        )

        output = mock_stdout.getvalue()
        self.assertIn("Покупка выполнена", output)
        self.assertIn("0.0500 BTC", output)
        self.assertIn("было 0.0700 → стало 0.1200", output)
        self.assertIn("2,966.86 USD", output)

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.buy")
    def test_not_logged_in(self, mock_buy, mock_stdout):
        handle_buy(
            ["--currency", "BTC", "--amount", "0.05"],
            None,
        )

        mock_buy.assert_not_called()
        self.assertIn("Сначала выполните login", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.buy")
    def test_invalid_arguments(self, mock_buy, mock_stdout):
        handle_buy(["--currency", "BTC"], self.user)

        mock_buy.assert_not_called()
        self.assertIn("Использование:", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.buy")
    def test_invalid_amount_string(self, mock_buy, mock_stdout):
        handle_buy(
            ["--currency", "BTC", "--amount", "abc"],
            self.user,
        )

        mock_buy.assert_not_called()
        self.assertIn(
            "'amount' должен быть положительным числом",
            mock_stdout.getvalue(),
        )

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.buy")
    def test_non_positive_amount(self, mock_buy, mock_stdout):
        mock_buy.side_effect = ValueError("'amount' должен быть положительным числом")

        handle_buy(
            ["--currency", "BTC", "--amount", "-1"],
            self.user,
        )

        mock_buy.assert_called_once_with(
            user_id=1,
            currency_code="BTC",
            amount=-1.0,
        )
        self.assertIn(
            "'amount' должен быть положительным числом",
            mock_stdout.getvalue(),
        )

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.buy")
    def test_unknown_currency(self, mock_buy, mock_stdout):
        mock_buy.side_effect = CurrencyNotFoundError("Неизвестная валюта 'ABC'")

        handle_buy(
            ["--currency", "ABC", "--amount", "1"],
            self.user,
        )

        self.assertIn(
            "Неизвестная валюта 'ABC'",
            mock_stdout.getvalue(),
        )

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.buy")
    def test_missing_rate(self, mock_buy, mock_stdout):
        mock_buy.side_effect = ValueError("Не удалось получить курс для BTC→USD")

        handle_buy(
            ["--currency", "BTC", "--amount", "0.05"],
            self.user,
        )

        self.assertIn(
            "Не удалось получить курс для BTC→USD",
            mock_stdout.getvalue(),
        )


class TestSellCLI(unittest.TestCase):
    def setUp(self):
        self.user = Mock()
        self.user.user_id = 1
        self.user.username = "alice"

        self.sell_result = {
            "currency_code": "BTC",
            "amount": 0.01,
            "rate": 59337.21,
            "old_balance": 0.05,
            "new_balance": 0.04,
            "estimated_revenue": 593.3721,
        }

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.sell")
    def test_successful_sell(self, mock_sell, mock_stdout):
        mock_sell.return_value = self.sell_result

        handle_sell(
            ["--currency", "BTC", "--amount", "0.01"],
            self.user,
        )

        mock_sell.assert_called_once_with(
            user_id=1,
            currency_code="BTC",
            amount=0.01,
        )

        output = mock_stdout.getvalue()
        self.assertIn("Продажа выполнена", output)
        self.assertIn("0.0100 BTC", output)
        self.assertIn("было 0.0500 → стало 0.0400", output)
        self.assertIn("593.37 USD", output)

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.sell")
    def test_not_logged_in(self, mock_sell, mock_stdout):
        handle_sell(
            ["--currency", "BTC", "--amount", "0.01"],
            None,
        )

        mock_sell.assert_not_called()
        self.assertIn("Сначала выполните login", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.sell")
    def test_invalid_arguments(self, mock_sell, mock_stdout):
        handle_sell(["--currency", "BTC"], self.user)

        mock_sell.assert_not_called()
        self.assertIn("Использование:", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.sell")
    def test_invalid_amount_string(self, mock_sell, mock_stdout):
        handle_sell(
            ["--currency", "BTC", "--amount", "abc"],
            self.user,
        )

        mock_sell.assert_not_called()
        self.assertIn(
            "'amount' должен быть положительным числом",
            mock_stdout.getvalue(),
        )

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.sell")
    def test_insufficient_funds(self, mock_sell, mock_stdout):
        mock_sell.side_effect = InsufficientFundsError(
            "Недостаточно средств: доступно 0.0400 BTC, требуется 0.0500 BTC"
        )

        handle_sell(
            ["--currency", "BTC", "--amount", "0.05"],
            self.user,
        )

        self.assertIn(
            "Недостаточно средств: доступно 0.0400 BTC",
            mock_stdout.getvalue(),
        )

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.sell")
    def test_missing_wallet(self, mock_sell, mock_stdout):
        mock_sell.side_effect = ValueError("У вас нет кошелька 'ETH'.")

        handle_sell(
            ["--currency", "ETH", "--amount", "1"],
            self.user,
        )

        self.assertIn(
            "У вас нет кошелька 'ETH'",
            mock_stdout.getvalue(),
        )

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.sell")
    def test_unknown_currency(self, mock_sell, mock_stdout):
        mock_sell.side_effect = CurrencyNotFoundError("Неизвестная валюта 'ABC'")

        handle_sell(
            ["--currency", "ABC", "--amount", "1"],
            self.user,
        )

        self.assertIn(
            "Неизвестная валюта 'ABC'",
            mock_stdout.getvalue(),
        )

    @patch("sys.stdout", new_callable=StringIO)
    @patch("valutatrade_hub.cli.interface.sell")
    def test_missing_rate(self, mock_sell, mock_stdout):
        mock_sell.side_effect = ValueError("Не удалось получить курс для BTC→USD")

        handle_sell(
            ["--currency", "BTC", "--amount", "0.01"],
            self.user,
        )

        self.assertIn(
            "Не удалось получить курс для BTC→USD",
            mock_stdout.getvalue(),
        )
