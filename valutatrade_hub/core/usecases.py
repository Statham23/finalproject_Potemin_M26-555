import secrets
from datetime import datetime

from valutatrade_hub.core.models import User
from valutatrade_hub.core.utils import load_json, save_json


def register_user(username: str, password: str) -> User:
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")

    if not isinstance(password, str) or len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users = load_json("users.json")

    for user_data in users:
        if user_data["username"] == username:
            raise ValueError(f"Имя пользователя '{username}' уже занято")

    new_user_id = (
        max(
            (user_data["user_id"] for user_data in users),
            default=0,
        )
        + 1
    )

    salt = secrets.token_hex(16)

    user = User(
        user_id=new_user_id,
        username=username,
        hashed_password="temporary",
        salt=salt,
        registration_date=datetime.now(),
    )

    user.change_password(password)

    users.append(
        {
            "user_id": user.user_id,
            "username": user.username,
            "hashed_password": user.hashed_password,
            "salt": user.salt,
            "registration_date": user.registration_date.isoformat(),
        }
    )

    portfolios = load_json("portfolios.json")
    portfolios.append(
        {
            "user_id": user.user_id,
            "wallets": {},
        }
    )

    save_json("users.json", users)
    save_json("portfolios.json", portfolios)

    return user
