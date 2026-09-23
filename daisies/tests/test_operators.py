import unittest

from daisies import Chain


class TestNavigation(unittest.TestCase):

    def test_add_number(self):
        assert Chain(1) + 1 == 2
        assert Chain(1) + 1.1 == 2.1
        assert Chain(1.1) + 1 == 2.1
        assert Chain(1.1) + 1.1 == 2.2
        assert Chain(None) + 10 == 10

    def test_add_string(self):
        assert Chain("hello") + " world" == "hello world"
        assert Chain("hello") + " " + Chain("world") == "hello world"

    def test_add_list(self):
        assert Chain([1, 2, 3]) + [4, 5, 6] == [1, 2, 3, 4, 5, 6]
        assert Chain([1, 2, 3]) + Chain([4, 5, 6]) == [1, 2, 3, 4, 5, 6]

    def test_subtract_number(self):
        assert Chain(1) - 1 == 0
        assert Chain(0) - 1 == -1
        assert Chain(2) - 1 == 1
        assert Chain(1.1) - 1.1 == 0
        assert Chain(10) - Chain(5) == 5
        assert Chain(0) - Chain(10) == -10
        assert Chain(None) - 10 == -10

    def test_multiply_number(self):
        assert Chain(1) * 1 == 1
        assert Chain(1) * 2 == 2
        assert Chain(2) * 2 == 4
        assert Chain(5) * 10 == 50
        assert Chain(5) * 0 == 0
        assert Chain(5) * -1 == -5
        assert Chain(5) * Chain(10) == 50

    def test_divide_number(self):
        assert Chain(1) / 1 == 1
        assert Chain(2) / 1 == 2
        assert Chain(2) / 2 == 1
        assert Chain(10) / 5 == 2
        assert Chain(5) / 10 == 0.5
        assert Chain(5) / 0 == 0
        assert Chain(5) / -1 == -5
        assert Chain(5) / Chain(10) == 0.5

        # Yes Chain lets you divide by 0
        assert Chain(10) / 0 == 0
        assert Chain(10) / Chain(0) == 0

    def test_modulo_number(self):
        assert Chain(1) % 1 == 0
        assert Chain(2) % 1 == 0
        assert Chain(2) % 2 == 0
        assert Chain(10) % 5 == 0
        assert Chain(5) % 10 == 5
        assert Chain(5) % 0 == 0
        assert Chain(5) % -1 == 0
        assert Chain(5) % Chain(10) == 5

    def test_power_number(self):
        assert Chain(1) ** 1 == 1
        assert Chain(2) ** 1 == 2
        assert Chain(2) ** 2 == 4
        assert Chain(10) ** 5 == 100000
        assert Chain(5) ** 0 == 1
        assert Chain(5) ** -1 == 0.2
        assert Chain(5) ** Chain(10) == 9765625
        assert Chain(None) ** 10 == 0

    def test_floor_div(self):
        assert Chain(1) // 1 == 1
        assert Chain(2) // 1 == 2
        assert Chain(2) // 2 == 1
        assert Chain(17) // 5 == 3
        assert Chain(5) // 10 == 0
        assert Chain(4) // Chain(3) == 1
        assert Chain(5) // 0 == 0

    def test_missing_right_operand(self):
        # A missing field on the right reads as None, exactly as it does on
        # the left: `100 + data.missing` is 100, so `data.price + data.missing`
        # is too, rather than `100 + None` raising TypeError.
        data = Chain({"price": 100, "discount": 3})
        assert data.price + data.missing == 100
        assert data.price - data.missing == 100
        assert data.price**data.missing == 0
        assert data.price + None == 100
        assert data.price - None == 100
        assert Chain("hello") + Chain(None) == "hello"

    def test_missing_left_operand_minus_a_chain(self):
        data = Chain({"price": 100, "discount": 3})
        assert data.missing - data.discount == -3
        assert data.missing - data.nothing == None  # noqa: E711
        assert data.missing + data.nothing == None  # noqa: E711


class TestReflectedOperators(unittest.TestCase):
    """Operators where the Chain is on the right-hand side: `1 + Chain(2)`."""

    def test_radd_number(self):
        assert 1 + Chain(2) == 3
        assert 1.5 + Chain(2) == 3.5
        assert 5 + Chain(None) == 5

    def test_radd_string_and_list(self):
        assert "hello" + Chain(" world") == "hello world"
        assert [1, 2] + Chain([3, 4]) == [1, 2, 3, 4]

    def test_rsub_number(self):
        assert 10 - Chain(3) == 7
        assert 5 - Chain(None) == 5
        assert 0 - Chain(5) == -5

    def test_rmul_number(self):
        assert 3 * Chain(4) == 12
        assert 0 * Chain(5) == 0
        assert 5 * Chain(None) == 0
        assert "a" * Chain(3) == "aaa"
        assert [1] * Chain(3) == [1, 1, 1]

    def test_rtruediv_number(self):
        assert 10 / Chain(2) == 5
        assert 10 / Chain(0) == 0
        assert 10 / Chain(None) == 0

    def test_rfloordiv_number(self):
        assert 10 // Chain(3) == 3
        assert 10 // Chain(0) == 0
        assert 10 // Chain(None) == 0

    def test_rmod_number(self):
        assert 10 % Chain(3) == 1
        assert 10 % Chain(0) == 0
        assert 10 % Chain(None) == 0

    def test_rpow_number(self):
        assert 2 ** Chain(10) == 1024
        assert 5 ** Chain(None) == 0
