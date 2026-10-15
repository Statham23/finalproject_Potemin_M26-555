import math
import secrets
from datetime import datetime, timedelta, timezone

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
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


def sell(user_id: int, currency_code: str, amount: float) -> dict:
    if (
        isinstance(amount, bool)
        or not isinstance(amount, (int, float))
        or not math.isfinite(amount)
        or amount <= 0
    ):
        raise ValueError("'amount' должен быть положительным числом")

    get_currency(currency_code)

    portfolio = get_user_portfolio(user_id)

    if currency_code not in portfolio.wallets:
        raise ValueError(
            f"У вас нет кошелька '{currency_code}'. "
            "Добавьте валюту: она создаётся автоматически "
            "при первой покупке."
        )

    wallet = portfolio.get_wallet(currency_code)
    old_balance = wallet.balance

    if old_balance < amount:
        raise InsufficientFundsError(
            f"Недостаточно средств: доступно {old_balance:.4f} "
            f"{currency_code}, требуется {amount:.4f} {currency_code}"
        )

    rates = get_exchange_rates()
    pair = f"{currency_code}_USD"

    if pair not in rates:
        raise ValueError(f"Не удалось получить курс для {currency_code}→USD")

    rate = rates[pair]
    estimated_revenue = amount * rate

    wallet.withdraw(amount)

    save_user_portfolio(portfolio)

    return {
        "currency_code": currency_code,
        "amount": amount,
        "rate": rate,
        "old_balance": old_balance,
        "new_balance": wallet.balance,
        "estimated_revenue": estimated_revenue,
    }


def is_rate_fresh(updated_at: str, max_age_minutes: int = 5) -> bool:
    updated_time = datetime.fromisoformat(updated_at)
    current_time = datetime.now(updated_time.tzinfo)

    age = current_time - updated_time

    return timedelta(0) <= age < timedelta(minutes=max_age_minutes)


def get_cached_rate(from_currency: str, to_currency: str) -> dict | None:
    get_currency(from_currency)
    get_currency(to_currency)

    if from_currency == to_currency:
        return {
            "rate": 1.0,
            "updated_at": None,
        }

    rates_data = load_json("rates.json")

    direct_pair = f"{from_currency}_{to_currency}"
    reverse_pair = f"{to_currency}_{from_currency}"

    if direct_pair in rates_data:
        rate_data = rates_data[direct_pair]

        rate = rate_data["rate"]

        if (
            isinstance(rate, bool)
            or not isinstance(rate, (int, float))
            or not math.isfinite(rate)
            or rate <= 0
        ):
            raise ValueError(f"Некорректный курс для '{direct_pair}'")

        return {
            "rate": float(rate),
            "updated_at": rate_data["updated_at"],
        }

    if reverse_pair in rates_data:
        rate_data = rates_data[reverse_pair]

        rate = rate_data["rate"]

        if (
            isinstance(rate, bool)
            or not isinstance(rate, (int, float))
            or not math.isfinite(rate)
            or rate <= 0
        ):
            raise ValueError(f"Некорректный курс для '{reverse_pair}'")

        return {
            "rate": 1.0 / rate,
            "updated_at": rate_data["updated_at"],
        }

    return None


MOCK_RATES = {
    "BTC_USD": 59337.21,
    "ETH_USD": 3720.0,
    "EUR_USD": 1.0786,
    "RUB_USD": 0.01016,
}


def fetch_rate_from_parser(from_currency: str, to_currency: str) -> float:
    direct_pair = f"{from_currency}_{to_currency}"
    reverse_pair = f"{to_currency}_{from_currency}"

    if direct_pair in MOCK_RATES:
        return MOCK_RATES[direct_pair]

    if reverse_pair in MOCK_RATES:
        return 1.0 / MOCK_RATES[reverse_pair]

    raise ApiRequestError(f"Курс {from_currency}→{to_currency} недоступен")


def update_cached_rate(from_currency: str, to_currency: str) -> dict:
    get_currency(from_currency)
    get_currency(to_currency)

    if from_currency == to_currency:
        return {
            "rate": 1.0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    rate = fetch_rate_from_parser(from_currency, to_currency)

    if (
        isinstance(rate, bool)
        or not isinstance(rate, (int, float))
        or not math.isfinite(rate)
        or rate <= 0
    ):
        raise ApiRequestError(f"Некорректный курс {from_currency}→{to_currency}")

    rates_data = load_json("rates.json")

    updated_at = datetime.now(timezone.utc).isoformat()
    pair = f"{from_currency}_{to_currency}"

    rates_data[pair] = {
        "rate": float(rate),
        "updated_at": updated_at,
    }

    rates_data["source"] = "MockParserService"
    rates_data["last_refresh"] = updated_at

    save_json("rates.json", rates_data)

    return {
        "rate": float(rate),
        "updated_at": updated_at,
    }


def get_rate(from_currency: str, to_currency: str) -> dict:
    get_currency(from_currency)
    get_currency(to_currency)

    cached = get_cached_rate(from_currency, to_currency)

    if cached is not None and (
        cached["updated_at"] is None or is_rate_fresh(cached["updated_at"])
    ):
        rate_data = cached
    else:
        rate_data = update_cached_rate(from_currency, to_currency)

    rate = rate_data["rate"]

    return {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "rate": rate,
        "reverse_rate": 1.0 / rate,
        "updated_at": rate_data["updated_at"],
    }
