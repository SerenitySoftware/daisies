import unittest

from daisies import Chain


class TestNavigation(unittest.TestCase):

    def test_raw_object(self):
        assert Chain(0) == 0
        assert Chain(False) == False
        assert Chain({"key": "value"}) == {"key": "value"}
        assert Chain([1, 2, 3]) == [1, 2, 3]

    def test_dict_access(self):
        assert Chain({"key": "value"}).key == "value"

    def test_dict_access_missing(self):
        assert Chain({"key": "value"}).missing() is None
        assert not Chain({"key": "value"}).missing

    def test_dict_access_nested(self):
        assert Chain({"nested": {"key": "value"}}).nested.key == "value"
        assert Chain({"nested": {"deeper": {"key": "value"}}}).nested.deeper == {"key": "value"}

    def test_dict_access_nested_missing(self):
        assert Chain({"nested": {"key": "value"}}).nested.missing() is None

    def test_list_access(self):
        assert Chain([1, 2, 3])[0] == 1
        assert Chain([1, 2, 3])[1] == 2
        assert Chain([1, 2, 3])[2] == 3

    def test_list_access_missing(self):
        assert Chain([1, 2, 3])[3]() is None

    def test_list_access_nested(self):
        assert Chain([{"key": "value"}])[0] == {"key": "value"}
        assert Chain({"items": [55, 8, 59]}).items[1] == 8
        assert Chain({"items": [{"hello": "world"}]}).items[0].hello == "world"

    def test_attribute_delegates_to_wrapped(self):
        assert Chain("hello").upper() == "HELLO"
        assert Chain("   hi   ").strip() == "hi"
        assert Chain([1, 2, 3]).index(2) == 1
        assert Chain({"name": "John"}).name.upper() == "JOHN"

    def test_object_with_an_items_attribute_still_navigates(self):
        # `items` is the most ordinary name a cart, order, or page object has,
        # and the dict-like sniff used to accept any object that merely *had*
        # the attribute — so every hop on one raised instead of navigating.
        class Cart:
            def __init__(self):
                self.id = 7
                self.items = [{"sku": "A1"}, {"sku": "B2"}]

        cart = Cart()
        assert Chain(cart).id == 7
        assert Chain(cart).missing() is None
        assert Chain({"cart": cart}).cart.id == 7
        # The field itself wins over the keys()/values()/items() proxy, the
        # same way a data key does on a dict.
        assert Chain(cart).items[1].sku == "B2"
        assert Chain(cart).items.list() == [{"sku": "A1"}, {"sku": "B2"}]

    def test_object_with_an_items_attribute_keeps_the_never_raise_promise(self):
        class Order:
            def __init__(self):
                self.items = ["widget"]

        order = Order()
        # Not dict-like, so `.dict()` answers with its documented empty dict…
        assert Chain(order).dict() == {}
        # …and `.tree()` describes it as the object it is rather than raising.
        assert Chain(order).tree().startswith("Order = <")

    def test_attribute_missing_on_wrapped(self):
        assert Chain("hello").nonexistent() is None
        assert Chain([1, 2, 3]).does_not_exist() is None

    def test_attribute_on_none_wrapped(self):
        assert Chain(None).anything() is None
        assert Chain(None).deeply.nested.path() is None

    def test_dunder_attributes_not_delegated(self):
        # Dunder lookups should fall through to AttributeError so Python's
        # protocols (pickle, copy, repr, etc.) work correctly instead of
        # being intercepted into Chain(None) and recursing.
        with self.assertRaises(AttributeError):
            Chain({"a": 1}).__nonexistent_dunder__

    def test_item_access_wrong_key_type(self):
        # Bracket lookup is the documented route for reserved and non-identifier
        # keys, so it has to absorb a wrong-shaped container the same way dotted
        # access does — the day the vendor sends a list where a dict was
        # promised, `data.users["name"]` must not raise.
        data = Chain({"users": [{"name": "Ada"}], "title": "hello"})
        assert data.users["name"]() is None
        assert data.title["name"]() is None
        assert data.users[1.5]() is None

    def test_item_access_unhashable_key(self):
        assert Chain({"a": 1})[["a"]]() is None

    def test_item_access_wrong_key_type_records_the_miss(self):
        data = Chain({"current": {"wind": []}})
        node = data.current["wind"]["speed_mph"]
        assert node.is_missing()
        assert node.trace() == "current['wind']['speed_mph']: missing"
