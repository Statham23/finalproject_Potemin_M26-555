import hashlib
import hmac
import math
from datetime import datetime

EXCHANGE_RATES = {
    "USD_USD": 1.0,
    "EUR_USD": 1.11,
    "BTC_USD": 82000.0,
    "ETH_USD": 2500.0,
    "RUB_USD": 0.012,
}


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


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        self.currency_code = currency_code
        self.balance = balance

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, new_balance: float) -> None:
        if isinstance(new_balance, bool) or not isinstance(new_balance, (int, float)):
            raise TypeError("Баланс должен быть числом")

        if not math.isfinite(new_balance):
            raise ValueError("Баланс должен быть конечным числом")

        if new_balance < 0:
            raise ValueError("Баланс не может быть отрицательным")

        self._balance = float(new_balance)

    def deposit(self, amount: float) -> None:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Сумма пополнения должна быть числом")

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError(
                "Сумма пополнения должна быть положительным конечным числом"
            )

        self._balance += amount

    def withdraw(self, amount: float) -> None:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Сумма снятия должна быть числом")

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Сумма снятия должна быть положительным конечным числом")

        if amount > self._balance:
            raise ValueError("Недостаточно средств на балансе")

        self._balance -= amount

    def get_balance_info(self) -> dict:
        return {
            "currency_code": self.currency_code,
            "balance": self._balance,
        }


class Portfolio:
    def __init__(
        self,
        user_id: int,
        wallets: dict[str, Wallet] | None = None,
        user: User | None = None,
    ) -> None:
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("ID пользователя должен быть положительным целым числом")

        if user is not None:
            if not isinstance(user, User):
                raise TypeError("user должен быть объектом User")

            if user.user_id != user_id:
                raise ValueError("ID пользователя не совпадает с владельцем портфеля")

        if wallets is not None:
            if not isinstance(wallets, dict):
                raise TypeError("wallets должен быть словарём")

            for currency_code, wallet in wallets.items():
                if not isinstance(wallet, Wallet):
                    raise TypeError("Все значения wallets должны быть объектами Wallet")

                if currency_code != wallet.currency_code:
                    raise ValueError("Код валюты не совпадает с кодом кошелька")

        self._user_id = user_id
        self._user = user
        self._wallets = wallets.copy() if wallets is not None else {}

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def user(self) -> User | None:
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> None:
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        if currency_code in self._wallets:
            raise ValueError(f"Кошелёк {currency_code} уже существует")

        self._wallets[currency_code] = Wallet(currency_code)

    def get_wallet(self, currency_code: str) -> Wallet:
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        if currency_code not in self._wallets:
            raise ValueError(f"Кошелёк {currency_code} не найден")

        return self._wallets[currency_code]

    def get_total_value(
        self,
        base_currency: str = "USD",
        rates: dict[str, float] | None = None,
    ) -> float:
        if not isinstance(base_currency, str) or not base_currency.strip():
            raise ValueError("Код базовой валюты не может быть пустым")

        if rates is None:
            rates = EXCHANGE_RATES

        base_currency = base_currency.upper()

        base_rate = 1.0 if base_currency == "USD" else rates.get(f"{base_currency}_USD")

        if base_rate is None:
            raise ValueError(f"Не найден курс для базовой валюты {base_currency}")

        if isinstance(base_rate, bool) or not isinstance(base_rate, (int, float)):
            raise ValueError("Некорректный курс базовой валюты")

        if not math.isfinite(base_rate) or base_rate <= 0:
            raise ValueError("Курс базовой валюты должен быть положительным")

        total_usd = 0.0

        for currency_code, wallet in self._wallets.items():
            if wallet.balance == 0:
                continue

            rate = 1.0 if currency_code == "USD" else rates.get(f"{currency_code}_USD")

            if rate is None:
                raise ValueError(f"Не найден курс для валюты {currency_code}")

            if isinstance(rate, bool) or not isinstance(rate, (int, float)):
                raise ValueError(f"Некорректный курс валюты {currency_code}")

            if not math.isfinite(rate) or rate <= 0:
                raise ValueError(
                    f"Курс валюты {currency_code} должен быть положительным"
                )

            total_usd += wallet.balance * rate

        return total_usd / base_rate
