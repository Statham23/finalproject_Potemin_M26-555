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


def handle_request_error(
    error: requests.exceptions.RequestException,
    service: str,
) -> None:
    """Преобразует сетевую ошибку API в понятную ошибку приложения."""

    if isinstance(error, requests.exceptions.Timeout):
        message = "Превышено время ожидания ответа"

    elif isinstance(error, requests.exceptions.HTTPError):
        status_code = error.response.status_code if error.response is not None else None

        if status_code == 401:
            message = "Ошибка авторизации (HTTP 401). Проверьте API-ключ"
        elif status_code == 403:
            message = "Доступ запрещён (HTTP 403)"
        elif status_code == 429:
            message = "Превышен лимит запросов (HTTP 429)"
        elif status_code is not None:
            message = f"HTTP-ошибка {status_code}"
        else:
            message = "HTTP-ошибка без кода ответа"

    elif isinstance(error, requests.exceptions.ConnectionError):
        message = "Не удалось подключиться к серверу"

    else:
        message = f"Сетевая ошибка: {type(error).__name__}"

    raise ApiRequestError(f"{service}: {message}") from error


class BaseApiClient(ABC):
    """Общий интерфейс получения валютных курсов."""

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Получает валютные курсы и возвращает словарь пар и значений."""
        pass


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko для получения курсов криптовалют."""

    def __init__(self, config: ParserConfig | None = None):
        self.config = config or ParserConfig()

    def fetch_rates(self) -> dict[str, float]:
        """Запрашивает курсы криптовалют к USD через CoinGecko."""
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
            handle_request_error(error, "CoinGecko")

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
        """Запрашивает фиатные курсы через ExchangeRate-API."""
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
            handle_request_error(error, "ExchangeRate-API")

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
