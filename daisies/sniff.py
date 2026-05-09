from collections.abc import Iterable, Mapping
from typing import Any


def isdictlike(obj: Any) -> bool:
    return isinstance(obj, Mapping) or hasattr(obj, "items")


def islistlike(obj: Any) -> bool:
    return isiterable(obj) and not isdictlike(obj) and not isinstance(obj, str)


def isiterable(obj: Any) -> bool:
    return isinstance(obj, Iterable)


def isnestable(obj: Any) -> bool:
    return isdictlike(obj) or islistlike(obj)
