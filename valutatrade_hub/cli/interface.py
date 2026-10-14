import shlex

from valutatrade_hub.core.usecases import register_user


def run() -> None:
    print("Welcome to ValutaTrade Hub!")
    print("Введите команду или 'exit' для выхода.")

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


def main() -> None:
    run()
