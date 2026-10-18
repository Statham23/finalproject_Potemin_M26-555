import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from valutatrade_hub.infra.settings import SettingsLoader

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def get_data_dir() -> Path:
    """Возвращает каталог данных из настроек приложения."""
    settings = SettingsLoader()

    data_dir = Path(settings.get("data_dir", "data"))

    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir

    return data_dir.resolve()


@dataclass(frozen=True)
class ParserConfig:
    """Конфигурация сервиса получения валютных курсов."""

    EXCHANGERATE_API_KEY: str | None = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY")
    )

    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    BASE_FIAT_CURRENCY: str = "USD"

    FIAT_CURRENCIES: tuple[str, ...] = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple[str, ...] = ("BTC", "ETH", "SOL")

    CRYPTO_ID_MAP: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    RATES_FILE_PATH: Path = field(default_factory=lambda: get_data_dir() / "rates.json")

    HISTORY_FILE_PATH: Path = field(
        default_factory=lambda: get_data_dir() / "exchange_rates.json"
    )

    REQUEST_TIMEOUT: int = 10
