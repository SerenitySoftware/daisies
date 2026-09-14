import asyncio
import threading
import unittest

import daisies
from daisies import Chain, MissingPathError


class ObserverTestCase(unittest.TestCase):
    """Registers an observer that is always torn down, however the test ends."""

    def setUp(self):
        self.seen = []
        observer = daisies.on_missing(self.seen.append)
        self.addCleanup(observer.__exit__)


class TestOnMissingReportsTheFailingHop(ObserverTestCase):
    def test_a_missing_key_reports_its_path(self):
        Chain({"user": {"name": "Ada"}}).user.email.value()

        assert self.seen == ["user.email"]

    def test_only_the_first_failure_in_a_chain_fires(self):
        # One absent field is one event, however far navigation carries on.
        Chain({"user": {}}).user.address.city.value()

        assert self.seen == ["user.address"]

    def test_paths_read_the_way_trace_writes_them(self):
        data = Chain({"users": [{"name": "Ada"}], "user": {}})

        data.users[3].email.value()
        data["user"]["phone"].value()
        data.user.name.city.value()

        assert self.seen == ["users[3]", "['user']['phone']", "user.name"]

    def test_the_same_absent_field_reports_the_same_string_every_time(self):
        rows = Chain({"users": [{"id": 1}, {"id": 2}]})

        for row in rows.users:
            row.email.value()

        # Indexed rows name themselves, so a per-row miss stays attributable.
        assert self.seen == ["users[0].email", "users[1].email"]

    def test_a_missing_collection_reports_once_even_when_defaulted(self):
        Chain({}).users.value(default=[])

        assert self.seen == ["users"]

    def test_a_resolved_path_reports_nothing(self):
        data = Chain({"user": {"name": "Ada", "nickname": None, "tags": []}})

        data.user.name.value()
        data.user.nickname.value()
        data.user.tags.list()

        # An explicit None is a value the vendor sent, not a field that vanished.
        assert self.seen == []

    def test_a_pluck_that_skips_an_absent_key_is_not_a_miss(self):
        # Plucking names what's allowed through, so a key that isn't there is
        # expected rather than a signal.
        Chain({"id": 7}).pluck("id", "email").dict()

        assert self.seen == []


class TestOnMissingStaysOutOfTheWay(ObserverTestCase):
    def test_navigation_returns_exactly_what_it_would_have(self):
        data = Chain({"user": {"name": "Ada"}})

        assert data.user.email.value() is None
        assert data.user.email() is None
        assert data.user.email.is_missing()
        assert data.user.email.fallback("anon") == "anon"
        assert data.user.email.trace() == "user.email: missing"

    def test_it_fires_alongside_strict_mode_without_swallowing_the_error(self):
        with self.assertRaises(MissingPathError):
            Chain({"user": {}}, strict=True).user.email.value()

        assert self.seen == ["user.email"]


class TestOnMissingNeverRaisesOutOfTheCallback(unittest.TestCase):
    def test_a_broken_observer_does_not_break_navigation(self):
        def boom(path):
            raise RuntimeError(path)

        with daisies.on_missing(boom):
            assert Chain({"user": {}}).user.email.value() is None

    def test_an_observer_that_navigates_missing_data_does_not_re_enter(self):
        calls = []

        def nosy(path):
            calls.append(path)
            Chain({}).something.value()

        with daisies.on_missing(nosy):
            Chain({}).outer.value()

        assert calls == ["outer"]


class TestRegisteringAndUnregistering(unittest.TestCase):
    def test_none_unregisters(self):
        seen = []

        daisies.on_missing(seen.append)
        Chain({}).before.value()
        daisies.on_missing(None)
        Chain({}).after.value()

        assert seen == ["before"]

    def test_the_handle_scopes_the_registration(self):
        seen = []

        with daisies.on_missing(seen.append):
            Chain({}).inside.value()
        Chain({}).outside.value()

        assert seen == ["inside"]

    def test_a_scoped_observer_restores_the_one_it_replaced(self):
        outer, inner = [], []

        with daisies.on_missing(outer.append):
            with daisies.on_missing(inner.append):
                Chain({}).nested.value()
            Chain({}).restored.value()

        assert inner == ["nested"]
        assert outer == ["restored"]

    def test_nothing_is_registered_by_default(self):
        # Guards against a leaked registration from another test in the suite.
        assert Chain({}).unwatched.value() is None

    def test_the_registration_does_not_leak_into_another_thread(self):
        seen = []
        crossed = []

        def read_unwatched():
            Chain({}).threaded.value()
            crossed.append(True)

        with daisies.on_missing(seen.append):
            worker = threading.Thread(target=read_unwatched)
            worker.start()
            worker.join()

        assert crossed == [True]
        assert seen == []

    def test_the_registration_does_not_leak_into_a_concurrent_task(self):
        watched, unwatched = [], []

        async def watched_reader():
            with daisies.on_missing(watched.append):
                await asyncio.sleep(0)
                Chain({}).watched.value()

        async def unwatched_reader():
            await asyncio.sleep(0)
            Chain({}).unwatched.value()

        async def main():
            await asyncio.gather(
                asyncio.create_task(watched_reader()),
                asyncio.create_task(unwatched_reader()),
            )

        asyncio.run(main())

        assert watched == ["watched"]
        assert unwatched == []
