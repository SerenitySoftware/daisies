from decimal import Decimal
import unittest

from daisies import Chain


class TestValueBare(unittest.TestCase):
    """`.value()` with no arguments returns the wrapped value, or None when missing."""

    def test_returns_wrapped_scalar(self):
        assert Chain(42).value() == 42
        assert Chain("hello").value() == "hello"
        assert Chain(True).value() is True
        assert Chain(False).value() is False

    def test_returns_wrapped_container(self):
        assert Chain([1, 2, 3]).value() == [1, 2, 3]
        assert Chain({"a": 1}).value() == {"a": 1}

    def test_returns_none_for_missing_key(self):
        assert Chain({"a": 1}).missing.value() is None

    def test_returns_none_for_none_wrapped(self):
        assert Chain(None).value() is None

    def test_does_not_invoke_callable(self):
        # `.value()` is a terminal "give me the typed value" call — unlike `()`,
        # it should not invoke a callable wrapped value.
        calls = []

        def sentinel():
            calls.append(1)
            return "called"

        assert Chain(sentinel).value() is sentinel
        assert calls == []
        # Sanity check: the function does run when invoked directly.
        sentinel()
        assert calls == [1]


class TestValueWithDefault(unittest.TestCase):
    """`.value(default=X)` returns X when the wrapped value is None."""

    def test_default_used_when_missing(self):
        assert Chain({"a": 1}).missing.value(default="fallback") == "fallback"

    def test_default_used_when_wrapped_is_none(self):
        assert Chain(None).value(default="fallback") == "fallback"

    def test_default_ignored_when_value_present(self):
        assert Chain("real").value(default="fallback") == "real"

    def test_default_ignored_for_falsy_but_present_values(self):
        # Empty string, zero, False are all valid values — not "missing".
        assert Chain("").value(default="fallback") == ""
        assert Chain(0).value(default=99) == 0
        assert Chain(False).value(default=True) is False
        assert Chain([]).value(default=[1]) == []

    def test_default_can_be_none_explicitly(self):
        assert Chain(None).value(default=None) is None


class TestValueWithCoercion(unittest.TestCase):
    """`.value(type_)` coerces the wrapped value through the callable."""

    def test_int_coercion(self):
        assert Chain("42").value(int) == 42
        assert Chain(42.7).value(int) == 42

    def test_float_coercion(self):
        assert Chain("3.14").value(float) == 3.14
        assert Chain(7).value(float) == 7.0

    def test_str_coercion(self):
        assert Chain(42).value(str) == "42"

    def test_decimal_coercion(self):
        assert Chain("1.5").value(Decimal) == Decimal("1.5")

    def test_custom_callable_coercion(self):
        assert Chain("hello").value(str.upper) == "HELLO"
        assert Chain([1, 2, 3]).value(len) == 3

    def test_coercion_returns_none_for_missing(self):
        assert Chain({"a": 1}).missing.value(int) is None

    def test_coercion_returns_none_for_none_wrapped(self):
        assert Chain(None).value(int) is None

    def test_coercion_failure_returns_none_without_default(self):
        # Library philosophy: never raise — failed coercion falls back rather
        # than propagating the ValueError/TypeError.
        assert Chain("not a number").value(int) is None
        assert Chain("not a float").value(float) is None


class TestValueWithCoercionAndDefault(unittest.TestCase):
    """`.value(type_, default=X)` coerces, falling back to X on missing or coercion failure."""

    def test_default_used_when_missing(self):
        assert Chain({"a": 1}).missing.value(int, default=0) == 0

    def test_default_used_when_wrapped_is_none(self):
        assert Chain(None).value(int, default=-1) == -1

    def test_default_used_when_coercion_fails(self):
        assert Chain("abc").value(int, default=0) == 0
        assert Chain("xyz").value(float, default=1.5) == 1.5

    def test_coercion_succeeds_when_value_is_convertible(self):
        assert Chain("42").value(int, default=0) == 42

    def test_typed_default_with_real_navigation(self):
        # The motivating use case from the TODO: replace `or "default"` chains.
        data = Chain({"user": {"role": None, "age": "30"}})
        assert data.user.role.value(default="guest") == "guest"
        assert data.user.age.value(int, default=0) == 30
        assert data.user.missing.value(default="n/a") == "n/a"


class TestValueDoesNotShadowDictAccess(unittest.TestCase):
    """The new `.value` method takes precedence over a dict's "value" key.

    Users with a literal "value" key must use bracket access — same convention
    that already applies to "keys", "items", and "values".
    """

    def test_value_method_wins_over_value_key(self):
        c = Chain({"value": "from key"})
        # `.value` resolves to the method, not the dict entry.
        assert callable(c.value)
        # Bracket access still reaches the underlying entry.
        assert c["value"] == "from key"
