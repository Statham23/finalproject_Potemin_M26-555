import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from valutatrade_hub.core import utils
from valutatrade_hub.core.usecases import register_user


class TestRegister(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.data_dir = Path(self.temp_dir.name)

        self.path_patcher = patch.object(utils, "DATA_DIR", self.data_dir)
        self.path_patcher.start()
        self.addCleanup(self.path_patcher.stop)

        utils.save_json("users.json", [])
        utils.save_json("portfolios.json", [])

    def test_successful_registration(self):
        user = register_user("alice", "1234")

        self.assertEqual(user.user_id, 1)
        self.assertEqual(user.username, "alice")
        self.assertTrue(user.verify_password("1234"))

        users = utils.load_json("users.json")
        portfolios = utils.load_json("portfolios.json")

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["username"], "alice")
        self.assertNotEqual(users[0]["hashed_password"], "1234")
        self.assertIn("salt", users[0])

        self.assertEqual(
            portfolios,
            [{"user_id": 1, "wallets": {}}],
        )

    def test_duplicate_username(self):
        register_user("alice", "1234")

        with self.assertRaisesRegex(ValueError, "уже занято"):
            register_user("alice", "5678")

        self.assertEqual(len(utils.load_json("users.json")), 1)
        self.assertEqual(len(utils.load_json("portfolios.json")), 1)

    def test_short_password(self):
        with self.assertRaises(ValueError):
            register_user("alice", "123")

        self.assertEqual(utils.load_json("users.json"), [])

    def test_empty_username(self):
        with self.assertRaises(ValueError):
            register_user("   ", "1234")

        self.assertEqual(utils.load_json("users.json"), [])

    def test_auto_increment_user_id(self):
        first = register_user("alice", "1234")
        second = register_user("bob", "5678")

        self.assertEqual(first.user_id, 1)
        self.assertEqual(second.user_id, 2)

    def test_unique_salt(self):
        first = register_user("alice", "1234")
        second = register_user("bob", "1234")

        self.assertNotEqual(first.salt, second.salt)
        self.assertNotEqual(first.hashed_password, second.hashed_password)
