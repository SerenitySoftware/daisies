from collections import UserDict
from types import MappingProxyType

import pytest

from daisies import Chain, MissingPathError, on_missing
from daisies.sniff import isdictlike


class Duck:
    """The required read protocol, without Mapping, iteration or values()."""

    def __init__(self, data):
        self.data = data

    def get(self, key, default=None):
        return self.data.get(key, default)

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def __getitem__(self, key):
        return self.data[key]

    def __len__(self):
        return len(self.data)


class Order:
    total = 42
    keys = ["real field"]
    values = {"city": "Austin"}

    def items(self):
        # Classification, dict conversion and tree inspection must not call it.
        raise AssertionError("ordinary items method was called")

    def __repr__(self):
        return "Order()"


@pytest.mark.parametrize("factory", [dict, UserDict, MappingProxyType, Duck])
def test_full_mappings_keep_navigation_conversion_tree_and_views(factory):
    raw = {"user": factory({"name": "Ada", "nickname": None})}
    data = Chain(factory(raw), strict=True)
    assert isdictlike(data.value())
    assert data.user.name.value() == "Ada"
    assert data["user"]["name"].value() == "Ada"
    assert data.user.nickname.exists()
    assert data.user.nickname.trace() == "user.nickname: resolved (None)"
    assert data.user.dict() == {"name": "Ada", "nickname": None}
    assert data.user.keys() == ["name", "nickname"]
    assert data.user.items() == [("name", "Ada"), ("nickname", None)]
    assert data.user.values() == ["Ada", None]
    assert data.user.pluck("name", "absent").dict() == {"name": "Ada"}
    assert data.user.tree() == "dict\n├─ name: str = 'Ada'\n└─ nickname: None"
    assert data.user.tree(max_depth=0) == "dict {…} (2 keys)"
    assert Chain(factory({})).tree() == "dict (empty)"
    assert data.user.absent.child.trace() == "user.absent.child: missing at user.absent"
    with pytest.raises(MissingPathError, match="user.absent: missing"):
        data.user.absent.value()


def test_items_only_object_keeps_real_fields_methods_and_missing_paths():
    seen = []
    with on_missing(seen.append):
        order = Chain({"order": Order()}, strict=True).order
        assert order.total.value() == 42
        assert order.keys.list() == ["real field"]
        assert order.values.city.value() == "Austin"
        assert callable(order.items.value())
        assert order.items.trace() == "order.items: resolved"
        assert order.dict() == {}
        assert order.pluck("total").dict() == {}
        assert order.tree() == "Order = Order()"
        assert "total" in dir(order)
        missing = order.absent.child
        assert missing.trace() == "order.absent.child: missing at order.absent"
        with pytest.raises(MissingPathError, match="order.absent.child: missing at order.absent"):
            missing.value()
    assert seen == ["order.absent"]
    assert Chain(Order()).absent.value() is None
    assert Chain(Order()).absent.items() == []
    with pytest.raises(AssertionError, match="ordinary items method was called"):
        Chain(Order()).items()


@pytest.mark.parametrize("member", ["get", "keys", "items", "__getitem__", "__len__"])
@pytest.mark.parametrize("value", [None, 42, []])
def test_noncallable_protocol_member_leaves_object_ordinary(member, value):
    partial = type("Partial", (Duck,), {member: value})({"hidden": 1})
    assert not isdictlike(partial)
    assert Chain(partial).data.hidden.value() == 1
    assert Chain(partial).dict() == {}
    assert Chain(partial).tree().startswith("Partial = ")


@pytest.mark.parametrize("member", ["get", "keys", "items", "__getitem__", "__len__"])
def test_absent_protocol_member_leaves_object_ordinary(member):
    members = {name: getattr(Duck, name) for name in ("get", "keys", "items", "__getitem__", "__len__")}
    del members[member]
    partial = type("Partial", (), members)()
    partial.data = {"hidden": 1}
    assert not isdictlike(partial)
    assert Chain(partial).data.hidden.value() == 1
    assert Chain(partial).dict() == {}


@pytest.mark.parametrize("error", [AttributeError, RuntimeError])
@pytest.mark.parametrize("member", ["get", "keys", "items"])
def test_unreadable_protocol_property_does_not_break_other_fields(member, error):
    def broken(self):
        raise error("unavailable")

    partial = type("Partial", (Duck,), {member: property(broken)})({"hidden": 1})
    assert not isdictlike(partial)
    assert Chain(partial).data.hidden.value() == 1
    assert Chain(partial).dict() == {}


def test_data_property_named_items_is_an_ordinary_field():
    class Page:
        @property
        def items(self):
            return [{"name": "Ada"}]

    assert not isdictlike(Page())
    assert Chain(Page()).items[0].name.value() == "Ada"


def test_callable_properties_can_supply_normal_protocol_methods():
    class PropertyDuck(Duck):
        get = property(lambda self: self.data.get)
        keys = property(lambda self: self.data.keys)
        items = property(lambda self: self.data.items)

    data = Chain(PropertyDuck({"name": "Ada"}))
    assert isdictlike(data.value())
    assert data.name.value() == "Ada"
    assert data.dict() == {"name": "Ada"}


def test_instance_only_special_methods_do_not_supply_python_protocol():
    class Pretender:
        get = {"name": "Ada"}.get
        keys = {"name": "Ada"}.keys
        items = {"name": "Ada"}.items

    obj = Pretender()
    obj.__getitem__ = {"name": "Ada"}.__getitem__
    obj.__len__ = lambda: 1
    assert not isdictlike(obj)
    assert Chain(obj).dict() == {}


def test_mapping_keys_named_like_views_still_win():
    data = Chain(Duck({"keys": [1], "items": {"name": "Ada"}, "values": None}))
    assert data.keys[0].value() == 1
    assert data.items.name.value() == "Ada"
    assert data.values.exists()
    assert data.values.value() is None


def test_callable_protocol_methods_are_not_run_during_classification():
    def broken(*args, **kwargs):
        raise RuntimeError("method bug")

    obj = type("BrokenDuck", (), dict.fromkeys(("get", "keys", "items", "__getitem__", "__len__"), broken))()
    assert isdictlike(obj)
    # Advertising the protocol cannot guarantee that arbitrary user methods work.
    with pytest.raises(RuntimeError, match="method bug"):
        Chain(obj).name


def test_iterable_items_only_object_keeps_existing_list_behavior():
    class Page(Order):
        def __iter__(self):
            return iter([{"name": "Ada"}])

    data = Chain(Page())
    assert not isdictlike(data.value())
    assert data.total.value() == 42
    assert data.dict() == {}
    assert data.list() == [{"name": "Ada"}]
    assert data.tree() == "list[1]\n└─ [0]: dict\n   └─ name: str = 'Ada'"


def test_mapping_subclasses_do_not_need_duck_inspection():
    class ReadOnly(UserDict):
        @property
        def items(self):
            raise RuntimeError("no items access")

    obj = ReadOnly({"name": "Ada"})
    assert isdictlike(obj)
    with pytest.raises(RuntimeError, match="no items access"):
        obj.items
