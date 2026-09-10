import copy
import pickle
import unittest

from daisies import Chain


class TestTracePath(unittest.TestCase):
    def test_root_has_walked_nowhere(self):
        assert Chain({"user": {}}).trace() == "<root>: resolved"

    def test_resolved_path_reports_the_steps_it_walked(self):
        data = Chain({"user": {"address": {"city": "Wonderland"}}})

        assert data.user.trace() == "user: resolved"
        assert data.user.address.city.trace() == "user.address.city: resolved"

    def test_item_access_renders_as_brackets(self):
        data = Chain({"user": {"name": "Ada"}, "tags": ["red", "blue"]})

        assert data["user"]["name"].trace() == "['user']['name']: resolved"
        assert data.tags[1].trace() == "tags[1]: resolved"

    def test_attribute_and_index_steps_mix_the_way_you_wrote_them(self):
        data = Chain({"users": [{"name": "Ada"}]})

        assert data.users[0].name.trace() == "users[0].name: resolved"

    def test_iterating_records_each_item_index(self):
        data = Chain({"users": [{"name": "Ada"}, {"name": "Bob"}]})

        traces = [user.name.trace() for user in data.users]

        assert traces == ["users[0].name: resolved", "users[1].name: resolved"]

    def test_attribute_navigation_onto_a_plain_object(self):
        class Account:
            owner = "Ada"

        assert Chain({"account": Account()}).account.owner.trace() == "account.owner: resolved"


class TestTraceExplainsAMiss(unittest.TestCase):
    def test_a_miss_on_the_final_hop_says_so_without_repeating_itself(self):
        data = Chain({"user": {"name": "Ada"}})

        assert data.user.address.trace() == "user.address: missing"

    def test_a_miss_mid_path_names_the_hop_that_failed(self):
        data = Chain({"user": {}})

        # `user` resolved and `city` was never reached — `address` is to blame.
        assert data.user.address.city.trace() == "user.address.city: missing at user.address"

    def test_the_first_failing_hop_wins_however_deep_navigation_goes(self):
        data = Chain({})

        assert data.account.owner.email.domain.trace() == "account.owner.email.domain: missing at account"

    def test_a_missing_index_is_named_like_an_index(self):
        data = Chain({"tags": ["red"]})

        assert data.tags[7].trace() == "tags[7]: missing"
        assert data.tags[7].label.trace() == "tags[7].label: missing at tags[7]"

    def test_a_missing_key_is_named_like_a_key(self):
        data = Chain({"user": {}})

        assert data["user"]["phone"].trace() == "['user']['phone']: missing"

    def test_navigating_off_a_scalar_blames_that_hop(self):
        data = Chain({"name": "Ada"})

        assert data.name.city.trace() == "name.city: missing"


class TestTraceKeepsMissingApartFromNone(unittest.TestCase):
    def test_an_explicit_none_is_resolved_not_missing(self):
        data = Chain({"user": {"nickname": None}})

        assert data.user.nickname.trace() == "user.nickname: resolved (None)"
        assert data.user.absent.trace() == "user.absent: missing"

    def test_present_but_falsy_values_are_plain_resolved(self):
        data = Chain({"count": 0, "label": "", "tags": [], "flag": False})

        assert data.count.trace() == "count: resolved"
        assert data.label.trace() == "label: resolved"
        assert data.tags.trace() == "tags: resolved"
        assert data.flag.trace() == "flag: resolved"

    def test_a_node_wrapping_none_at_the_root_is_resolved(self):
        assert Chain(None).trace() == "<root>: resolved (None)"


class TestTraceLeavesNavigationAlone(unittest.TestCase):
    def test_values_and_missing_behavior_are_untouched(self):
        data = Chain({"user": {"name": "Ada", "nickname": None}})

        assert data.user.name == "Ada"
        assert data.user.address.city() is None
        assert data.user.nickname.exists()
        assert data.user.address.is_missing()
        assert data.user.address.fallback("elsewhere") == "elsewhere"

    def test_the_dict_view_proxies_still_resolve(self):
        data = Chain({"user": {"theme": "dark"}})

        assert data.user.keys() == ["theme"]
        assert data.user.keys.trace() == "user.keys: resolved"
        # Off a non-dict the proxy stays null-tolerant, so it still resolved.
        assert data.user.theme.keys() == []
        assert data.missing.keys.trace() == "missing.keys: missing at missing"

    def test_a_data_key_named_like_a_proxy_still_wins(self):
        data = Chain({"items": [{"sku": "A1"}]})

        assert data.items[0].sku == "A1"
        assert data.items[0].sku.trace() == "items[0].sku: resolved"

    def test_a_trace_survives_copy_and_pickle(self):
        missing = Chain({"user": {}}).user.address.city

        for restored in (
            copy.copy(missing),
            copy.deepcopy(missing),
            pickle.loads(pickle.dumps(missing)),
        ):
            assert restored.trace() == "user.address.city: missing at user.address"

    def test_a_fallback_value_traces_as_a_fresh_root(self):
        # The fallback did not come from navigation, so it has no path to
        # report — claiming the original path resolved would be a lie.
        assert Chain({}).user.fallback("anonymous").trace() == "<root>: resolved"
