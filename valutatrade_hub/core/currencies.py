import math
from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    def __init__(self, name: str, code: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты не может быть пустым")

        if (
            not isinstance(code, str)
            or not 2 <= len(code) <= 5
            or not code.isascii()
            or not code.isalpha()
            or not code.isupper()
        ):
            raise ValueError(
                "Код валюты должен состоять из 2–5 заглавных латинских букв"
            )

        self.name = name
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        pass


class FiatCurrency(Currency):
    def __init__(
        self,
        name: str,
        code: str,
        issuing_country: str,
    ) -> None:
        super().__init__(name, code)

        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна выпуска не может быть пустой")

        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float,
    ) -> None:
        super().__init__(name, code)

        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")

        if (
            isinstance(market_cap, bool)
            or not isinstance(market_cap, (int, float))
            or not math.isfinite(market_cap)
            or market_cap < 0
        ):
            raise ValueError(
                "Рыночная капитализация должна быть неотрицательным конечным числом"
            )

        self.algorithm = algorithm
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        mcap = f"{self.market_cap:.2e}".replace("e+", "e")
        return (
            f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {mcap})"
        )


CURRENCY_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency(
        name="US Dollar",
        code="USD",
        issuing_country="United States",
    ),
    "EUR": FiatCurrency(
        name="Euro",
        code="EUR",
        issuing_country="Eurozone",
    ),
    "RUB": FiatCurrency(
        name="Russian Ruble",
        code="RUB",
        issuing_country="Russia",
    ),
    "BTC": CryptoCurrency(
        name="Bitcoin",
        code="BTC",
        algorithm="SHA-256",
        market_cap=1_120_000_000_000,
    ),
    "ETH": CryptoCurrency(
        name="Ethereum",
        code="ETH",
        algorithm="Proof of Stake",
        market_cap=300_000_000_000,
    ),
}


def get_currency(code: str) -> Currency:
    if not isinstance(code, str):
        raise CurrencyNotFoundError(f"Неизвестная валюта '{code}'")

    currency = CURRENCY_REGISTRY.get(code)

    if currency is None:
        raise CurrencyNotFoundError(f"Неизвестная валюта '{code}'")

    return currency
