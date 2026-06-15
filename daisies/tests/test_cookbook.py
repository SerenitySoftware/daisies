import unittest

from daisies import Chain, tree


class TestStripeWebhookRecipe(unittest.TestCase):
    """Mirrors docs/cookbook.md -> Parsing a Stripe webhook."""

    def setUp(self):
        self.raw_event = {
            "id": "evt_1NG8Du2eZvKYlo2C",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_a1b2c3",
                    "amount_total": 2000,
                    "currency": "usd",
                    "customer_details": {
                        "email": "buyer@example.com",
                        "name": None,
                    },
                    "metadata": {"order_id": "order_789"},
                }
            },
        }

    def test_recipe(self):
        event = Chain(self.raw_event)
        session = event.data.object

        assert event.type.value() == "checkout.session.completed"
        assert session.amount_total.value(int, default=0) == 2000
        assert session.customer_details.email.value() == "buyer@example.com"
        assert session.metadata.order_id.value() == "order_789"
        assert session.customer_details.name.value(default="(no name)") == "(no name)"
        assert event.data.object.refund.reason.value() is None


class TestPaginationRecipe(unittest.TestCase):
    """Mirrors docs/cookbook.md -> Walking a paginated REST response."""

    def setUp(self):
        self.response = {
            "data": [
                {"id": 1, "name": "Ada Lovelace", "team": {"name": "Engineering"}},
                {"id": 2, "name": "Alan Turing", "team": None},
                {"id": 3, "name": "Grace Hopper"},
            ],
            "pagination": {"next_cursor": "eyJpZCI6M30", "has_more": True},
        }

    def test_recipe(self):
        page = Chain(self.response)

        names = [row.name.value() for row in page.data]
        teams = [row.team.name.value(default="Unassigned") for row in page.data]
        assert names == ["Ada Lovelace", "Alan Turing", "Grace Hopper"]
        assert teams == ["Engineering", "Unassigned", "Unassigned"]

        assert page.data[0].team.name.value() == "Engineering"
        assert page.pagination.next_cursor.value() == "eyJpZCI6M30"
        assert page.pagination.has_more.value(bool, default=False) is True

    def test_last_page_has_no_cursor(self):
        last_page = Chain({"data": []})
        assert last_page.pagination.next_cursor.value() is None
        assert last_page.pagination.has_more.value(bool, default=False) is False


class TestFlakyApiRecipe(unittest.TestCase):
    """Mirrors docs/cookbook.md -> Hardening against a flaky third-party API."""

    def setUp(self):
        self.raw = {
            "location": {"city": "Austin", "region": None},
            "current": {
                "temp_f": "88.6",
                "humidity": 41,
                "wind": {},
            },
        }

    def test_recipe(self):
        weather = Chain(self.raw)

        assert weather.location.city.value(default="Unknown") == "Austin"
        assert weather.location.region.value(default="N/A") == "N/A"
        assert weather.current.temp_f.value(float, default=0.0) == 88.6
        assert weather.current.humidity.value(int, default=0) == 41
        assert weather.current.wind.speed_mph.value(float, default=0.0) == 0.0
        assert weather.forecast.tomorrow.high_f.value(int, default=0) == 0
        assert weather.alerts.count + 5 == 5


class TestTreeRecipe(unittest.TestCase):
    """Mirrors docs/cookbook.md -> Exploring an unknown payload with .tree()."""

    def test_recipe(self):
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
        # The exact rendering is pinned in test_tree.py; here we assert the
        # specific lines the cookbook shows so the doc can't drift.
        assert out.startswith("dict")
        assert "├─ users: list[2]" in out
        assert "│  └─ [0]: dict" in out
        assert "│     ├─ name: str = 'Ada'" in out
        assert "├─ tags: list[3] of str (e.g. 'a')" in out
        assert "└─ ok: bool = True" in out

    def test_module_level_shorthand(self):
        assert tree({"a": 1}) == "dict\n└─ a: int = 1"
