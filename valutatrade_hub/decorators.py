from functools import wraps
from inspect import signature

from valutatrade_hub.logging_config import setup_logging


def log_action(action: str, verbose: bool = False):
    """Логирует результат выполнения доменной операции."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = setup_logging()

            bound = signature(func).bind(*args, **kwargs)
            bound.apply_defaults()

            user_id = bound.arguments.get("user_id")
            currency = bound.arguments.get("currency_code")
            amount = bound.arguments.get("amount")

            formatted_amount = (
                f"{amount:.4f}"
                if isinstance(amount, (int, float)) and not isinstance(amount, bool)
                else repr(amount)
            )

            context = (
                f"{action} user_id={user_id} "
                f"currency={currency!r} amount={formatted_amount}"
            )

            try:
                result = func(*args, **kwargs)

            except Exception as error:
                logger.info(
                    "%s result=ERROR error_type=%r error_message=%r",
                    context,
                    type(error).__name__,
                    str(error),
                )
                raise

            rate = result.get("rate") if isinstance(result, dict) else None

            details = f"{context} rate={rate!r} base='USD' result=OK"

            if verbose and isinstance(result, dict):
                old_balance = result.get("old_balance")
                new_balance = result.get("new_balance")

                details += f" old_balance={old_balance!r} new_balance={new_balance!r}"

            logger.info("%s", details)
            return result

        return wrapper

    return decorator
