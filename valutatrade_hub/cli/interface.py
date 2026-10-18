import math
import shlex
from datetime import datetime

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import CURRENCY_REGISTRY, CryptoCurrency
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import User
from valutatrade_hub.core.usecases import (
    buy,
    get_rate,
    login_user,
    register_user,
    sell,
    show_portfolio,
)
from valutatrade_hub.core.utils import load_json
from valutatrade_hub.logging_config import parser_console_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


def run() -> None:
    """Запускает интерактивный интерфейс командной строки."""

    print("Welcome to ValutaTrade Hub!")
    print("Введите команду или 'exit' для выхода.")

    current_user = None

    while True:
        try:
            command = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход из программы.")
            break

        if not command:
            continue

        try:
            args = shlex.split(command)
        except ValueError as error:
            print(f"Ошибка разбора команды: {error}")
            continue

        if args[0] == "exit":
            print("Выход из программы.")
            break

        if args[0] == "register":
            handle_register(args[1:])

        elif args[0] == "login":
            user = handle_login(args[1:])

            if user is not None:
                current_user = user

        elif args[0] == "show-portfolio":
            handle_show_portfolio(args[1:], current_user)

        elif args[0] == "buy":
            handle_buy(args[1:], current_user)

        elif args[0] == "sell":
            handle_sell(args[1:], current_user)

        elif args[0] == "get-rate":
            handle_get_rate(args[1:])

        elif args[0] == "update-rates":
            handle_update_rates(args[1:])

        elif args[0] == "show-rates":
            handle_show_rates(args[1:])

        elif args[0] == "whoami":
            if current_user is None:
                print("Сначала выполните login")
            else:
                print(f"Вы вошли как '{current_user.username}'")

        else:
            print(f"Неизвестная команда: {args[0]}")


def handle_register(args: list[str]) -> None:
    """Обрабатывает регистрацию нового пользователя."""

    if len(args) != 4 or args[0] != "--username" or args[2] != "--password":
        print("Использование: register --username <имя> --password <пароль>")
        return

    username = args[1]
    password = args[3]

    try:
        user = register_user(username, password)
    except ValueError as error:
        print(error)
        return

    print(f"Пользователь '{user.username}' зарегистрирован (id={user.user_id}).")
    print(f"Войдите: login --username {user.username} --password ****")


def handle_login(args: list[str]):
    """Проверяет учётные данные и выполняет вход пользователя."""

    if len(args) != 4 or args[0] != "--username" or args[2] != "--password":
        print("Использование: login --username <имя> --password <пароль>")
        return None

    username = args[1]
    password = args[3]

    try:
        user = login_user(username, password)
    except ValueError as error:
        print(error)
        return None

    print(f"Вы вошли как '{user.username}'")
    return user


def handle_show_portfolio(args: list[str], current_user: User | None) -> None:
    """Отображает валютные кошельки и общую стоимость портфеля."""

    if current_user is None:
        print("Сначала выполните login")
        return

    if not args:
        base_currency = "USD"
    elif len(args) == 2 and args[0] == "--base":
        base_currency = args[1]
    else:
        print("Использование: show-portfolio --base <валюта>")
        return

    try:
        result = show_portfolio(
            user_id=current_user.user_id,
            base_currency=base_currency,
        )
    except (ValueError, CurrencyNotFoundError, ApiRequestError) as error:
        print(f"Ошибка: {error}")
        return

    print(
        f"Портфель пользователя '{current_user.username}' "
        f"(база: {result['base_currency']}):"
    )

    if not result["wallets"]:
        print("Портфель пуст")
        return

    table = PrettyTable()

    table.field_names = ["Валюта", "Баланс", f"Стоимость ({base_currency})"]

    table.align["Валюта"] = "l"
    table.align["Баланс"] = "r"
    table.align[f"Стоимость ({base_currency})"] = "r"

    for wallet in result["wallets"]:
        code = wallet["currency_code"]
        balance = wallet["balance"]
        value = wallet["value"]

        currency = CURRENCY_REGISTRY.get(code)
        balance_precision = 4 if isinstance(currency, CryptoCurrency) else 2

        table.add_row(
            [
                code,
                f"{balance:,.{balance_precision}f}",
                f"{value:,.2f}",
            ]
        )

    print(table)
    print(f"ИТОГО: {result['total']:,.2f} {base_currency}")


def format_rate(rate: float) -> str:
    """Форматирует валютный курс для вывода в консоль."""

    if rate < 1:
        return f"{rate:.8f}"
    return f"{rate:.2f}"


def handle_buy(args: list[str], current_user: User | None) -> None:
    """Обрабатывает покупку валюты текущим пользователем."""

    if current_user is None:
        print("Сначала выполните login")
        return

    if len(args) != 4 or args[0] != "--currency" or args[2] != "--amount":
        print("Использование: buy --currency <код валюты> --amount <количество>")
        return

    currency_code = args[1]

    try:
        amount = float(args[3])
    except ValueError:
        print("'amount' должен быть положительным числом")
        return

    try:
        result = buy(
            user_id=current_user.user_id,
            currency_code=currency_code,
            amount=amount,
        )
    except CurrencyNotFoundError as error:
        print(error)
        print("Поддерживаемые валюты: " + ", ".join(CURRENCY_REGISTRY))
        return
    except (ValueError, ApiRequestError) as error:
        print(f"Ошибка: {error}")
        return

    print(
        f"Покупка выполнена: {result['amount']:.4f} "
        f"{result['currency_code']} по курсу "
        f"{format_rate(result['rate'])} USD/{result['currency_code']}"
    )

    print("Изменения в портфеле:")
    print(
        f"- {result['currency_code']}: "
        f"было {result['old_balance']:.4f} → "
        f"стало {result['new_balance']:.4f}"
    )

    print(f"Оценочная стоимость покупки: {result['estimated_cost']:,.2f} USD")


def handle_sell(args: list[str], current_user: User | None) -> None:
    """Обрабатывает продажу валюты текущим пользователем."""

    if current_user is None:
        print("Сначала выполните login")
        return

    if len(args) != 4 or args[0] != "--currency" or args[2] != "--amount":
        print("Использование: sell --currency <код> --amount <количество>")
        return

    currency_code = args[1]

    try:
        amount = float(args[3])
    except ValueError:
        print("'amount' должен быть положительным числом")
        return

    try:
        result = sell(
            user_id=current_user.user_id,
            currency_code=currency_code,
            amount=amount,
        )
    except CurrencyNotFoundError as error:
        print(error)
        print("Поддерживаемые валюты: " + ", ".join(CURRENCY_REGISTRY))
        return

    except (InsufficientFundsError, ValueError, ApiRequestError) as error:
        print(f"Ошибка: {error}")
        return

    print(
        f"Продажа выполнена: {result['amount']:.4f} "
        f"{result['currency_code']} по курсу "
        f"{format_rate(result['rate'])} USD/{result['currency_code']}"
    )

    print("Изменения в портфеле:")
    print(
        f"- {result['currency_code']}: "
        f"было {result['old_balance']:.4f} → "
        f"стало {result['new_balance']:.4f}"
    )

    print(f"Оценочная выручка: {result['estimated_revenue']:,.2f} USD")


def handle_get_rate(args: list[str]) -> None:
    """Отображает прямой и обратный валютные курсы."""

    if len(args) != 4 or args[0] != "--from" or args[2] != "--to":
        print("Использование: get-rate --from <валюта> --to <валюта>")
        return

    from_currency = args[1]
    to_currency = args[3]

    try:
        result = get_rate(
            from_currency=from_currency,
            to_currency=to_currency,
        )
    except CurrencyNotFoundError as error:
        print(error)
        print("Поддерживаемые валюты: " + ", ".join(CURRENCY_REGISTRY))
        print("Использование: get-rate --from USD --to BTC")
        return
    except ApiRequestError as error:
        print(error)
        return
    except ValueError as error:
        print(error)
        return

    updated_at = result["updated_at"]

    if updated_at is None:
        formatted_time = "не требуется"
    else:
        formatted_time = datetime.fromisoformat(
            updated_at.replace("Z", "+00:00")
        ).strftime("%Y-%m-%d %H:%M:%S UTC")

    print(
        f"Курс {from_currency}→{to_currency}: "
        f"{format_rate(result['rate'])} "
        f"(обновлено: {formatted_time})"
    )

    print(
        f"Обратный курс {to_currency}→{from_currency}: "
        f"{format_rate(result['reverse_rate'])}"
    )


def handle_update_rates(args: list[str]) -> None:
    """Обновляет курсы валют через Parser Service."""

    if not args:
        source = "all"
    elif len(args) == 2 and args[0] == "--source":
        source = args[1].lower()
    else:
        print("Использование: update-rates [--source coingecko|exchangerate]")
        return

    if source not in ("all", "coingecko", "exchangerate"):
        print(
            f"Неизвестный источник '{source}'. "
            "Доступные источники: coingecko, exchangerate"
        )
        return

    clients = []

    if source in ("all", "coingecko"):
        clients.append(CoinGeckoClient())

    if source in ("all", "exchangerate"):
        clients.append(ExchangeRateApiClient())

    updater = RatesUpdater(
        clients=clients,
        storage=RatesStorage(),
    )

    print("Начинаем обновление валютных курсов...")

    try:
        with parser_console_logging():
            result = updater.run_update()
    except ApiRequestError as error:
        print(f"Ошибка обновления курсов: {error}")
        return

    if result["errors"]:
        print("Обновление завершено с ошибками.")
    else:
        print("Обновление успешно завершено!")

    print(f"Получено курсов: {len(result['rates'])}")
    print(f"Обновлено записей кеша: {result['updated_count']}")
    print(f"Последнее обновление: {result['last_refresh']}")

    if result["errors"]:
        print("Подробности ошибок смотрите в logs/parser.log.")


def handle_show_rates(args: list[str]) -> None:
    """Показывает валютные курсы из локального кеша."""

    currency = None
    base = "USD"
    top = None
    base_specified = False

    if len(args) % 2 != 0:
        print(
            "Использование: show-rates "
            "[--currency <код>] [--top <число>] [--base <код>]"
        )
        return

    for i in range(0, len(args), 2):
        flag = args[i]
        value = args[i + 1]

        if flag == "--currency":
            if currency is not None:
                print("Параметр --currency указан повторно")
                return
            currency = value.upper()

        elif flag == "--top":
            if top is not None:
                print("Параметр --top указан повторно")
                return

            try:
                top = int(value)
            except ValueError:
                print("Параметр --top должен быть положительным целым числом")
                return

            if top <= 0:
                print("Параметр --top должен быть положительным целым числом")
                return

        elif flag == "--base":
            if base_specified:
                print("Параметр --base указан повторно")
                return

            base = value.upper()
            base_specified = True

        else:
            print(f"Неизвестный параметр: {flag}")
            return

    if currency is not None and top is not None:
        print("Параметры --currency и --top нельзя использовать вместе")
        return

    try:
        rates_data = load_json("rates.json")
    except FileNotFoundError:
        print(
            "Локальный кеш курсов пуст. "
            "Выполните 'update-rates', чтобы загрузить данные."
        )
        return
    except ValueError:
        print("Не удалось прочитать rates.json: некорректный JSON.")
        return

    if not isinstance(rates_data, dict):
        print("Некорректный формат rates.json: ожидается JSON-объект.")
        return

    pairs = rates_data.get("pairs")

    if not isinstance(pairs, dict):
        print("Некорректный формат rates.json: ожидается объект pairs.")
        return

    if not pairs:
        print(
            "Локальный кеш курсов пуст. "
            "Выполните 'update-rates', чтобы загрузить данные."
        )
        return

    usd_rates = {"USD": 1.0}

    for pair, data in pairs.items():
        if not isinstance(data, dict):
            continue

        if not pair.endswith("_USD"):
            continue

        rate = data.get("rate")

        if (
            isinstance(rate, bool)
            or not isinstance(rate, (int, float))
            or not math.isfinite(rate)
            or rate <= 0
        ):
            continue

        code = pair.removesuffix("_USD")
        usd_rates[code] = float(rate)

    if base not in usd_rates:
        print(f"Курс для '{base}' не найден в кеше.")
        return

    if currency is not None and currency not in usd_rates:
        print(f"Курс для '{currency}' не найден в кеше.")
        return

    if top is not None:
        crypto_codes = ("BTC", "ETH", "SOL")

        selected = [code for code in crypto_codes if code in usd_rates and code != base]

        selected.sort(
            key=lambda code: usd_rates[code] / usd_rates[base],
            reverse=True,
        )

        selected = selected[:top]

    elif currency is not None:
        selected = [currency]

    else:
        selected = sorted(code for code in usd_rates if code != base)

    if not selected:
        print("Нет курсов для отображения.")
        return

    print(
        "Курсы из локального кеша "
        f"(последнее обновление: {rates_data.get('last_refresh', 'неизвестно')}):"
    )

    table = PrettyTable()

    table.field_names = ["Пара", "Курс", "Обновлено"]
    table.align["Пара"] = "l"
    table.align["Курс"] = "r"
    table.align["Обновлено"] = "l"

    for code in selected:
        pair = f"{code}_{base}"

        if code == base:
            rate = 1.0
        else:
            rate = usd_rates[code] / usd_rates[base]

        source_times = []

        for currency_code in (code, base):
            if currency_code == "USD":
                continue

            source_data = pairs.get(f"{currency_code}_USD", {})

            if not isinstance(source_data, dict):
                continue

            updated_at = source_data.get("updated_at")

            if isinstance(updated_at, str):
                source_times.append(updated_at)

        if source_times:
            updated_at = min(source_times)
        else:
            updated_at = "неизвестно"

        table.add_row([pair, format_rate(rate), updated_at])

    print(table)


def main() -> None:
    run()
