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


class TestValueCoercionNeverRaises(unittest.TestCase):
    """Every way a coercion can reject the value falls back instead of raising.

    `ValueError`/`TypeError` are only two of the families: `Decimal("abc")`
    raises `decimal.InvalidOperation`, an `ArithmeticError`.
    """

    def test_decimal_conversion_failure_falls_back(self):
        assert Chain({"amt": "abc"}).amt.value(Decimal, default=Decimal("0")) == Decimal("0")
        assert Chain("abc").value(Decimal) is None

    def test_overflow_falls_back(self):
        assert Chain(float("inf")).value(int, default=0) == 0

    def test_zero_division_falls_back(self):
        assert Chain(0).value(lambda v: 100 / v, default=-1) == -1

    def test_lookup_failure_falls_back(self):
        assert Chain({"a": 1}).value(lambda v: v["b"], default="none") == "none"
        assert Chain([]).value(lambda v: v[0], default="none") == "none"

    def test_attribute_failure_falls_back(self):
        # A date-shaped coercion applied to the string the vendor actually sent.
        assert Chain("2026-09-16").value(lambda v: v.isoformat(), default="n/a") == "n/a"

    def test_bug_in_coercion_callable_still_surfaces(self):
        # Absorbing a wrong-shaped value is the promise; hiding a broken
        # callable is not. A programming error propagates as usual.
        def broken(_value):
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            Chain("42").value(broken, default=0)


class TestValueRejectsNonCallableType(unittest.TestCase):
    """A positional default — `.value("guest")` — is a bug, not a shape the data arrived in.

    `"guest"(wrapped)` raises `TypeError`, which `_COERCION_FAILURES` would
    otherwise swallow into the implicit `None` default, losing a present value
    and never applying the intended default. Refuse it up front instead.
    """

    def assert_rejects(self, chain, type_):
        with self.assertRaises(TypeError) as caught:
            chain.value(type_)
        message = str(caught.exception)
        assert message == (
            f".value() takes a callable to coerce with, got {type_!r}; "
            f"to supply a default write .value(default={type_!r})"
        )

    def test_string_on_present_value_raises(self):
        self.assert_rejects(Chain({"user": {"name": "Ada"}}).user.name, "Unknown")

    def test_int_on_present_value_raises(self):
        self.assert_rejects(Chain({"user": {"age": 30}}).user.age, 0)

    def test_string_and_int_on_none_wrapped_value_raise(self):
        self.assert_rejects(Chain({"role": None}).role, "guest")
        self.assert_rejects(Chain(None), 0)

    def test_string_and_int_on_missing_node_raise(self):
        # A missing node would otherwise make the slip look like a legitimate None.
        self.assert_rejects(Chain({"user": {}}).user.missing, "guest")
        self.assert_rejects(Chain({"user": {}}).user.missing, 0)

    def test_raises_even_with_an_explicit_default(self):
        with self.assertRaises(TypeError):
            Chain({"name": "Ada"}).name.value("Unknown", default="x")

    def test_raises_before_strict_mode_reports_the_miss(self):
        # The calling code's bug outranks the data's gap.
        with self.assertRaises(TypeError):
            Chain({"user": {}}, strict=True).user.missing.value("guest")

    def test_keyword_default_and_callables_still_work(self):
        data = Chain({"user": {"name": "Ada", "age": "30", "role": None}})
        assert data.user.role.value(default="guest") == "guest"
        assert data.user.missing.value(default="guest") == "guest"
        assert data.user.name.value() == "Ada"
        assert data.user.age.value(int) == 30
        assert data.user.age.value(int, default=0) == 30
        assert data.user.age.value(Decimal) == Decimal("30")
        assert data.user.age.value(str.upper) == "30"
        assert data.user.name.value(lambda v: v.lower()) == "ada"
        assert data.user.missing.value(int, default=0) == 0
        # A class is callable; a bound method is callable; None means "no coercion".
        assert data.user.name.value(None) == "Ada"


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
