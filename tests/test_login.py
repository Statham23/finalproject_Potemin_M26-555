import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from valutatrade_hub.core import utils
from valutatrade_hub.core.models import User
from valutatrade_hub.core.usecases import login_user, register_user


class TestLogin(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.data_dir = Path(self.temp_dir.name)

        self.path_patcher = patch.object(utils, "DATA_DIR", self.data_dir)
        self.path_patcher.start()
        self.addCleanup(self.path_patcher.stop)

        utils.save_json("users.json", [])
        utils.save_json("portfolios.json", [])

        self.registered_user = register_user("alice", "1234")

    def test_successful_login(self):
        user = login_user("alice", "1234")

        self.assertEqual(user.username, "alice")
        self.assertEqual(user.user_id, self.registered_user.user_id)

    def test_wrong_password(self):
        with self.assertRaisesRegex(ValueError, "Неверный пароль"):
            login_user("alice", "wrong")

    def test_unknown_user(self):
        with self.assertRaisesRegex(ValueError, "не найден"):
            login_user("unknown", "1234")

    def test_login_returns_user_object(self):
        user = login_user("alice", "1234")

        self.assertIsInstance(user, User)
        self.assertTrue(user.verify_password("1234"))

    def test_login_does_not_modify_users(self):
        users_before = utils.load_json("users.json")

        login_user("alice", "1234")

        users_after = utils.load_json("users.json")
        self.assertEqual(users_before, users_after)
