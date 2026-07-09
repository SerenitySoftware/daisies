import unittest

from daisies import Chain


class TestIterables(unittest.TestCase):
    def test_dict_keys(self):
        wrapped = Chain({"key": "value", "nested": {"key": "value"}})
        assert list(wrapped.keys()) == ["key", "nested"]
        assert list(wrapped.nested.keys()) == ["key"]
        assert "key" in wrapped.keys()
        assert "nested" in wrapped
        assert "missing" not in wrapped

    def test_keys_values_items_return_plain_lists(self):
        wrapped = Chain({"a": 1, "b": 2})
        # Plain lists, not raw dict_keys/dict_values/dict_items views.
        assert wrapped.keys() == ["a", "b"]
        assert type(wrapped.keys()) is list
        assert wrapped.values() == [1, 2]
        assert type(wrapped.values()) is list
        assert wrapped.items() == [("a", 1), ("b", 2)]
        assert type(wrapped.items()) is list

    def test_keys_values_items_are_null_tolerant(self):
        # A missing node, or a non-dict value, yields [] rather than raising.
        assert Chain({"a": 1}).missing.keys() == []
        assert Chain(None).keys() == []
        assert Chain(None).values() == []
        assert Chain(None).items() == []
        assert Chain([1, 2, 3]).keys() == []
        assert Chain("hi").items() == []
        # Works several hops deep off an absent path.
        assert Chain({"user": {}}).user.settings.keys() == []

    def test_data_key_wins_over_proxy(self):
        # A field literally named items/keys/values still navigates as data;
        # reach the proxy via the method call on a dict without that key.
        assert Chain({"items": [55, 8, 59]}).items[1] == 8
        assert Chain({"keys": {"a": 1}}).keys.a == 1

    def test_lists(self):
        wrapped = Chain([1, 2, 3])
        assert wrapped[0] == 1
        assert wrapped[1] == 2
        assert wrapped[2] == 3
        assert 1 in wrapped
        assert 4 not in wrapped
        assert 1 in wrapped[0:2]

        assert sorted(wrapped, reverse=True) == [3, 2, 1]
        assert sorted(wrapped, reverse=False) == [1, 2, 3]
        assert sorted(wrapped[0:2], reverse=True) == [2, 1]
        assert sorted(wrapped[0:2], reverse=False) == [1, 2]

        for index, item in enumerate(wrapped):
            assert index + 1 == item

    def test_iteration_yields_wrapped_items(self):
        # Iterating keeps you in Chain-land, so navigation continues through a
        # loop without re-wrapping; missing fields inside still resolve to None.
        data = Chain({"users": [{"name": "Ada"}, {"name": "Bob"}, {}]})
        for item in data.users:
            assert isinstance(item, Chain)
        assert [user.name.value() for user in data.users] == ["Ada", "Bob", None]

    def test_iterated_scalars_compare_equal_to_raw(self):
        # Wrapped items compare equal to their raw values, so sorted/==/in keep
        # working unchanged after the wrapping fix.
        wrapped = Chain([3, 1, 2])
        assert [item for item in wrapped] == [3, 1, 2]
        assert sorted(wrapped) == [1, 2, 3]

    def test_sets(self):
        assert Chain(set()) == set()
        assert Chain({1, 2, 3}) == {1, 2, 3}
        assert 1 in Chain({1, 2, 3})

    def test_strings(self):
        wrapped = Chain("abcdefghijklmnopqrstuvwxyz")
        assert wrapped[0] == "a"
        assert wrapped[1] == "b"
        assert wrapped[0:5] == "abcde"

        assert "a" in wrapped
        assert "z" in wrapped
        assert "abc" in wrapped
        assert "xyz" in wrapped

    def test_generators(self):
        wrapped = Chain(range(5))

        for index, item in enumerate(wrapped):
            assert index == item

    def test_non_iterable(self):
        with self.assertRaises(TypeError):
            enumerate(Chain(1))

    def test_no_contains(self):
        self.assertFalse("x" in Chain(None))

    def test_no_len(self):
        self.assertEqual(len(Chain(None)), 0)
