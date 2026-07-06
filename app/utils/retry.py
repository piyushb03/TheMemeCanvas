"""
TheMemeCanvas Automation Suite — Retry Decorator with Exponential Backoff
=========================================================================
Provides a configurable retry decorator for any function that may fail
transiently (API calls, downloads, uploads, etc.).
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from typing import Callable, Optional, Tuple, Type

logger = logging.getLogger("thememecanvas.pipeline")


def retry_with_backoff(
    max_attempts: int = 3,
    delays: Tuple[float, ...] = (60, 300, 900, 3600),  # seconds
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    raise_on_failure: bool = True,
):
    """
    Decorator: retry a function on failure with configurable delays.

    Args:
        max_attempts: Maximum number of total attempts (1 = no retry).
        delays: Tuple of wait times (seconds) between attempts.
                If fewer delays than attempts, last delay is reused.
        exceptions: Tuple of exception types to catch and retry on.
        on_retry: Optional callback(attempt_number, exception) called before each retry.
        raise_on_failure: If True, re-raises the last exception after all attempts fail.

    Usage:
        @retry_with_backoff(max_attempts=4, delays=(300, 900, 1800, 3600))
        def upload_to_youtube(...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc

                    if attempt == max_attempts:
                        logger.error(
                            "All %d attempts failed for %s. Last error: %s",
                            max_attempts,
                            func.__name__,
                            exc,
                        )
                        if raise_on_failure:
                            raise
                        return None

                    delay_idx = min(attempt - 1, len(delays) - 1)
                    delay = delays[delay_idx]

                    logger.warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %.0f seconds...",
                        attempt,
                        max_attempts,
                        func.__name__,
                        exc,
                        delay,
                    )

                    if on_retry:
                        try:
                            on_retry(attempt, exc)
                        except Exception as cb_exc:
                            logger.warning("on_retry callback failed: %s", cb_exc)

                    time.sleep(delay)

            if raise_on_failure and last_exc:
                raise last_exc
            return None

        return wrapper

    return decorator


def retry_with_backoff_async(
    max_attempts: int = 3,
    delays: Tuple[float, ...] = (60, 300, 900, 3600),
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    raise_on_failure: bool = True,
):
    """Async version of retry_with_backoff for async functions."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc

                    if attempt == max_attempts:
                        logger.error(
                            "All %d async attempts failed for %s. Last error: %s",
                            max_attempts,
                            func.__name__,
                            exc,
                        )
                        if raise_on_failure:
                            raise
                        return None

                    delay_idx = min(attempt - 1, len(delays) - 1)
                    delay = delays[delay_idx]

                    logger.warning(
                        "Async attempt %d/%d failed for %s: %s. Retrying in %.0f seconds...",
                        attempt,
                        max_attempts,
                        func.__name__,
                        exc,
                        delay,
                    )

                    if on_retry:
                        try:
                            on_retry(attempt, exc)
                        except Exception:
                            pass

                    await asyncio.sleep(delay)

            if raise_on_failure and last_exc:
                raise last_exc
            return None

        return wrapper

    return decorator


class RetryableError(Exception):
    """Raise this to signal a retryable condition explicitly."""
    pass


class PermanentError(Exception):
    """Raise this to signal a non-retryable failure — skips retry logic."""
    pass
