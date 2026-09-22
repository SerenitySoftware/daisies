from collections.abc import Iterable, Mapping
from typing import Any


def isdictlike(obj: Any) -> bool:
    # `items` has to be a *method*. The duck-type is here for mappings that
    # aren't Mapping subclasses, but merely having the attribute matched any
    # plain object with a field named `items` — a cart, an order, a page of
    # results — and reading one of those as a mapping raised on every hop.
    return isinstance(obj, Mapping) or callable(getattr(obj, "items", None))


def islistlike(obj: Any) -> bool:
    return isiterable(obj) and not isdictlike(obj) and not isinstance(obj, str)


def isiterable(obj: Any) -> bool:
    return isinstance(obj, Iterable)


def isnestable(obj: Any) -> bool:
    return isdictlike(obj) or islistlike(obj)
