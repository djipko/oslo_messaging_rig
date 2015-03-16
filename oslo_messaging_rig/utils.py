import functools
import sys


def lazymap(func, iterable):
    for el in iterable:
        yield func(el)


class WrappedException(object):
    def __init__(self, exc):
        self.exc = exc

def returned_exception(response):
    return isinstance(response, WrappedException)


def return_exception(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return WrappedException(e)
    return wrapper
