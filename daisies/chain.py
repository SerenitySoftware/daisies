from __future__ import annotations

import json as _json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, TypeVar, overload

from .sniff import isdictlike, isiterable, islistlike, isnestable

T = TypeVar("T")

_MISSING = object()
_UNSET = object()

# What a coercion callable raises when the value it got is the wrong shape for
# it. ValueError alone is not enough: Decimal("abc") raises
# decimal.InvalidOperation (an ArithmeticError), int(float("inf")) raises
# OverflowError, and a callable that reaches into the value — v["amount"],
# v.isoformat() — raises LookupError or AttributeError. Those are all "the
# vendor sent something else", which is exactly what Daisies absorbs.
# Deliberately not a bare Exception: a genuine bug inside a coercion callable
# (a NameError, a RecursionError) should still surface rather than quietly
# turning into the default.
_COERCION_FAILURES = (TypeError, ValueError, ArithmeticError, LookupError, AttributeError)

# The only key types json.dumps will take. Anything else raises TypeError, and
# its `default=` hook is never consulted for keys — see _json_safe.
_JSON_KEY_TYPES = (str, int, float, bool, type(None))

# Ambient strictness, for code that navigates data it did not wrap itself.
# A ContextVar rather than a module global so a strict region stays confined to
# the thread — or the async task — that opened it.
_STRICT: ContextVar[bool] = ContextVar("daisies_strict", default=False)

# The observer notified whenever a hop fails to resolve. Also a ContextVar, so
# a test can scope one to itself without disturbing a process-wide registration.
_ON_MISSING: ContextVar[Callable[[str], Any] | None] = ContextVar("daisies_on_missing", default=None)


class MissingPathError(Exception):
    """Raised in strict mode when a value that never resolved is unwrapped.

    The message is the offending chain's :meth:`Chain.trace`, so it names both
    the path you asked for and the hop that actually failed.
    """


@contextmanager
def strict() -> Iterator[None]:
    """Navigate strictly for the duration of the block.

    Every :class:`Chain` that hasn't pinned its own mode reads this, so it
    works on data someone else wrapped::

        with daisies.strict():
            payload.user.emial.value()  # raises MissingPathError

    Reentrant and scoped to the current thread or async task; leaving the
    block restores whatever was in force before it.
    """
    token = _STRICT.set(True)
    try:
        yield
    finally:
        _STRICT.reset(token)


class _MissingObserver:
    """The handle :func:`on_missing` hands back. See there for what it does."""

    __slots__ = ("_token",)

    def __init__(self, callback: Callable[[str], Any] | None) -> None:
        self._token = _ON_MISSING.set(callback)

    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc_info: Any) -> None:
        _ON_MISSING.reset(self._token)


def on_missing(callback: Callable[[str], Any] | None) -> _MissingObserver:
    """Call ``callback`` with the path of every hop that fails to resolve.

    Daisies survives a field the vendor stopped sending by returning ``None``
    — which also means nobody finds out. This is the signal: register once at
    startup and every miss becomes a countable, loggable event naming the
    field that went away::

        daisies.on_missing(lambda path: metrics.increment("daisies.missing", path))

    The callback receives the failing hop as a string in the same notation
    :meth:`Chain.trace` uses (``"user.address"``, ``"users[3].email"``), so the
    same path always groups together. Only the *first* failure in a chain fires
    — ``data.user.address.city`` with no ``address`` reports ``user.address``
    once, not three misses for one absent field.

    Strictly observational: it never changes what navigation returns, anything
    the callback raises is swallowed rather than surfacing at the call site,
    and a callback that navigates missing data itself won't re-enter. When no
    observer is registered the cost is a single context lookup per miss.

    Pass ``None`` to unregister. The return value can be used as a context
    manager to scope the registration instead, restoring the previous observer
    on the way out::

        with daisies.on_missing(seen.append):
            ...
    """
    return _MissingObserver(callback)


def _notify_missing(path: tuple[str, ...]) -> None:
    """Hand one failed hop to the registered observer, if there is one."""
    callback = _ON_MISSING.get()
    if callback is None:
        return

    # Muting the observer for the duration keeps a callback that navigates
    # missing data of its own from calling itself back.
    token = _ON_MISSING.set(None)
    try:
        callback(_render_path(path))
    except Exception:
        # An observer is a bystander; a broken one must not break the data
        # access it was watching.
        pass
    finally:
        _ON_MISSING.reset(token)


class Chain:
    __slots__ = ("_wrapped", "_exists", "_path", "_missed_at", "_strict")

    _wrapped: Any
    _exists: bool
    _path: tuple[str, ...]
    _missed_at: tuple[str, ...] | None
    _strict: bool | None

    def __init__(self, obj: Any = None, *, strict: bool | None = None) -> None:
        self._exists = obj is not _MISSING
        self._wrapped = None if obj is _MISSING else obj
        # Trace bookkeeping: the steps walked to get here, and the prefix of
        # those steps that first failed to resolve. Freshly wrapping an object
        # makes a root — it has walked nowhere and has nothing to explain.
        self._path = ()
        self._missed_at = None
        # None pins nothing and defers to the ambient ``daisies.strict()``
        # region, if any; True or False pin this chain either way.
        self._strict = strict

    def _fail_if_strict(self) -> None:
        """Refuse to hand back a stand-in for a hop that never resolved.

        Only unwrapping goes through here. Navigation itself stays silent so a
        strict chain behaves identically right up to the moment it would have
        quietly substituted ``None``, ``{}``, ``[]``, or ``"null"``.
        """
        if self._exists:
            return

        strict_here = _STRICT.get() if self._strict is None else self._strict
        if strict_here:
            raise MissingPathError(self.trace())

    def __repr__(self) -> str:
        return repr(self._wrapped)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self._fail_if_strict()
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
        default: Any = _UNSET,
    ) -> Any:
        """Unwrap the value, optionally coercing it and defaulting the gaps.

        Naming a ``default`` is how you say an absence is expected, so it is
        honoured even in strict mode; asking for the bare value in a strict
        region raises :class:`MissingPathError` instead.

        A coercion that fails falls back the same way a missing hop does — see
        :data:`_COERCION_FAILURES` for what counts as a failure.
        """
        if default is _UNSET:
            self._fail_if_strict()
            default = None
        wrapped = self._wrapped
        if wrapped is None:
            return default
        if type_ is None:
            return wrapped
        try:
            return type_(wrapped)
        except _COERCION_FAILURES:
            return default

    def json(self, indent: int | None = None, **kwargs: Any) -> str:
        """Serialize the wrapped value to a JSON string.

        Never raises: a missing or ``None`` wrapped value serializes to
        ``"null"``, and a value :func:`json.dumps` doesn't understand (a
        ``datetime``, ``Decimal``, ``set``, …) degrades to its string form
        rather than raising ``TypeError``. Pass your own ``default=`` to
        override that fallback. A dict *key* of one of those types degrades
        the same way — see :func:`_json_safe`, which also covers data that
        refers back to itself. Extra keyword arguments are forwarded to
        :func:`json.dumps`, so ``chain.json(indent=2, sort_keys=True)`` works.
        """
        self._fail_if_strict()
        kwargs.setdefault("default", str)
        try:
            return _json.dumps(self._wrapped, indent=indent, **kwargs)
        except (TypeError, ValueError):
            # Two shapes refuse to serialize before `default=` ever gets a
            # look in: a key that isn't a string or number, and data that
            # refers back to itself. Repairing those and trying once more
            # keeps the promise at the door while costing the ordinary
            # payload nothing.
            return _json.dumps(_json_safe(self._wrapped), indent=indent, **kwargs)

    def dict(self) -> dict[Any, Any]:
        """Return the wrapped value as a plain ``dict``.

        Returns an empty dict when the wrapped value isn't dict-like, keeping
        with the library's never-raise philosophy.
        """
        self._fail_if_strict()
        if isdictlike(self._wrapped):
            return dict(self._wrapped)

        return {}

    def list(self) -> list[Any]:
        """Return the wrapped value as a plain ``list``.

        Returns an empty list when the wrapped value isn't list-like — strings
        and dicts don't count — keeping with the never-raise philosophy.
        """
        self._fail_if_strict()
        if islistlike(self._wrapped):
            return list(self._wrapped)

        return []

    def exists(self) -> bool:
        """Return whether navigation resolved to a value.

        Falsy values and an explicit ``None`` still exist. Only a failed key,
        index, or attribute lookup is missing.
        """
        return self._exists

    def is_missing(self) -> bool:
        """Return whether navigation failed to resolve this node."""
        return not self._exists

    def fallback(self, fallback: Any) -> Chain:
        """Use ``fallback`` only when this node is missing.

        The fallback may be another :class:`Chain` or a plain value. The
        result always remains wrapped so navigation can continue.
        """
        if self._exists:
            return self

        if isinstance(fallback, Chain):
            return fallback

        replacement = Chain(fallback)
        # A literal fallback is a fresh root with no path to report, but it is
        # still part of this navigation, so it keeps the mode it was pinned to.
        replacement._strict = self._strict
        return replacement

    def pluck(self, *keys: Any) -> Chain:
        """Return a wrapped dict of just ``keys``, skipping the ones that aren't there.

        A whitelist projection for building a small outbound payload out of a
        big, untrusted one::

            >>> Chain({"id": 7, "email": "a@b.c", "secret": "x"}).pluck("id", "email").dict()
            {'id': 7, 'email': 'a@b.c'}

        Keys come back in the order you asked for them. A key that is absent is
        skipped silently rather than filled in with ``None``, so a present-but-
        null field stays distinguishable from one that was never sent. In
        keeping with the never-raise philosophy, a missing node or a value that
        isn't dict-like plucks to an empty dict — in a strict region, plucking
        off a hop that never resolved raises instead. The result stays wrapped,
        so it composes straight into ``.dict()``, ``.json()``, or further
        navigation.
        """
        source = self.dict()
        picked: dict[Any, Any] = {}
        for key in keys:
            try:
                if key in source:
                    picked[key] = source[key]
            except TypeError:
                # An unhashable key can never be in a mapping. Skipping it keeps
                # the promise that navigation never raises at the caller.
                continue

        return self._navigate(f".pluck({', '.join(repr(key) for key in keys)})", picked)

    def trace(self) -> str:
        """Explain in one line how navigation got here, and where it stopped.

        Built for dropping straight into a log line when a chain came back
        empty and you need to know which hop was to blame::

            >>> Chain({"user": {}}).user.address.city.trace()
            'user.address.city: missing at user.address'

        A node that resolved reports the path it walked instead, and an
        explicit ``None`` says so, so a key that is present but null stays
        distinguishable from one that was never there. Tracing is pure
        bookkeeping and never changes what navigation returns.
        """
        path = _render_path(self._path)
        if self._missed_at == self._path:
            # The very hop you asked for is the one that failed; naming it
            # twice would just pad the log line.
            return f"{path}: missing"
        if self._missed_at is not None:
            return f"{path}: missing at {_render_path(self._missed_at)}"
        if self._wrapped is None:
            return f"{path}: resolved (None)"

        return f"{path}: resolved"

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

    def _navigate(self, step: str, obj: Any) -> Chain:
        """Wrap the result of one navigation hop, carrying the trace path along.

        The path grows by ``step``, and ``_missed_at`` latches onto the *first*
        hop that failed, so ``.trace()`` can still name it however far
        navigation carried on afterwards.
        """
        chain = Chain(obj, strict=self._strict)
        chain._path = self._path + (step,)
        chain._missed_at = self._missed_at
        if chain._missed_at is None and obj is _MISSING:
            chain._missed_at = chain._path
            _notify_missing(chain._path)

        return chain

    def __getattr__(self, name: str) -> Chain:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)

        wrapped = self._wrapped
        step = f".{name}"

        if isdictlike(wrapped):
            got = wrapped.get(name, _MISSING)
            if got is not _MISSING:
                # A data key wins over the keys()/values()/items() proxies, so
                # `data.items[1]` still navigates a field literally named
                # "items". Reach a shadowed proxy via the method call instead.
                return self._navigate(step, got)
            if name in ("keys", "values", "items"):
                return self._navigate(step, lambda: _dict_view(wrapped, name))
            return self._navigate(step, _MISSING)

        # keys()/values()/items() stay null-tolerant off a dict: a missing or
        # non-dict node answers with an empty list rather than raising.
        if name in ("keys", "values", "items"):
            return self._navigate(step, lambda: _dict_view(wrapped, name))

        if not self._exists or wrapped is None:
            return self._navigate(step, _MISSING)

        return self._navigate(step, getattr(wrapped, name, _MISSING))

    def __getitem__(self, key: Any) -> Chain:
        item = _MISSING
        if self._exists and isiterable(self._wrapped):
            try:
                item = self._wrapped[key]
            except (KeyError, IndexError, TypeError):
                # TypeError is the wrong-container case, not a wrong-key one:
                # a string key on a list or a string, a float index, an
                # unhashable key. That is the same "the vendor sent a different
                # shape" family _COERCION_FAILURES absorbs, and the dotted form
                # of the same path already resolves to None, so bracket lookup
                # records it as a missed hop rather than raising at the caller.
                pass

        return self._navigate(f"[{key!r}]", item)

    def __iter__(self) -> Iterator[Chain]:
        # Yield wrapped items so navigation continues through a loop without
        # re-wrapping (e.g. ``for row in chain.users: row.name``). Wrapped items
        # still compare equal to their raw values, so ``sorted``/``==``/``in``
        # keep working. Returning None for non-iterables makes ``iter()`` raise
        # TypeError just as before (a generator function wouldn't — it defers).
        if isiterable(self._wrapped):
            return (self._navigate(f"[{index}]", item) for index, item in enumerate(self._wrapped))

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


def _json_safe(value: Any, seen: frozenset[int] = frozenset()) -> Any:
    """Rebuild ``value`` into something :func:`json.dumps` will accept.

    Only the two shapes ``dumps`` rejects outright are rewritten. A dict key
    that isn't a string, number, bool, or ``None`` becomes its string form —
    the same degradation ``default=str`` already gives an unserializable
    *value*, so a ``date`` reads as ``"2026-07-09"`` on either side of the
    colon. A container that contains itself becomes its string form too,
    rather than the ``ValueError`` ``dumps`` raises for a circular reference;
    tracking the containers on the way down is also what stops this walk from
    recursing forever on that data.

    Everything else is passed straight through, so a caller's own ``default=``
    still sees exactly the values it would have seen.
    """
    if id(value) in seen:
        return str(value)

    # Only dict/list/tuple, because those are precisely what dumps recurses
    # into itself; any other container is a value its `default=` handles.
    if isinstance(value, dict):
        nested = seen | {id(value)}
        return {
            (key if isinstance(key, _JSON_KEY_TYPES) else str(key)): _json_safe(item, nested)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        nested = seen | {id(value)}
        return [_json_safe(item, nested) for item in value]

    return value


def _dict_view(wrapped: Any, name: str) -> list[Any]:
    """Return a dict's ``keys``/``values``/``items`` as a plain ``list``.

    Null-tolerant: a value that isn't dict-like (a missing ``None`` node, a
    string, a list, a scalar) yields ``[]`` instead of raising, so the
    ``keys()``/``values()``/``items()`` proxies never break a chain.
    """
    if isdictlike(wrapped):
        return list(getattr(wrapped, name)())

    return []


def _render_path(steps: tuple[str, ...]) -> str:
    """Render recorded navigation steps the way you would have written them."""
    if not steps:
        return "<root>"

    return "".join(steps).removeprefix(".")


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
