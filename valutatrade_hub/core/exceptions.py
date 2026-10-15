class CurrencyNotFoundError(Exception):
    """Валюта не найдена в реестре."""


class InsufficientFundsError(Exception):
    """Недостаточно средств для выполнения операции."""


class ApiRequestError(Exception):
    """Ошибка при обращении к внешнему API."""
