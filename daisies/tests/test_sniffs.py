import unittest

from daisies import sniff


class TestSniffs(unittest.TestCase):

    def test_isdictlike(self):
        assert sniff.isdictlike({}) is True
        assert sniff.isdictlike([]) is False
        assert sniff.isdictlike(set()) is False
        assert sniff.isdictlike(1) is False
        assert sniff.isdictlike("hello") is False

    def test_isdictlike_wants_items_to_be_a_method(self):
        # A plain object whose *data attribute* happens to be named `items` —
        # a cart, an order, a paginated response — is not a mapping.
        class Cart:
            def __init__(self):
                self.items = [{"sku": "A1"}]

        assert sniff.isdictlike(Cart()) is False

        # A duck-typed mapping, which is what the `items` check is there for,
        # still counts even though it isn't a Mapping subclass.
        class Row:
            def items(self):
                return [("a", 1)]

        assert Row().items() == [("a", 1)]
        assert sniff.isdictlike(Row()) is True

    def test_islistlike_follows_the_same_rule(self):
        # An iterable object with an `items` data attribute used to read as a
        # dict, so it was neither list-like nor nestable.
        class Page:
            def __init__(self):
                self.items = [1, 2]

            def __iter__(self):
                return iter(self.items)

        assert list(Page()) == [1, 2]
        assert sniff.islistlike(Page()) is True
        assert sniff.isnestable(Page()) is True

    def test_islistlike(self):
        assert sniff.islistlike([]) is True
        assert sniff.islistlike(set()) is True
        assert sniff.islistlike({}) is False
        assert sniff.islistlike(1) is False
        assert sniff.islistlike("hello") is False

    def test_isiterable(self):
        assert sniff.isiterable([]) is True
        assert sniff.isiterable(set()) is True
        assert sniff.isiterable({}) is True
        assert sniff.isiterable(1) is False
        assert sniff.isiterable("hello") is True

    def test_isnestable(self):
        assert sniff.isnestable([]) is True
        assert sniff.isnestable(set()) is True
        assert sniff.isnestable({}) is True
        assert sniff.isnestable(1) is False
        assert sniff.isnestable("hello") is False
