"""Reusable function decorators."""

import logging
import sys
from collections.abc import Callable
from datetime import datetime
from typing import ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def task(label: str) -> Callable[[Callable[P, T]], Callable[P, None]]:
    """
    Wrap a callable so it logs start/end and total runtime, and exits the
    process with status ``1`` if the wrapped callable raises. The return
    value of the wrapped callable is discarded.

    ----------
    Parameters
    ----------
    label : str
        Tag used as prefix in every log line emitted by the wrapper.

    ----------
    Returns
    ----------
    Callable[[Callable[P, T]], Callable[P, None]]
        Decorator that turns the target callable into a logged task.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, None]:
        """Bind ``func`` to the logging/error-handling wrapper."""

        def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
            """Run ``func`` with logging and process-exit-on-failure."""
            try:
                start_time = datetime.today()
                logger.info(f"[{label}] Starting task execution at '{start_time}'...")
                func(*args, **kwargs)
                sec_elapsed = (datetime.today() - start_time).total_seconds()
                logger.info(f"[{label}] Succesfully executed all steps from task!")
                logger.info(f"[{label}] Task took {sec_elapsed:.2f} seconds.")
            except Exception as exc:  # pylint: disable=W0718
                logger.error(
                    f"[{label}] Something went wrong... Could not finish task!" f"\nReason: {exc}"
                )
                sys.exit(1)

        return wrapper

    return decorator
