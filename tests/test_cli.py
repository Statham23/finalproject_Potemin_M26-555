import unittest
from io import StringIO
from unittest.mock import Mock, patch

from valutatrade_hub.cli.interface import handle_register


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
