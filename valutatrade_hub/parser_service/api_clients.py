import math
from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


def validate_rate(rate: object, currency: str) -> float:
    """Проверяет, что курс является положительным конечным числом."""
    if (
        isinstance(rate, bool)
        or not isinstance(rate, (int, float))
        or not math.isfinite(rate)
        or rate <= 0
    ):
        raise ApiRequestError(f"Некорректный курс валюты {currency}")

    return float(rate)


class BaseApiClient(ABC):
    """Общий интерфейс получения валютных курсов."""

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        pass


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko для получения курсов криптовалют."""

    def __init__(self, config: ParserConfig | None = None):
        self.config = config or ParserConfig()

    def fetch_rates(self) -> dict[str, float]:
        base = self.config.BASE_FIAT_CURRENCY.upper()

        ids = [
            self.config.CRYPTO_ID_MAP[code] for code in self.config.CRYPTO_CURRENCIES
        ]

        params = {
            "ids": ",".join(ids),
            "vs_currencies": base.lower(),
        }

        try:
            response = requests.get(
                self.config.COINGECKO_URL,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT,
            )

            response.raise_for_status()
            data = response.json()

        except requests.exceptions.RequestException as error:
            raise ApiRequestError(
                f"Ошибка при обращении к CoinGecko: {type(error).__name__}"
            ) from error

        except ValueError as error:
            raise ApiRequestError("CoinGecko вернул некорректный JSON") from error

        if not isinstance(data, dict):
            raise ApiRequestError("Некорректная структура ответа CoinGecko")

        rates = {}

        for code in self.config.CRYPTO_CURRENCIES:
            coin_id = self.config.CRYPTO_ID_MAP[code]
            coin_data = data.get(coin_id)

            if not isinstance(coin_data, dict):
                raise ApiRequestError(f"CoinGecko не вернул данные для {code}")

            rate = validate_rate(
                coin_data.get(base.lower()),
                code,
            )

            rates[f"{code}_{base}"] = rate

        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API для получения фиатных курсов."""

    def __init__(self, config: ParserConfig | None = None):
        self.config = config or ParserConfig()

    def fetch_rates(self) -> dict[str, float]:
        api_key = self.config.EXCHANGERATE_API_KEY

        if not api_key:
            raise ApiRequestError(
                "Не указан EXCHANGERATE_API_KEY в переменных окружения"
            )

        base = self.config.BASE_FIAT_CURRENCY.upper()

        url = f"{self.config.EXCHANGERATE_API_URL.rstrip('/')}/{api_key}/latest/{base}"

        try:
            response = requests.get(
                url,
                timeout=self.config.REQUEST_TIMEOUT,
            )

            response.raise_for_status()
            data = response.json()

        except requests.exceptions.RequestException as error:
            raise ApiRequestError(
                f"Ошибка при обращении к ExchangeRate-API: {type(error).__name__}"
            ) from error

        except ValueError as error:
            raise ApiRequestError(
                "ExchangeRate-API вернул некорректный JSON"
            ) from error

        if not isinstance(data, dict):
            raise ApiRequestError("Некорректная структура ответа ExchangeRate-API")

        if data.get("result") != "success":
            error_type = data.get("error-type", "неизвестная ошибка")

            raise ApiRequestError(f"ExchangeRate-API: {error_type}")

        if data.get("base_code") != base:
            raise ApiRequestError("ExchangeRate-API вернул неверную базовую валюту")

        conversion_rates = data.get("conversion_rates")

        if conversion_rates is None:
            conversion_rates = data.get("rates")

        if not isinstance(conversion_rates, dict):
            raise ApiRequestError("В ответе ExchangeRate-API отсутствуют курсы")

        rates = {}

        for code in self.config.FIAT_CURRENCIES:
            direct_rate = validate_rate(
                conversion_rates.get(code),
                code,
            )

            # API возвращает USD→EUR, а нам нужен EUR→USD.
            rates[f"{code}_{base}"] = 1.0 / direct_rate

        return rates
