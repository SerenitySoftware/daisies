import unittest

from daisies import Chain


class TestExistsAndMissing(unittest.TestCase):
    """`.exists()` / `.is_missing()` disambiguate absent from falsy."""

    def test_present_falsy_values_exist(self):
        # The whole point: a present-but-falsy value is not missing.
        data = Chain({"count": 0, "name": "", "items": [], "flag": False})
        assert data.count.exists() is True
        assert data.name.exists() is True
        assert data.items.exists() is True
        assert data.flag.exists() is True
        assert data.count.is_missing() is False

    def test_absent_keys_are_missing(self):
        data = Chain({"count": 0})
        assert data.nope.exists() is False
        assert data.nope.is_missing() is True
        # Distinguishes a genuine zero from an absent count.
        assert data.count.exists() and not data.nope.exists()

    def test_missing_nested_path(self):
        data = Chain({"user": {}})
        assert data.user.address.city.exists() is False
        assert data.user.address.city.is_missing() is True

    def test_none_valued_key_reads_as_missing(self):
        # Documented limitation: a key literally set to None can't be told
        # apart from an absent one, because a missing hop is itself None.
        data = Chain({"middle_name": None})
        assert data.middle_name.exists() is False
        assert data.middle_name.is_missing() is True

    def test_methods_win_over_keys(self):
        # Same convention as the other methods: a data key named "exists" is
        # shadowed by the method and reached via bracket access.
        data = Chain({"exists": "surprise"})
        assert callable(data.exists)
        assert data["exists"] == "surprise"
