import math
import secrets
from datetime import datetime

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.core.models import Portfolio, User, Wallet
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


def login_user(username: str, password: str) -> User:
    users = load_json("users.json")

    for user_data in users:
        if user_data["username"] == username:
            user = User(
                user_id=user_data["user_id"],
                username=user_data["username"],
                hashed_password=user_data["hashed_password"],
                salt=user_data["salt"],
                registration_date=datetime.fromisoformat(
                    user_data["registration_date"]
                ),
            )

            if not user.verify_password(password):
                raise ValueError("Неверный пароль")

            return user

    raise ValueError(f"Пользователь '{username}' не найден")


def get_user_portfolio(user_id: int) -> Portfolio:
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("ID пользователя должен быть положительным целым числом")

    portfolios = load_json("portfolios.json")

    for portfolio_data in portfolios:
        if portfolio_data["user_id"] == user_id:
            wallets = {}

            for currency_code, wallet_data in portfolio_data["wallets"].items():
                wallets[currency_code] = Wallet(
                    currency_code=currency_code,
                    balance=wallet_data["balance"],
                )

            return Portfolio(
                user_id=user_id,
                wallets=wallets,
            )

    raise ValueError(f"Портфель пользователя с ID {user_id} не найден")


def save_user_portfolio(portfolio: Portfolio) -> None:
    portfolios = load_json("portfolios.json")

    wallets_data = {}

    for currency_code, wallet in portfolio.wallets.items():
        wallets_data[currency_code] = {
            "balance": wallet.balance,
        }

    for portfolio_data in portfolios:
        if portfolio_data["user_id"] == portfolio.user_id:
            portfolio_data["wallets"] = wallets_data
            save_json("portfolios.json", portfolios)
            return

    raise ValueError(f"Портфель пользователя с ID {portfolio.user_id} не найден")


def get_exchange_rates() -> dict[str, float]:
    rates_data = load_json("rates.json")
    rates = {"USD_USD": 1.0}

    for pair, data in rates_data.items():
        if pair in ("source", "last_refresh"):
            continue

        if not isinstance(data, dict) or "rate" not in data:
            raise ValueError(f"Некорректные данные курса '{pair}'")

        rate = data["rate"]

        if (
            isinstance(rate, bool)
            or not isinstance(rate, (int, float))
            or not math.isfinite(rate)
            or rate <= 0
        ):
            raise ValueError(f"Некорректный курс для '{pair}'")

        rates[pair] = float(rate)

    return rates


def show_portfolio(
    user_id: int,
    base_currency: str = "USD",
) -> dict:
    try:
        get_currency(base_currency)
    except CurrencyNotFoundError:
        raise ValueError(f"Неизвестная базовая валюта '{base_currency}'") from None

    portfolio = get_user_portfolio(user_id)

    if not portfolio.wallets:
        return {
            "base_currency": base_currency,
            "wallets": [],
            "total": 0.0,
        }

    rates = get_exchange_rates()
    wallet_info = []

    for code, wallet in portfolio.wallets.items():
        get_currency(code)

        single_wallet = Portfolio(
            user_id=user_id,
            wallets={code: wallet},
        )

        value = single_wallet.get_total_value(
            base_currency=base_currency,
            rates=rates,
        )

        wallet_info.append(
            {
                "currency_code": code,
                "balance": wallet.balance,
                "value": value,
            }
        )

    total = portfolio.get_total_value(
        base_currency=base_currency,
        rates=rates,
    )

    return {
        "base_currency": base_currency,
        "wallets": wallet_info,
        "total": total,
    }


def buy(user_id: int, currency_code: str, amount: float) -> dict:
    if (
        isinstance(amount, bool)
        or not isinstance(amount, (int, float))
        or not math.isfinite(amount)
        or amount <= 0
    ):
        raise ValueError("'amount' должен быть положительным числом")

    get_currency(currency_code)

    rates = get_exchange_rates()
    pair = f"{currency_code}_USD"

    if pair not in rates:
        raise ValueError(f"Не удалось получить курс для {currency_code}→USD")

    rate = rates[pair]
    estimated_cost = amount * rate

    portfolio = get_user_portfolio(user_id)

    if currency_code not in portfolio.wallets:
        portfolio.add_currency(currency_code)

    wallet = portfolio.get_wallet(currency_code)
    old_balance = wallet.balance

    wallet.deposit(amount)

    save_user_portfolio(portfolio)

    return {
        "currency_code": currency_code,
        "amount": amount,
        "rate": rate,
        "old_balance": old_balance,
        "new_balance": wallet.balance,
        "estimated_cost": estimated_cost,
    }
