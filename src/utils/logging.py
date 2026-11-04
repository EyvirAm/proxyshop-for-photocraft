"""
* Utils: Logging

Logging decorators.
"""
from __future__ import annotations
from collections.abc import Callable
from functools import wraps
from logging import Logger, getLogger

_logger = getLogger(__name__)


def log_on_exception[**P, T, E: Exception](
    msg: str | Callable[[E], str] = "",
    exception_type: type[E] = Exception,
    logger: Logger = _logger,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Log exceptions raised by the decorated function."""
    def decorator(func: Callable[P, T]):
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs):
            """Wrapper."""
            try:
                return func(*args, **kwargs)
            except exception_type as e:
                logger.exception(msg if isinstance(msg, str) else msg(e))  # noqa: TRY401
                raise

        return wrapper

    return decorator
