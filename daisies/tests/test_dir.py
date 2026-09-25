import rlcompleter
import unittest

from daisies import Chain


class Account:
    def __init__(self):
        self.owner = "Ada"
        self.balance = 10


class Row:
    # A partial mapping: items() and nothing else, so it has no keys().
    def items(self):
        return {"a": 1}.items()


class Hostile:
    def __dir__(self):
        raise RuntimeError("no introspection for you")


class TestDir(unittest.TestCase):
    """dir() lists what dotted navigation can reach, so REPLs can complete it."""

    def test_dict_keys_are_listed(self):
        names = dir(Chain({"user": {"name": "Ada", "age": 36}}).user)
        assert "name" in names
        assert "age" in names

    def test_chain_methods_are_still_listed(self):
        names = dir(Chain({"user": {"name": "Ada"}}).user)
        for method in ("value", "tree", "trace", "fallback", "json"):
            assert method in names

    def test_keys_the_dot_cannot_spell_are_left_out(self):
        names = dir(Chain({"jeffrey-epstein": 1, "123": 2, "class": 3, 7: 4, "ok": 5}))
        assert "jeffrey-epstein" not in names
        assert "123" not in names
        assert "class" not in names
        assert 7 not in names
        assert "ok" in names

    def test_dict_methods_are_not_offered_as_fields(self):
        # A dict's own methods aren't reachable as fields (except the view
        # proxies, which Chain defines behaviour for anyway).
        assert "setdefault" not in dir(Chain({"a": 1}))

    def test_plain_object_attributes_are_listed(self):
        names = dir(Chain({"account": Account()}).account)
        assert "owner" in names
        assert "balance" in names

    def test_string_methods_are_listed(self):
        assert "upper" in dir(Chain({"name": "Ada"}).name)

    def test_missing_and_none_add_nothing(self):
        bare = set(dir(Chain(None)))
        assert set(dir(Chain({}).nope)) == bare
        assert set(dir(Chain({"a": None}).a)) == bare
        # Nothing from NoneType leaks in.
        assert "__bool__" in bare

    def test_partial_mapping_does_not_raise(self):
        assert "value" in dir(Chain(Row()))

    def test_object_whose_dir_raises_does_not_raise(self):
        assert "value" in dir(Chain(Hostile()))

    def test_dir_does_not_navigate_or_notify(self):
        import daisies

        seen = []
        with daisies.on_missing(seen.append):
            dir(Chain({}).nope)
        assert seen == ["nope"]

    def test_rlcompleter_completes_wrapped_keys(self):
        data = Chain({"user": {"name": "Ada", "nationality": "UK"}, "jeffrey-epstein": 1})
        completer = rlcompleter.Completer({"data": data})
        matches = completer.attr_matches("data.user.na")
        assert {m.rstrip("(") for m in matches} == {"data.user.name", "data.user.nationality"}
        assert not any("epstein" in m for m in completer.attr_matches("data.je"))
