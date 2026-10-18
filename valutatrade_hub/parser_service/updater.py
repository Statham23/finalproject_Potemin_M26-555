from datetime import datetime, timezone

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import setup_parser_logging
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.storage import RatesStorage


class RatesUpdater:
    """Координирует получение и сохранение валютных курсов."""

    def __init__(
        self,
        clients: list[BaseApiClient],
        storage: RatesStorage,
    ):
        if not clients:
            raise ValueError("Не указан ни один API-клиент")

        self.clients = clients
        self.storage = storage
        self.logger = setup_parser_logging()
        self.errors: list[str] = []
        self.updated_count = 0

    @staticmethod
    def get_source(client: BaseApiClient) -> str:
        """Возвращает название источника для указанного API-клиента."""
        if isinstance(client, CoinGeckoClient):
            return "CoinGecko"

        if isinstance(client, ExchangeRateApiClient):
            return "ExchangeRate-API"

        return type(client).__name__

    def run_update(self) -> dict:
        """Обновляет курсы и возвращает сводку выполнения."""

        self.errors = []
        self.updated_count = 0

        self.logger.info("Начало обновления валютных курсов")

        all_rates = {}
        last_refresh = None

        for client in self.clients:
            source = self.get_source(client)

            self.logger.info("Запрос курсов: %s", source)

            try:
                rates = client.fetch_rates()

                if not isinstance(rates, dict) or not rates:
                    raise ApiRequestError(f"{source} не вернул валютные курсы")

                self.logger.info(
                    "Получено %s курсов от %s",
                    len(rates),
                    source,
                )

            except Exception as error:
                self.errors.append(f"{source}: {type(error).__name__}")

                self.logger.exception(
                    "Ошибка получения курсов от %s",
                    source,
                )
                continue

            timestamp = (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )

            for pair, rate in rates.items():
                try:
                    from_currency, to_currency = pair.split("_")

                    record = {
                        "from_currency": from_currency,
                        "to_currency": to_currency,
                        "rate": rate,
                        "timestamp": timestamp,
                        "source": source,
                        "meta": {},
                    }

                    result = self.storage.save_record(record)

                    if result["cache_updated"]:
                        self.updated_count += 1
                        last_refresh = timestamp

                    all_rates[pair] = rate

                    self.logger.info(
                        "Курс %s обработан: rate=%s history_added=%s cache_updated=%s",
                        pair,
                        rate,
                        result["history_added"],
                        result["cache_updated"],
                    )

                except Exception as error:
                    self.errors.append(f"{source}, пара {pair}: {type(error).__name__}")

                    self.logger.exception(
                        "Ошибка обработки курса %s от %s",
                        pair,
                        source,
                    )

        # Ни один курс не удалось получить и обработать.
        if not all_rates:
            self.logger.error("Обновление не удалось: ни один курс не обработан")

            raise ApiRequestError(
                "Не удалось обновить валютные курсы. "
                "Проверьте подключение к интернету и повторите попытку позже."
            )

        self.logger.info(
            "Обновление завершено. Обработано курсов: %s, обновлено в кеше: %s",
            len(all_rates),
            self.updated_count,
        )

        return {
            "rates": all_rates,
            "updated_count": self.updated_count,
            "last_refresh": last_refresh,
            "errors": self.errors.copy(),
        }
