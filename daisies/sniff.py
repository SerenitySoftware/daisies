from collections.abc import Iterable, Mapping
from typing import Any


def isdictlike(obj: Any) -> bool:
    if isinstance(obj, Mapping):
        return True

    # Navigation, dict conversion and tree inspection share this read protocol.
    # Python looks special methods up on the type, not the instance.
    try:
        return all(callable(getattr(obj, name, None)) for name in ("get", "keys", "items")) and all(
            callable(getattr(type(obj), name, None)) for name in ("__getitem__", "__len__")
        )
    except Exception:
        # A descriptor that cannot be read does not advertise a usable protocol.
        # Do not call the methods here or consume an arbitrary items iterator.
        return False


def islistlike(obj: Any) -> bool:
    return isiterable(obj) and not isdictlike(obj) and not isinstance(obj, str)


def isiterable(obj: Any) -> bool:
    return isinstance(obj, Iterable)


def isnestable(obj: Any) -> bool:
    return isdictlike(obj) or islistlike(obj)
