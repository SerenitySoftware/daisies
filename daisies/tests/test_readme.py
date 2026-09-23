import unittest
from collections import Counter
from decimal import Decimal

import daisies
from daisies import Chain, MissingPathError


class TestReadmeExamples(unittest.TestCase):
    """Every assertion below mirrors a claim in README.md.

    If you change README.md examples, change these alongside — they exist
    so the documentation can't silently drift away from the implementation.
    """

    def test_top_level_demo(self):
        raw = {
            "never": {"gonna": {"give": {"you": {"up": "never gonna let you down"}}}},
            "artists": [
                {"name": "Rick Astley", "genre": "Pop"},
                {"name": "Michael Jackson", "genre": "Pop"},
            ],
        }
        data = Chain(raw)
        assert data.never.gonna.give.you.up == "never gonna let you down"
        assert data.let.you.down() is None
        assert data.artists[0].name == "Rick Astley"
        assert data.artists[1].name == "Michael Jackson"
        assert data.artists[2].name() is None

    def test_scalar_values(self):
        data = Chain({"name": "John Doe", "age": 30, "is_active": True})
        assert data.name == "John Doe"
        assert data.age == 30
        assert data.is_active == True  # noqa: E712
        assert data.name.upper() == "JOHN DOE"
        assert data.age + 10 == 40

    def test_arithmetic(self):
        data = Chain({"price": 100, "quantity": 5})
        assert data.price * data.quantity == 500
        assert data.missing + 10 == 10
        assert data.price - data.missing == 100
        assert data.missing - data.price == -100
        assert data.quantity**3 == 125
        # Division by zero coerces to 0 rather than raising, as the README says.
        assert data.missing / 0 == 0

    def test_lists(self):
        data = Chain(
            {
                "names": ["Alice", "Bob", "Charlie"],
                "users": [{"name": "Alice"}, {"name": "Bob"}],
            }
        )
        assert data.names[0] == "Alice"
        assert data.names[50]() is None
        # Iterating yields Chains, so nested access keeps working in the loop.
        assert [user.name.value() for user in data.users] == ["Alice", "Bob"]

    def test_nested_dicts(self):
        data = Chain(
            {
                "user": {
                    "name": "Alice",
                    "address": {"city": "Wonderland", "country": "Fairyland"},
                }
            }
        )
        assert data.user.name == "Alice"
        assert data.user.address.city == "Wonderland"
        assert data.user.phone.number() is None

    def test_typed_defaults_with_value(self):
        data = Chain({"user": {"role": None, "age": "30"}})
        assert data.user.role.value(default="guest") == "guest"
        assert data.user.missing.value(default="n/a") == "n/a"
        assert data.user.age.value(int, default=0) == 30
        assert data.user.missing.value(int, default=0) == 0
        assert data.user.role.value(int, default=-1) == -1
        assert Chain({"amt": "n/a"}).amt.value(Decimal, default=Decimal("0")) == Decimal("0")

    def test_serialization_methods(self):
        data = Chain({"user": {"name": "Alice", "roles": ["admin", "editor"]}})
        assert data.user.json() == '{"name": "Alice", "roles": ["admin", "editor"]}'
        assert data.user.json(indent=2).startswith("{\n")
        assert data.user.dict() == {"name": "Alice", "roles": ["admin", "editor"]}
        assert data.user.roles.list() == ["admin", "editor"]
        # Never raises on missing or mismatched data.
        assert data.missing.json() == "null"
        assert data.missing.dict() == {}
        assert data.user.name.list() == []

    def test_json_stringifies_unserializable(self):
        from datetime import date

        assert Chain({"when": date(2026, 7, 9)}).json() == '{"when": "2026-07-09"}'

    def test_json_stringifies_unserializable_keys(self):
        # "That holds on either side of the colon."
        from datetime import date

        assert Chain({date(2026, 7, 9): 12}).json() == '{"2026-07-09": 12}'

    def test_dict_views(self):
        settings = Chain({"user": {"theme": "dark", "lang": "en"}})
        assert settings.user.keys() == ["theme", "lang"]
        assert settings.user.values() == ["dark", "en"]
        assert settings.user.items() == [("theme", "dark"), ("lang", "en")]
        assert settings.user.missing.keys() == []

    def test_exists_and_is_missing(self):
        data = Chain({"count": 0})
        assert data.count.exists() is True
        assert data.missing.exists() is False
        assert data.missing.is_missing() is True

        # A key the sender set literally to None is a value they sent, so it
        # exists; only a key that never arrived is missing. The README said the
        # opposite until 2026-09-18 — it was written before the missing
        # sentinel landed and nothing here contradicted it.
        nulled = Chain({"nickname": None})
        assert nulled.nickname.exists() is True
        assert nulled.nickname.is_missing() is False
        # ...while .value(default=...) still covers both, as the same section says.
        assert nulled.nickname.value(default="anon") == "anon"

    def test_tree_shape_inspector(self):
        data = Chain(
            {
                "user": {"name": "Ada", "age": 36},
                "roles": ["admin", "editor"],
            }
        )
        out = data.tree()
        assert out.startswith("dict")
        assert "├─ user: dict" in out
        assert "│  ├─ name: str = 'Ada'" in out
        assert "│  └─ age: int = 36" in out
        assert "└─ roles: list[2] of str (e.g. 'admin')" in out

    def test_trace_explains_an_empty_result(self):
        data = Chain({"user": {"name": "Alice"}})
        assert data.user.name.trace() == "user.name: resolved"
        assert data.user.address.trace() == "user.address: missing"
        assert data.user.address.city.trace() == "user.address.city: missing at user.address"

        data = Chain({"user": {"nickname": None}})
        assert data.user.nickname.trace() == "user.nickname: resolved (None)"
        assert data.user.absent.trace() == "user.absent: missing"

        data = Chain({"users": [{"name": "Ada"}, {"name": "Bob"}]})
        assert data.users[0].name.trace() == "users[0].name: resolved"
        assert data.users[1].email.trace() == "users[1].email: missing"

    def test_pluck_trims_a_payload(self):
        customer = Chain(
            {
                "id": 42,
                "email": "ada@example.com",
                "internal_notes": "do not share",
                "card_token": "tok_secret",
            }
        )
        assert customer.pluck("id", "email").dict() == {"id": 42, "email": "ada@example.com"}
        assert customer.pluck("id", "email").json() == '{"id": 42, "email": "ada@example.com"}'
        # Absent keys are left out; an explicit null is kept.
        assert customer.pluck("id", "nickname").dict() == {"id": 42}
        assert Chain({"nickname": None}).pluck("nickname").dict() == {"nickname": None}
        assert customer.missing.pluck("id").dict() == {}

    def test_identity_comparisons(self):
        data = Chain({"name": "John Doe", "age": 30, "is_active": True})
        # Wrapped values are not the raw values — `is` against True/None fails.
        assert (data.is_active is True) is False
        assert (data.missing.key is None) is False
        # Calling unwraps, so identity works.
        assert data.is_active() is True
        assert data.missing.key() is None

    def test_reserved_or_invalid_keys(self):
        data = Chain({"123": "Hello World!", "jeffrey-epstein": "Didn't kill himself"})
        assert data["123"] == "Hello World!"
        assert data["jeffrey-epstein"] == "Didn't kill himself"

    def test_brackets_are_as_forgiving_as_the_dots(self):
        weather = Chain({"current": {"wind": []}})
        assert weather.current["wind"]["speed_mph"]() is None
        assert weather.current["wind"]["speed_mph"].trace() == "current['wind']['speed_mph']: missing"


class TestEdgeCases(unittest.TestCase):
    """Behaviors that work but aren't covered elsewhere."""

    def test_custom_class_attribute_delegation(self):
        class Greeter:
            def __init__(self):
                self.greeting = "hi"

            def shout(self):
                return self.greeting.upper()

        c = Chain(Greeter())
        assert c.greeting == "hi"
        assert c.shout() == "HI"
        assert c.missing() is None

    def test_an_objects_own_items_attribute_wins_over_the_view(self):
        # README, dict views: "The same holds for a plain object: an order
        # whose `items` attribute holds its line items navigates to those
        # line items."
        class Order:
            def __init__(self):
                self.id = 41
                self.items = [{"sku": "A1"}, {"sku": "B2"}]

        order = Chain(Order())
        assert order.items[0].sku == "A1"
        assert order.id == 41
        # An object without such an attribute still gets the null-tolerant view.
        assert Chain(Order()).keys() == []

    def test_tuple_indexing(self):
        c = Chain((10, 20, 30))
        assert c[0] == 10
        assert c[2] == 30

    def test_negative_list_indexing(self):
        c = Chain([1, 2, 3])
        assert c[-1] == 3
        assert c[-2] == 2

    def test_non_string_dict_keys(self):
        c = Chain({1: "one", 2: "two"})
        assert c[1] == "one"
        assert c[2] == "two"

    def test_double_wrapping_still_navigates(self):
        # Wrapping a Chain currently nests rather than flattens, but operations
        # still work through the layers because Chain is callable/comparable.
        nested = Chain(Chain(5))
        assert nested == 5
        assert nested + 3 == 8


class TestReadmeStrictMode(unittest.TestCase):
    """Mirrors README.md -> Usage: Catching your own typos with strict mode."""

    def test_a_typo_raises_while_a_real_field_resolves(self):
        data = Chain({"user": {"email": "ada@example.com"}}, strict=True)

        assert data.user.email.value() == "ada@example.com"
        with self.assertRaises(MissingPathError) as caught:
            data.user.emial.value()
        assert str(caught.exception) == "user.emial: missing"

    def test_the_message_names_the_hop_that_failed(self):
        data = Chain({"user": {}}, strict=True)

        with self.assertRaises(MissingPathError) as caught:
            data.user.address.city.value()
        assert str(caught.exception) == "user.address.city: missing at user.address"

    def test_an_explicitly_handled_absence_is_left_alone(self):
        data = Chain({"user": {}}, strict=True)

        assert data.user.email.value(default="noreply@example.com") == "noreply@example.com"
        assert data.user.email.fallback("anonymous").value() == "anonymous"
        assert data.user.email.exists() is False
        assert data.user.email.is_missing() is True
        assert data.user.email.trace() == "user.email: missing"

    def test_the_context_manager_covers_a_chain_someone_else_wrapped(self):
        payload = Chain({"user": {}})

        with daisies.strict():
            with self.assertRaises(MissingPathError):
                payload.user.emial.value()
            # An explicitly tolerant chain opts back out of the region.
            assert Chain({"user": {}}, strict=False).user.emial.value() is None

        assert payload.user.emial.value() is None


class TestReadmeOnMissing(unittest.TestCase):
    """Mirrors README.md -> Usage: Watching for fields that disappear with on_missing()."""

    def test_a_failed_hop_reaches_the_observer(self):
        seen = []

        with daisies.on_missing(seen.append):
            Chain({"user": {"name": "Ada"}}).user.email.value()

        assert seen == ["user.email"]

    def test_misses_group_under_the_same_key_so_they_count(self):
        misses = Counter()

        with daisies.on_missing(lambda path: misses.update([path])):
            data = Chain({"users": [{"id": 1}, {"id": 2}]})
            for row in data.users:
                row.email.value()

        assert misses == Counter({"users[0].email": 1, "users[1].email": 1})

    def test_only_the_first_failure_in_a_chain_fires(self):
        seen = []

        with daisies.on_missing(seen.append):
            Chain({"user": {}}).user.address.city.value()

        assert seen == ["user.address"]

    def test_the_scoped_registration_example(self):
        seen = []

        with daisies.on_missing(seen.append):
            Chain({"user": {}}).user.email.value()

        assert seen == ["user.email"]
