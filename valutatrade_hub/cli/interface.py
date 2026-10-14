import shlex

from valutatrade_hub.core.models import User
from valutatrade_hub.core.usecases import (
    login_user,
    register_user,
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


def main() -> None:
    run()
