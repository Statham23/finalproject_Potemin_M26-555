import hashlib
import hmac
from datetime import datetime


class User:
    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:

        if type(user_id) is not int or user_id <= 0:
            raise ValueError("ID пользователя должен быть положительным целым числом")

        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым")

        if not isinstance(hashed_password, str) or not hashed_password:
            raise ValueError("Хеш пароля не может быть пустым")

        if not isinstance(salt, str) or not salt:
            raise ValueError("Соль не может быть пустой")

        if not isinstance(registration_date, datetime):
            raise TypeError("Дата регистрации должна быть объектом datetime")

        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, new_username: str) -> None:
        if not isinstance(new_username, str) or not new_username.strip():
            raise ValueError("Имя пользователя не может быть пустым")

        self._username = new_username

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def get_user_info(self) -> dict:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен содержать минимум 4 символа")

        password_with_salt = new_password + self._salt

        self._hashed_password = hashlib.sha256(
            password_with_salt.encode("utf-8")
        ).hexdigest()

    def verify_password(self, password: str) -> bool:
        if not isinstance(password, str):
            return False

        password_with_salt = password + self._salt

        hashed_password = hashlib.sha256(password_with_salt.encode("utf-8")).hexdigest()

        return hmac.compare_digest(hashed_password, self._hashed_password)
