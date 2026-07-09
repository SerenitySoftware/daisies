import json
import unittest

from daisies import Chain


class TestJson(unittest.TestCase):
    """`.json()` serializes the wrapped value to a JSON string."""

    def test_serializes_dict(self):
        assert Chain({"a": 1}).json() == '{"a": 1}'

    def test_serializes_list(self):
        assert Chain([1, 2, 3]).json() == "[1, 2, 3]"

    def test_serializes_scalars(self):
        assert Chain(42).json() == "42"
        assert Chain("hi").json() == '"hi"'
        assert Chain(True).json() == "true"

    def test_missing_serializes_to_null(self):
        # Null-tolerant: a missing key serializes to JSON null, not an error.
        assert Chain({"a": 1}).missing.json() == "null"
        assert Chain(None).json() == "null"

    def test_indent_forwarded(self):
        assert Chain({"a": 1}).json(indent=2) == '{\n  "a": 1\n}'

    def test_kwargs_forwarded_to_dumps(self):
        # `default=` lets users serialize otherwise-unserializable values.
        result = Chain({"nums": {3, 1, 2}}).json(default=sorted)
        assert json.loads(result) == {"nums": [1, 2, 3]}

    def test_sort_keys_kwarg(self):
        assert Chain({"b": 1, "a": 2}).json(sort_keys=True) == '{"a": 2, "b": 1}'

    def test_roundtrips_after_navigation(self):
        data = Chain({"user": {"name": "Alice", "tags": ["x", "y"]}})
        assert json.loads(data.user.json()) == {"name": "Alice", "tags": ["x", "y"]}

    def test_unserializable_value_stringifies(self):
        # Never-raise all the way to the door: a value json.dumps doesn't know
        # (datetime, Decimal, set, an arbitrary object) degrades to its string
        # form instead of raising TypeError.
        from datetime import date
        from decimal import Decimal

        assert Chain({"when": date(2026, 7, 9)}).json() == '{"when": "2026-07-09"}'
        assert Chain(Decimal("1.5")).json() == '"1.5"'
        # A bare object() still produces a string rather than blowing up.
        result = Chain({"obj": object()}).json()
        assert json.loads(result)["obj"].startswith("<object object")

    def test_default_override_still_wins(self):
        # The permissive default is only a fallback — an explicit default= wins.
        result = Chain({"nums": {3, 1, 2}}).json(default=sorted)
        assert json.loads(result) == {"nums": [1, 2, 3]}


class TestDict(unittest.TestCase):
    """`.dict()` returns the wrapped value as a plain dict, or `{}`."""

    def test_returns_wrapped_dict(self):
        assert Chain({"a": 1, "b": 2}).dict() == {"a": 1, "b": 2}

    def test_returns_plain_dict_type(self):
        assert type(Chain({"a": 1}).dict()) is dict

    def test_returns_dict_after_navigation(self):
        data = Chain({"user": {"name": "Alice"}})
        assert data.user.dict() == {"name": "Alice"}

    def test_missing_returns_empty_dict(self):
        assert Chain({"a": 1}).missing.dict() == {}

    def test_none_returns_empty_dict(self):
        assert Chain(None).dict() == {}

    def test_non_dict_returns_empty_dict(self):
        assert Chain([1, 2, 3]).dict() == {}
        assert Chain("hello").dict() == {}
        assert Chain(42).dict() == {}

    def test_returns_a_copy(self):
        raw = {"a": 1}
        result = Chain(raw).dict()
        result["b"] = 2
        assert raw == {"a": 1}


class TestList(unittest.TestCase):
    """`.list()` returns the wrapped value as a plain list, or `[]`."""

    def test_returns_wrapped_list(self):
        assert Chain([1, 2, 3]).list() == [1, 2, 3]

    def test_returns_plain_list_type(self):
        assert type(Chain([1, 2, 3]).list()) is list

    def test_coerces_tuple_and_set(self):
        assert Chain((1, 2, 3)).list() == [1, 2, 3]
        assert sorted(Chain({1, 2, 3}).list()) == [1, 2, 3]

    def test_coerces_generator(self):
        assert Chain(range(3)).list() == [0, 1, 2]

    def test_returns_list_after_navigation(self):
        data = Chain({"names": ["Alice", "Bob"]})
        assert data.names.list() == ["Alice", "Bob"]

    def test_missing_returns_empty_list(self):
        assert Chain({"a": 1}).missing.list() == []

    def test_none_returns_empty_list(self):
        assert Chain(None).list() == []

    def test_string_returns_empty_list(self):
        # Strings are iterable but not list-like — don't explode into chars.
        assert Chain("hello").list() == []

    def test_dict_returns_empty_list(self):
        assert Chain({"a": 1}).list() == []

    def test_scalar_returns_empty_list(self):
        assert Chain(42).list() == []

    def test_returns_a_copy(self):
        raw = [1, 2, 3]
        result = Chain(raw).list()
        result.append(4)
        assert raw == [1, 2, 3]


class TestSerializationDoesNotShadowKeys(unittest.TestCase):
    """The new methods take precedence over dict keys of the same name.

    Same convention as `.value`, `.keys`, `.items`, `.values`: users with a
    literal "json"/"dict"/"list" key must reach it via bracket access.
    """

    def test_methods_win_over_keys(self):
        c = Chain({"json": "x", "dict": "y", "list": "z"})
        assert callable(c.json)
        assert callable(c.dict)
        assert callable(c.list)
        # Bracket access still reaches the underlying entries.
        assert c["json"] == "x"
        assert c["dict"] == "y"
        assert c["list"] == "z"
