import unittest
from datetime import datetime

from valutatrade_hub.core.models import User


class TestUser(unittest.TestCase):
    def setUp(self):
        self.user = User(
            user_id=1,
            username="alice",
            hashed_password="test_hash",
            salt="x5T9!",
            registration_date=datetime(2025, 10, 9, 12, 0),
        )

    def test_get_user_info(self):
        info = self.user.get_user_info()

        self.assertEqual(info["user_id"], 1)
        self.assertEqual(info["username"], "alice")
        self.assertEqual(info["registration_date"], "2025-10-09T12:00:00")
        self.assertNotIn("hashed_password", info)
        self.assertNotIn("salt", info)

    def test_change_password(self):
        self.user.change_password("qwerty123")

        self.assertEqual(len(self.user.hashed_password), 64)
        self.assertNotEqual(self.user.hashed_password, "qwerty123")

    def test_verify_password(self):
        self.user.change_password("qwerty123")

        self.assertTrue(self.user.verify_password("qwerty123"))
        self.assertFalse(self.user.verify_password("wrongpass"))

    def test_password_change_invalidates_old_password(self):
        self.user.change_password("oldpassword")
        self.user.change_password("newpassword")

        self.assertFalse(self.user.verify_password("oldpassword"))
        self.assertTrue(self.user.verify_password("newpassword"))

    def test_short_password(self):
        with self.assertRaises(ValueError):
            self.user.change_password("123")

    def test_empty_username(self):
        with self.assertRaises(ValueError):
            self.user.username = "   "

    def test_change_username(self):
        self.user.username = "bob"

        self.assertEqual(self.user.username, "bob")

    def test_invalid_user_id(self):
        with self.assertRaises(ValueError):
            User(
                user_id=-1,
                username="alice",
                hashed_password="test_hash",
                salt="x5T9!",
                registration_date=datetime.now(),
            )

    def test_user_id_read_only(self):
        with self.assertRaises(AttributeError):
            self.user.user_id = 10
