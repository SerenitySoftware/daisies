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
        assert weather.current["wind"]["speed_mph"].value(float, default=0.0) == 0.0

    def test_brackets_survive_the_container_changing_shape(self):
        # The day "wind" comes back as a list instead of an object.
        weather = Chain({"current": {"wind": []}})

        assert weather.current["wind"]["speed_mph"].value(float, default=0.0) == 0.0


class TestForwardingWhitelistRecipe(unittest.TestCase):
    """Mirrors docs/cookbook.md -> Forwarding only what you're allowed to share."""

    def setUp(self):
        self.raw = {
            "id": "usr_88121",
            "email": "ada@example.com",
            "display_name": None,
            "ssn": "000-00-0000",
            "internal": {"risk_score": 0.92, "notes": "flagged"},
        }

    def test_only_the_whitelist_is_serialized(self):
        user = Chain(self.raw)
        payload = user.pluck("id", "email", "display_name")
        assert payload.json() == '{"id": "usr_88121", "email": "ada@example.com", "display_name": null}'
        assert "ssn" not in payload.dict()
        assert "internal" not in payload.dict()

    def test_absent_key_is_left_out_rather_than_nulled(self):
        user = Chain(self.raw)
        assert user.pluck("id", "phone").dict() == {"id": "usr_88121"}

    def test_composes_with_navigation(self):
        user = Chain(self.raw)
        assert user.internal.pluck("risk_score").dict() == {"risk_score": 0.92}


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


class TestTraceRecipe(unittest.TestCase):
    """Mirrors docs/cookbook.md -> Explaining an empty result with .trace()."""

    def test_recipe(self):
        payload = {
            "user": {"name": "Ada"},
            "billing": {"address": {"city": "Austin"}},
        }
        order = Chain(payload)
        city = order.user.address.city

        assert city.is_missing()
        assert city.trace() == "user.address.city: missing at user.address"
        assert order.billing.address.city.trace() == "billing.address.city: resolved"

    def test_an_explicit_null_reads_differently_from_an_absent_field(self):
        account = Chain({"user": {"name": "Ada", "nickname": None}})

        assert account.user.nickname.trace() == "user.nickname: resolved (None)"
        assert account.user.email.trace() == "user.email: missing"

    def test_a_bad_row_in_a_batch_names_itself(self):
        rows = Chain({"users": [{"name": "Ada"}, {"name": "Bob"}]})

        assert [user.email.trace() for user in rows.users] == [
            "users[0].email: missing",
            "users[1].email: missing",
        ]
