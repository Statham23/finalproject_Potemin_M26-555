import shlex
from datetime import datetime

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


def run() -> None:
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

        elif args[0] == "whoami":
            if current_user is None:
                print("Сначала выполните login")
            else:
                print(f"Вы вошли как '{current_user.username}'")

        else:
            print(f"Неизвестная команда: {args[0]}")


def handle_register(args: list[str]) -> None:
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
    except ValueError as error:
        print(error)
        return

    print(
        f"Портфель пользователя '{current_user.username}' "
        f"(база: {result['base_currency']}):"
    )

    if not result["wallets"]:
        print("Портфель пуст")
        return

    for wallet in result["wallets"]:
        code = wallet["currency_code"]
        balance = wallet["balance"]
        value = wallet["value"]

        balance_precision = 4 if code in ("BTC", "ETH") else 2

        print(
            f"- {code}: {balance:,.{balance_precision}f} → {value:,.2f} {base_currency}"
        )

    print("--------------------------------------")
    print(f"ИТОГО: {result['total']:,.2f} {base_currency}")


def format_rate(rate: float) -> str:
    if rate < 1:
        return f"{rate:.8f}"
    return f"{rate:.2f}"


def handle_buy(args: list[str], current_user: User | None) -> None:
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
        print("Поддерживаемые валюты: USD, EUR, RUB, BTC, ETH")
        return
    except ValueError as error:
        print(error)
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
        print("Поддерживаемые валюты: USD, EUR, RUB, BTC, ETH")
        return

    except (InsufficientFundsError, ValueError) as error:
        print(error)
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
        print("Поддерживаемые валюты: USD, EUR, RUB, BTC, ETH")
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
        formatted_time = datetime.fromisoformat(updated_at).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    print(
        f"Курс {from_currency}→{to_currency}: "
        f"{format_rate(result['rate'])} "
        f"(обновлено: {formatted_time})"
    )

    print(
        f"Обратный курс {to_currency}→{from_currency}: "
        f"{format_rate(result['reverse_rate'])}"
    )


def main() -> None:
    run()
