class CurrencyNotFoundError(Exception):
    """Валюта не найдена в реестре."""


class InsufficientFundsError(Exception):
    """Недостаточно средств для выполнения операции."""
