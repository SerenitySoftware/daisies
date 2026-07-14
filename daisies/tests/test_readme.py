import unittest

from daisies import Chain


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
        assert data.quantity**3 == 125
        # Note: README says `data.missing / 0` returns None, but the
        # implementation (and existing tests) returns 0. This documents
        # the actual behavior — the README needs a small correction.
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
        assert data.this.is_missing()

    def test_typed_defaults_with_value(self):
        data = Chain({"user": {"role": None, "age": "30"}})
        assert data.user.role.value(default="guest") == "guest"
        assert data.user.missing.value(default="n/a") == "n/a"
        assert data.user.age.value(int, default=0) == 30
        assert data.user.missing.value(int, default=0) == 0
        assert data.user.role.value(int, default=-1) == -1

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
