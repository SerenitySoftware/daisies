from __future__ import annotations

import json as _json
from collections.abc import Callable, Iterator
from typing import Any, TypeVar, overload

from .sniff import isdictlike, isiterable, islistlike, isnestable

T = TypeVar("T")


class Chain:
    __slots__ = ("_wrapped",)

    _wrapped: Any

    def __init__(self, obj: Any = None) -> None:
        self._wrapped = obj

    def __repr__(self) -> str:
        return repr(self._wrapped)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if callable(self._wrapped):
            return self._wrapped(*args, **kwargs)

        return self._wrapped

    @overload
    def value(self) -> Any: ...
    @overload
    def value(self, *, default: T) -> Any | T: ...
    @overload
    def value(self, type_: Callable[[Any], T]) -> T | None: ...
    @overload
    def value(self, type_: Callable[[Any], T], *, default: T) -> T: ...

    def value(
        self,
        type_: Callable[[Any], Any] | None = None,
        *,
        default: Any = None,
    ) -> Any:
        wrapped = self._wrapped
        if wrapped is None:
            return default
        if type_ is None:
            return wrapped
        try:
            return type_(wrapped)
        except (TypeError, ValueError):
            return default

    def json(self, indent: int | None = None, **kwargs: Any) -> str:
        """Serialize the wrapped value to a JSON string.

        A missing or ``None`` wrapped value serializes to ``"null"`` rather
        than raising. Extra keyword arguments are forwarded to
        :func:`json.dumps`, so ``chain.json(indent=2, default=str)`` works.
        """
        return _json.dumps(self._wrapped, indent=indent, **kwargs)

    def dict(self) -> dict[Any, Any]:
        """Return the wrapped value as a plain ``dict``.

        Returns an empty dict when the wrapped value isn't dict-like, keeping
        with the library's never-raise philosophy.
        """
        if isdictlike(self._wrapped):
            return dict(self._wrapped)

        return {}

    def list(self) -> list[Any]:
        """Return the wrapped value as a plain ``list``.

        Returns an empty list when the wrapped value isn't list-like — strings
        and dicts don't count — keeping with the never-raise philosophy.
        """
        if islistlike(self._wrapped):
            return list(self._wrapped)

        return []

    def tree(self, *, max_depth: int = 6, max_items: int = 50) -> str:
        """Render the *shape* of the wrapped data as a terse, copy-pasteable tree.

        Tuned for exploring an unfamiliar payload rather than dumping every
        value: it shows keys, value types, list lengths, and a sample primitive
        at each leaf. Lists of dicts show their first element as a representative
        rather than every item. Deep or wide structures are truncated via
        ``max_depth`` and ``max_items``.

        Returns the tree as a string, so you typically ``print`` it::

            >>> print(Chain({"user": {"name": "Ada", "age": 36}}).tree())
            dict
            └─ user: dict
               ├─ name: str = 'Ada'
               └─ age: int = 36

        Never raises on odd input, in keeping with the library's philosophy.
        """
        lines: list[str] = []
        _tree_walk(None, self._wrapped, "", True, True, 0, max_depth, max_items, lines)
        return "\n".join(lines)

    def __str__(self) -> str:
        return str(self._wrapped)

    def __hash__(self) -> int:
        return hash(self._wrapped)

    def __getattr__(self, name: str) -> Chain:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)

        wrapped = self._wrapped

        if isdictlike(wrapped):
            attr = wrapped.get(name, None)
            if attr is None and name in ("keys", "items", "values") and hasattr(wrapped, name):
                attr = getattr(wrapped, name)
            return Chain(attr)

        if wrapped is None:
            return Chain(None)

        return Chain(getattr(wrapped, name, None))

    def __getitem__(self, key: Any) -> Chain:
        item = None
        if self._wrapped and isiterable(self._wrapped):
            try:
                item = self._wrapped[key]
            except (KeyError, IndexError):
                pass

        return Chain(item)

    def __iter__(self) -> Iterator[Chain]:
        # Yield wrapped items so navigation continues through a loop without
        # re-wrapping (e.g. ``for row in chain.users: row.name``). Wrapped items
        # still compare equal to their raw values, so ``sorted``/``==``/``in``
        # keep working. Returning None for non-iterables makes ``iter()`` raise
        # TypeError just as before (a generator function wouldn't — it defers).
        if isiterable(self._wrapped):
            return (Chain(item) for item in self._wrapped)

        return None  # type: ignore[return-value]

    def __contains__(self, item: Any) -> bool:
        if self._wrapped is None:
            return False

        return item in self._wrapped

    def __len__(self) -> int:
        if not self._wrapped:
            return 0

        return len(self._wrapped)

    def __bool__(self) -> bool:
        return bool(self._wrapped)

    def __eq__(self, other: object) -> bool:
        return self._wrapped == self.__maybe_unwrap(other)

    def __ne__(self, other: object) -> bool:
        return self._wrapped != self.__maybe_unwrap(other)

    def __gt__(self, other: Any) -> bool:
        comparison = self._wrapped
        if comparison is None:
            comparison = 0

        return comparison > other

    def __ge__(self, other: Any) -> bool:
        comparison = self._wrapped
        if comparison is None:
            comparison = 0

        return comparison >= other

    def __lt__(self, other: Any) -> bool:
        comparison = self._wrapped
        if comparison is None:
            comparison = 0

        return comparison < other

    def __le__(self, other: Any) -> bool:
        comparison = self._wrapped
        if comparison is None:
            comparison = 0

        return comparison <= other

    def __add__(self, other: Any) -> Chain:
        if self._wrapped is None:
            return self.__maybe_wrap(other)

        return Chain(self._wrapped + self.__maybe_unwrap(other))

    def __sub__(self, other: Any) -> Chain:
        if self._wrapped is None:
            return self.__maybe_wrap(-other)

        return Chain(self._wrapped - self.__maybe_unwrap(other))

    def __mul__(self, other: Any) -> Chain:
        if self._wrapped is None or not other:
            return Chain(0)

        return Chain(self._wrapped * self.__maybe_unwrap(other))

    def __truediv__(self, other: Any) -> Chain:
        if self._wrapped is None or not other:
            return Chain(0)

        return Chain(self._wrapped / self.__maybe_unwrap(other))

    def __floordiv__(self, other: Any) -> Chain:
        if self._wrapped is None or not other:
            return Chain(0)

        return Chain(self._wrapped // self.__maybe_unwrap(other))

    def __mod__(self, other: Any) -> Chain:
        if self._wrapped is None or not other:
            return Chain(0)

        return Chain(self._wrapped % self.__maybe_unwrap(other))

    def __pow__(self, other: Any) -> Chain:
        if self._wrapped is None:
            return Chain(0)

        return Chain(self._wrapped ** self.__maybe_unwrap(other))

    def __radd__(self, other: Any) -> Chain:
        if self._wrapped is None:
            return self.__maybe_wrap(other)

        return Chain(self.__maybe_unwrap(other) + self._wrapped)

    def __rsub__(self, other: Any) -> Chain:
        if self._wrapped is None:
            return self.__maybe_wrap(other)

        return Chain(self.__maybe_unwrap(other) - self._wrapped)

    def __rmul__(self, other: Any) -> Chain:
        if self._wrapped is None or not other:
            return Chain(0)

        return Chain(self.__maybe_unwrap(other) * self._wrapped)

    def __rtruediv__(self, other: Any) -> Chain:
        if not self._wrapped:
            return Chain(0)

        return Chain(self.__maybe_unwrap(other) / self._wrapped)

    def __rfloordiv__(self, other: Any) -> Chain:
        if not self._wrapped:
            return Chain(0)

        return Chain(self.__maybe_unwrap(other) // self._wrapped)

    def __rmod__(self, other: Any) -> Chain:
        if not self._wrapped:
            return Chain(0)

        return Chain(self.__maybe_unwrap(other) % self._wrapped)

    def __rpow__(self, other: Any) -> Chain:
        if self._wrapped is None:
            return Chain(0)

        return Chain(self.__maybe_unwrap(other) ** self._wrapped)

    def __int__(self) -> int:
        if self._wrapped is None:
            return 0

        return int(self._wrapped)

    def __float__(self) -> float:
        if self._wrapped is None:
            return 0.0

        return float(self._wrapped)

    def __index__(self) -> int:
        if self._wrapped is None:
            return 0

        return self._wrapped.__index__()

    @staticmethod
    def __maybe_wrap(obj: Any) -> Chain:
        if not isinstance(obj, Chain):
            obj = Chain(obj)

        return obj

    @staticmethod
    def __maybe_unwrap(obj: Any) -> Any:
        if isinstance(obj, Chain):
            return obj._wrapped

        return obj


def _short_repr(value: Any, limit: int = 40) -> str:
    """A single-line, length-bounded repr for use as a leaf sample."""
    text = repr(value)
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def _describe_node(value: Any, depth: int, max_depth: int) -> tuple[str, list[tuple[str, Any]] | None]:
    """Return a ``(descriptor, children)`` pair for one node.

    ``descriptor`` is the text shown on the node's own line; ``children`` is a
    list of ``(label, value)`` pairs to recurse into, or ``None`` for a leaf
    (scalar, empty container, or a container truncated by ``max_depth``).
    """
    if value is None:
        return "None", None
    # bool is a subclass of int, so it must be checked first.
    if isinstance(value, bool):
        return f"bool = {value}", None
    if isdictlike(value):
        if len(value) == 0:
            return "dict (empty)", None
        if depth >= max_depth:
            return f"dict {{…}} ({len(value)} keys)", None
        return "dict", [(str(k), v) for k, v in value.items()]
    if islistlike(value):
        items = list(value)
        count = len(items)
        if count == 0:
            return "list[0]", None
        element_types = {type(item) for item in items}
        all_scalar = all(not isnestable(item) and item is not None for item in items)
        if all_scalar and len(element_types) == 1:
            type_name = next(iter(element_types)).__name__
            return f"list[{count}] of {type_name} (e.g. {_short_repr(items[0])})", None
        if depth >= max_depth:
            return f"list[{count}] [...]", None
        # Show the first element as a representative of the whole list.
        return f"list[{count}]", [("[0]", items[0])]
    if isinstance(value, (int, float)):
        return f"{type(value).__name__} = {value}", None
    return f"{type(value).__name__} = {_short_repr(value)}", None


def _tree_walk(
    label: str | None,
    value: Any,
    prefix: str,
    is_last: bool,
    is_root: bool,
    depth: int,
    max_depth: int,
    max_items: int,
    lines: list[str],
) -> None:
    descriptor, children = _describe_node(value, depth, max_depth)
    if is_root:
        # The root has no key, so it renders as just its own descriptor.
        lines.append(descriptor)
        child_prefix = ""
    else:
        connector = "└─ " if is_last else "├─ "
        lines.append(f"{prefix}{connector}{label}: {descriptor}")
        child_prefix = prefix + ("   " if is_last else "│  ")

    if not children:
        return

    shown = children[:max_items]
    hidden = len(children) - len(shown)
    for index, (child_label, child_value) in enumerate(shown):
        child_is_last = index == len(shown) - 1 and hidden == 0
        _tree_walk(
            child_label,
            child_value,
            child_prefix,
            child_is_last,
            False,
            depth + 1,
            max_depth,
            max_items,
            lines,
        )
    if hidden:
        lines.append(f"{child_prefix}└─ … (+{hidden} more)")
