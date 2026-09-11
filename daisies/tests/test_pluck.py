import json
import unittest

from daisies import Chain


class TestPluck(unittest.TestCase):
    """`.pluck(*keys)` projects a mapping down to a whitelist of keys."""

    def test_returns_only_the_requested_keys(self):
        data = Chain({"id": 7, "email": "a@b.c", "secret": "shhh"})
        assert data.pluck("id", "email").dict() == {"id": 7, "email": "a@b.c"}

    def test_keeps_the_order_you_asked_for(self):
        data = Chain({"a": 1, "b": 2, "c": 3})
        assert list(data.pluck("c", "a").dict()) == ["c", "a"]

    def test_absent_keys_are_skipped_silently(self):
        data = Chain({"id": 7})
        assert data.pluck("id", "nope", "also_nope").dict() == {"id": 7}

    def test_every_key_absent_gives_an_empty_dict(self):
        assert Chain({"id": 7}).pluck("nope").dict() == {}

    def test_no_keys_gives_an_empty_dict(self):
        assert Chain({"id": 7}).pluck().dict() == {}

    def test_present_but_null_key_is_kept(self):
        # A key the source explicitly nulled is *there* — skipping it would
        # erase the difference between "sent as null" and "never sent".
        data = Chain({"nickname": None, "name": "Ada"})
        assert data.pluck("nickname", "missing").dict() == {"nickname": None}

    def test_falsy_values_are_kept(self):
        data = Chain({"zero": 0, "false": False, "empty": "", "none": None, "list": []})
        plucked = data.pluck("zero", "false", "empty", "none", "list").dict()
        assert plucked == {"zero": 0, "false": False, "empty": "", "none": None, "list": []}

    def test_duplicate_keys_appear_once(self):
        assert Chain({"a": 1}).pluck("a", "a").dict() == {"a": 1}

    def test_non_string_keys(self):
        assert Chain({1: "one", 2: "two"}).pluck(1).dict() == {1: "one"}

    def test_unhashable_key_is_skipped(self):
        # A list can never be a mapping key, so asking for one is a miss, not
        # a TypeError — navigation never raises at the caller.
        assert Chain({"a": 1}).pluck(["a"], "a").dict() == {"a": 1}


class TestPluckNullTolerance(unittest.TestCase):
    """Missing and non-mapping nodes pluck to an empty dict rather than raising."""

    def test_missing_node_plucks_empty(self):
        assert Chain({"a": 1}).missing.pluck("a").dict() == {}

    def test_deeply_missing_node_plucks_empty(self):
        assert Chain({"a": 1}).missing.deeply.nested.pluck("a").dict() == {}

    def test_none_plucks_empty(self):
        assert Chain(None).pluck("a").dict() == {}

    def test_non_mapping_values_pluck_empty(self):
        assert Chain([1, 2, 3]).pluck("a").dict() == {}
        assert Chain("hello").pluck("a").dict() == {}
        assert Chain(42).pluck("a").dict() == {}


class TestPluckComposes(unittest.TestCase):
    """The result stays wrapped, so it flows into the rest of the library."""

    def test_returns_a_chain(self):
        assert isinstance(Chain({"a": 1}).pluck("a"), Chain)

    def test_composes_with_json(self):
        data = Chain({"id": 7, "email": "a@b.c", "secret": "shhh"})
        assert json.loads(data.pluck("id", "email").json()) == {"id": 7, "email": "a@b.c"}

    def test_composes_with_navigation(self):
        data = Chain({"user": {"name": "Ada", "age": 36}})
        assert data.user.pluck("name").name == "Ada"
        assert data.user.pluck("name").age() is None

    def test_plucks_after_navigation(self):
        data = Chain({"user": {"name": "Ada", "age": 36, "token": "t"}})
        assert data.user.pluck("name", "age").dict() == {"name": "Ada", "age": 36}

    def test_result_exists_even_when_empty(self):
        # An empty projection is a real, resolved dict — not a failed lookup.
        assert Chain({"a": 1}).pluck("nope").exists()

    def test_keeps_dict_views_working(self):
        data = Chain({"a": 1, "b": 2, "c": 3})
        assert data.pluck("a", "b").keys() == ["a", "b"]

    def test_does_not_mutate_the_source(self):
        raw = {"a": 1, "b": 2}
        plucked = Chain(raw).pluck("a").dict()
        plucked["c"] = 3
        assert raw == {"a": 1, "b": 2}


class TestPluckTrace(unittest.TestCase):
    """Plucking is bookkeeping-friendly: `.trace()` still explains the path."""

    def test_trace_records_the_projection(self):
        data = Chain({"user": {"name": "Ada"}})
        assert data.user.pluck("name").trace() == "user.pluck('name'): resolved"

    def test_trace_still_names_the_hop_that_missed(self):
        data = Chain({"user": {}})
        assert data.user.address.pluck("city").trace() == "user.address.pluck('city'): missing at user.address"


class TestPluckDoesNotShadowKeys(unittest.TestCase):
    """Same convention as `.json`/`.dict`/`.list`: the method wins over a key."""

    def test_method_wins_over_key(self):
        c = Chain({"pluck": "x"})
        assert callable(c.pluck)
        assert c["pluck"] == "x"
