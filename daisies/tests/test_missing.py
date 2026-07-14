import copy
import pickle
import unittest

from daisies import Chain


class TestMissingPredicates(unittest.TestCase):
    def test_resolved_values_exist_even_when_falsy_or_none(self):
        data = Chain(
            {
                "none": None,
                "zero": 0,
                "false": False,
                "empty_string": "",
                "empty_list": [],
                "empty_dict": {},
            }
        )

        for node in (
            data.none,
            data.zero,
            data.false,
            data.empty_string,
            data.empty_list,
            data.empty_dict,
        ):
            assert node.exists()
            assert not node.is_missing()

        assert Chain(None).exists()
        assert not Chain(None).is_missing()

    def test_failed_navigation_is_missing_and_stays_missing(self):
        data = Chain({"items": [None]})

        for node in (
            data.absent,
            data.absent.deeply.nested,
            data.items[1],
            data.items[0].nested,
            Chain("value").absent,
        ):
            assert not node.exists()
            assert node.is_missing()

    def test_missing_keeps_its_existing_public_none_behavior(self):
        missing = Chain({}).absent

        assert missing() is None
        assert missing.value() is None
        assert missing.value(default="fallback") == "fallback"
        assert missing == None
        assert not missing
        assert repr(missing) == "None"
        assert missing.json() == "null"

    def test_present_none_and_missing_are_distinct_through_item_access(self):
        data = Chain({"present": None})

        assert data["present"].exists()
        assert data["absent"].is_missing()

    def test_missing_state_survives_copy_and_pickle(self):
        missing = Chain({}).absent

        for restored in (
            copy.copy(missing),
            copy.deepcopy(missing),
            pickle.loads(pickle.dumps(missing)),
        ):
            assert restored.is_missing()
            assert restored() is None


class TestFallback(unittest.TestCase):
    def test_resolved_value_wins_and_preserves_the_chain(self):
        data = Chain({"value": "primary", "none": None, "zero": 0})

        for node in (data["value"], data.none, data.zero):
            assert node.fallback("backup") is node

        assert data["value"].fallback("backup") == "primary"
        assert data.none.fallback("backup").value() is None
        assert data.zero.fallback(99) == 0

    def test_missing_node_uses_plain_fallback_and_stays_wrapped(self):
        result = Chain({}).missing.fallback({"profile": {"name": "Ada"}})

        assert isinstance(result, Chain)
        assert result.profile.name == "Ada"

    def test_missing_node_uses_an_existing_fallback_chain(self):
        data = Chain({"contact": {"email": "ada@example.com"}})
        backup = data.contact.email

        assert data.user.email.fallback(backup) is backup
        assert data.user.email.fallback(backup) == "ada@example.com"

    def test_missing_fallback_can_continue_to_another_fallback(self):
        data = Chain({})

        result = data.primary.fallback(data.secondary).fallback("default")

        assert result == "default"
        assert result.exists()

    def test_explicit_none_fallback_becomes_a_resolved_value(self):
        result = Chain({}).missing.fallback(None)

        assert result.exists()
        assert result.value() is None
