import unittest

from daisies import Chain, tree


class TestTreeLeaves(unittest.TestCase):
    """Scalar and empty-container roots render on a single line."""

    def test_none(self):
        assert Chain(None).tree() == "None"

    def test_int(self):
        assert Chain(5).tree() == "int = 5"

    def test_float(self):
        assert Chain(1.5).tree() == "float = 1.5"

    def test_str(self):
        assert Chain("hi").tree() == "str = 'hi'"

    def test_bool_is_not_int(self):
        # bool subclasses int; it must be labelled as bool, not int.
        assert Chain(True).tree() == "bool = True"
        assert Chain(False).tree() == "bool = False"

    def test_empty_dict(self):
        assert Chain({}).tree() == "dict (empty)"

    def test_empty_list(self):
        assert Chain([]).tree() == "list[0]"


class TestTreeStructure(unittest.TestCase):
    def test_nested_dict_matches_docstring(self):
        out = Chain({"user": {"name": "Ada", "age": 36}}).tree()
        assert out == "\n".join(
            [
                "dict",
                "└─ user: dict",
                "   ├─ name: str = 'Ada'",
                "   └─ age: int = 36",
            ]
        )

    def test_full_payload(self):
        payload = {
            "users": [
                {"name": "Ada", "age": 36, "email": None},
                {"name": "Bob", "age": 40, "email": "bob@example.com"},
            ],
            "meta": {"next": None, "count": 2},
            "tags": ["a", "b", "c"],
            "ok": True,
        }
        out = Chain(payload).tree()
        assert out == "\n".join(
            [
                "dict",
                "├─ users: list[2]",
                "│  └─ [0]: dict",
                "│     ├─ name: str = 'Ada'",
                "│     ├─ age: int = 36",
                "│     └─ email: None",
                "├─ meta: dict",
                "│  ├─ next: None",
                "│  └─ count: int = 2",
                "├─ tags: list[3] of str (e.g. 'a')",
                "└─ ok: bool = True",
            ]
        )

    def test_homogeneous_scalar_list_collapses_inline(self):
        assert Chain({"n": [1, 2, 3]}).tree() == "\n".join(["dict", "└─ n: list[3] of int (e.g. 1)"])

    def test_mixed_scalar_list_shows_representative(self):
        assert Chain({"m": [1, "a"]}).tree() == "\n".join(["dict", "└─ m: list[2]", "   └─ [0]: int = 1"])

    def test_list_of_dicts_shows_first_as_representative(self):
        out = Chain([{"id": 1}, {"id": 2}]).tree()
        assert out == "\n".join(["list[2]", "└─ [0]: dict", "   └─ id: int = 1"])


class TestTreeTruncation(unittest.TestCase):
    def test_max_depth_stops_recursing(self):
        out = Chain({"a": {"b": {"c": 1}}}).tree(max_depth=2)
        assert "b: dict {…} (1 keys)" in out
        assert "c: int = 1" not in out

    def test_max_depth_truncates_a_nested_list(self):
        out = Chain({"a": {"b": [{"x": 1}, {"y": 2}]}}).tree(max_depth=2)
        assert "b: list[2] [...]" in out
        assert "[0]:" not in out

    def test_max_items_caps_width(self):
        out = Chain({f"k{i}": i for i in range(5)}).tree(max_items=2)
        assert "k0: int = 0" in out
        assert "k1: int = 1" in out
        assert "… (+3 more)" in out
        assert "k2" not in out

    def test_long_string_sample_is_bounded(self):
        out = Chain({"s": "x" * 100}).tree()
        assert "…" in out
        # The sample is truncated well short of the full value.
        assert "x" * 60 not in out


class TestTreeNeverRaises(unittest.TestCase):
    def test_set_is_treated_as_a_list(self):
        # Sets are list-like but unordered; assert only the stable prefix.
        out = Chain({"s": {1, 2, 3}}).tree()
        assert out.startswith("dict\n└─ s: list[3] of int")

    def test_arbitrary_object(self):
        out = Chain(object()).tree()
        assert out.startswith("object = ")


class TestModuleLevelTree(unittest.TestCase):
    def test_tree_function_matches_method(self):
        data = {"a": 1, "b": {"c": 2}}
        assert tree(data) == Chain(data).tree()

    def test_tree_function_passes_options(self):
        data = {f"k{i}": i for i in range(5)}
        assert tree(data, max_items=2) == Chain(data).tree(max_items=2)
