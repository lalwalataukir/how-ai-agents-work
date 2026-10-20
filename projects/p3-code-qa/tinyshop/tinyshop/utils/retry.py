"""Retrying calls that fail for a moment, such as a network timeout."""
import functools
import random
import time


def retry(times=3, on=(Exception,), base_seconds=0.5):
    """Call the function again when it raises one of `on`, waiting longer each time (0.5 s, 1 s, 2 s,
    plus a little randomness so many clients don't retry at the same moment)."""
    def decorate(function):
        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            for attempt in range(times):
                try:
                    return function(*args, **kwargs)
                except on:
                    if attempt == times - 1:
                        raise
                    time.sleep(base_seconds * 2 ** attempt + random.uniform(0, 0.1))
        return wrapped
    return decorate
