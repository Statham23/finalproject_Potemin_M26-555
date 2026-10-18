from threading import Event

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import setup_parser_logging
from valutatrade_hub.parser_service.updater import RatesUpdater


class RatesScheduler:
    """Периодически запускает обновление валютных курсов."""

    def __init__(
        self,
        updater: RatesUpdater,
        interval_seconds: int = 300,
    ):
        if interval_seconds <= 0:
            raise ValueError("Интервал обновления должен быть положительным")

        self.updater = updater
        self.interval_seconds = interval_seconds
        self.stop_event = Event()
        self.logger = setup_parser_logging()

    def run(self) -> None:
        """Запускает цикл обновления до получения сигнала остановки."""

        self.logger.info("Планировщик обновления курсов запущен")

        while not self.stop_event.is_set():
            try:
                self.updater.run_update()
            except ApiRequestError:
                self.logger.exception("Не удалось обновить курсы по расписанию")

            if self.stop_event.wait(self.interval_seconds):
                break

        self.logger.info("Планировщик обновления курсов остановлен")

    def stop(self) -> None:
        """Останавливает цикл обновления."""

        self.stop_event.set()
