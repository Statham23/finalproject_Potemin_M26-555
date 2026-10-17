import math
import re
from datetime import datetime, timezone
from pathlib import Path

from valutatrade_hub.infra.database import DatabaseManager

CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{2,5}$")


def validate_rate_record(record: dict) -> dict:
    """Проверяет и нормализует запись курса."""

    from_currency = record["from_currency"]
    to_currency = record["to_currency"]
    rate = record["rate"]
    timestamp = record["timestamp"]
    source = record["source"]

    for code in (from_currency, to_currency):
        if not isinstance(code, str) or not CURRENCY_CODE_PATTERN.fullmatch(code):
            raise ValueError("Код валюты должен содержать 2–5 заглавных латинских букв")

    if (
        isinstance(rate, bool)
        or not isinstance(rate, (int, float))
        or not math.isfinite(rate)
        or rate <= 0
    ):
        raise ValueError("Курс должен быть положительным конечным числом")

    if not isinstance(timestamp, str):
        raise ValueError("timestamp должен быть строкой в формате ISO-UTC")

    try:
        parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Некорректный формат timestamp") from error

    if parsed_time.tzinfo is None or parsed_time.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp должен содержать часовой пояс UTC")

    normalized_timestamp = (
        parsed_time.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )

    if not isinstance(source, str) or not source.strip():
        raise ValueError("Не указан источник курса")

    meta = record.get("meta", {})

    if not isinstance(meta, dict):
        raise ValueError("meta должен быть словарём")

    return {
        "id": f"{from_currency}_{to_currency}_{normalized_timestamp}",
        "from_currency": from_currency,
        "to_currency": to_currency,
        "rate": float(rate),
        "timestamp": normalized_timestamp,
        "source": source.strip(),
        "meta": meta,
    }


def save_rate_record(record: dict, data_dir: Path | None = None) -> bool:
    """
    Сохраняет запись в историю.

    Возвращает True, если запись добавлена,
    False, если запись с таким id уже существует.
    """

    validated_record = validate_rate_record(record)

    db = DatabaseManager()
    history = db.load("exchange_rates.json", data_dir=data_dir)

    if not isinstance(history, list):
        raise ValueError("История курсов должна быть списком")

    existing_ids = {item["id"] for item in history}

    if validated_record["id"] in existing_ids:
        return False

    history.append(validated_record)

    db.save("exchange_rates.json", history, data_dir=data_dir)

    return True


def update_rates_cache(
    record: dict,
    data_dir: Path | None = None,
) -> bool:
    """
    Обновляет rates.json, если полученный курс новее сохранённого.

    Возвращает:
        True — кеш обновлён.
        False — запись не новее существующей.
    """
    validated_record = validate_rate_record(record)

    db = DatabaseManager()
    cache = db.load("rates.json", data_dir=data_dir)

    if not isinstance(cache, dict) or not isinstance(cache.get("pairs"), dict):
        raise ValueError("Некорректный формат rates.json: ожидается объект pairs")

    pair = f"{validated_record['from_currency']}_{validated_record['to_currency']}"

    new_timestamp = validated_record["timestamp"]
    current_record = cache["pairs"].get(pair)

    if current_record is not None:
        current_timestamp = datetime.fromisoformat(
            current_record["updated_at"].replace("Z", "+00:00")
        )

        new_datetime = datetime.fromisoformat(new_timestamp.replace("Z", "+00:00"))

        if new_datetime <= current_timestamp:
            return False

    cache["pairs"][pair] = {
        "rate": validated_record["rate"],
        "updated_at": new_timestamp,
        "source": validated_record["source"],
    }

    cache["last_refresh"] = (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )

    db.save("rates.json", cache, data_dir=data_dir)

    return True


class RatesStorage:
    """Хранилище истории и актуального кеша курсов."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir

    def save_record(self, record: dict) -> dict:
        history_added = save_rate_record(
            record,
            data_dir=self.data_dir,
        )

        cache_updated = update_rates_cache(
            record,
            data_dir=self.data_dir,
        )

        return {
            "history_added": history_added,
            "cache_updated": cache_updated,
        }
