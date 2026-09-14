import asyncio
import copy
import pickle
import threading
import unittest

from daisies import Chain, MissingPathError, strict


class TestStrictRaisesOnAMissingHop(unittest.TestCase):
    def test_value_on_a_missing_path_raises(self):
        data = Chain({"user": {"name": "Ada"}}, strict=True)

        with self.assertRaises(MissingPathError):
            data.user.emial.value()

    def test_calling_a_missing_path_raises(self):
        data = Chain({"user": {"name": "Ada"}}, strict=True)

        with self.assertRaises(MissingPathError):
            data.user.emial()

    def test_the_message_is_the_trace_so_it_names_the_guilty_hop(self):
        data = Chain({"user": {}}, strict=True)

        with self.assertRaises(MissingPathError) as caught:
            data.user.address.city.value()

        assert str(caught.exception) == "user.address.city: missing at user.address"

    def test_a_missing_index_raises_too(self):
        data = Chain({"tags": ["red"]}, strict=True)

        with self.assertRaises(MissingPathError) as caught:
            data.tags[7].value()

        assert str(caught.exception) == "tags[7]: missing"

    def test_the_container_accessors_refuse_to_hand_back_an_empty_stand_in(self):
        data = Chain({"user": {}}, strict=True)

        for unwrap in (
            lambda: data.user.roles.list(),
            lambda: data.user.profile.dict(),
            lambda: data.user.profile.json(),
            lambda: data.user.profile.pluck("id"),
        ):
            with self.assertRaises(MissingPathError):
                unwrap()


class TestStrictLeavesEverythingElseAlone(unittest.TestCase):
    def test_resolved_values_unwrap_exactly_as_before(self):
        data = Chain({"user": {"name": "Ada", "roles": ["admin"], "meta": {"id": 7}}}, strict=True)

        assert data.user.name.value() == "Ada"
        assert data.user.name() == "Ada"
        assert data.user.roles.list() == ["admin"]
        assert data.user.meta.dict() == {"id": 7}
        assert data.user.meta.json() == '{"id": 7}'
        assert data.user.meta.pluck("id").dict() == {"id": 7}

    def test_an_explicit_none_is_a_resolved_value_and_never_raises(self):
        data = Chain({"user": {"nickname": None}}, strict=True)

        assert data.user.nickname.value() is None
        assert data.user.nickname() is None
        assert data.user.nickname.json() == "null"

    def test_falsy_values_are_resolved_values(self):
        data = Chain({"count": 0, "label": "", "tags": [], "flag": False}, strict=True)

        assert data.count.value() == 0
        assert data.label.value() == ""
        assert data.tags.list() == []
        assert data.flag.value() is False

    def test_a_resolved_value_of_the_wrong_shape_still_degrades_quietly(self):
        # Strict mode is about hops that never resolved, not about values that
        # resolved to something the accessor can't use.
        data = Chain({"user": "not-a-dict"}, strict=True)

        assert data.user.dict() == {}
        assert data.user.list() == []
        assert data.user.pluck("id").dict() == {}

    def test_navigation_itself_stays_silent(self):
        data = Chain({"user": {}}, strict=True)

        # Walking through a missing hop is fine; only unwrapping is refused.
        node = data.user.address.city
        assert node.is_missing()
        assert not node.exists()
        assert node.trace() == "user.address.city: missing at user.address"
        assert repr(node) == "None"
        assert str(node) == "None"
        assert bool(node) is False

    def test_a_missing_path_is_not_strict_by_default(self):
        data = Chain({"user": {}})

        assert data.user.address.city.value() is None
        assert data.user.address.city() is None


class TestStrictHonoursAnExplicitDefault(unittest.TestCase):
    def test_value_with_a_default_is_handling_the_absence(self):
        data = Chain({"user": {}}, strict=True)

        assert data.user.emial.value(default="noreply@example.com") == "noreply@example.com"

    def test_an_explicit_none_default_counts_as_handling_it(self):
        data = Chain({"user": {}}, strict=True)

        assert data.user.emial.value(default=None) is None

    def test_a_default_still_covers_a_failed_coercion(self):
        data = Chain({"user": {"age": "old"}}, strict=True)

        assert data.user.age.value(int, default=0) == 0

    def test_a_bare_coercion_of_a_missing_path_still_raises(self):
        data = Chain({"user": {}}, strict=True)

        with self.assertRaises(MissingPathError):
            data.user.age.value(int)

    def test_fallback_is_handling_the_absence_too(self):
        data = Chain({"user": {}, "contact": {"email": "ada@example.com"}}, strict=True)

        assert data.user.email.fallback(data.contact.email).value() == "ada@example.com"
        assert data.user.email.fallback("anonymous").value() == "anonymous"

    def test_a_fallback_that_is_itself_missing_still_raises_when_unwrapped(self):
        data = Chain({}, strict=True)

        with self.assertRaises(MissingPathError):
            data.user.email.fallback(data.contact.email).value()


class TestStrictCarriesOntoDerivedChains(unittest.TestCase):
    def test_attribute_and_item_hops_stay_strict(self):
        data = Chain({"users": [{"name": "Ada"}]}, strict=True)

        with self.assertRaises(MissingPathError):
            data.users[0].email.value()
        with self.assertRaises(MissingPathError):
            data["users"][0]["email"].value()

    def test_iteration_yields_strict_chains(self):
        data = Chain({"users": [{"name": "Ada"}, {"name": "Bob"}]}, strict=True)

        with self.assertRaises(MissingPathError):
            [user.email.value() for user in data.users]

    def test_a_plucked_projection_stays_strict(self):
        data = Chain({"user": {"id": 7}}, strict=True)

        with self.assertRaises(MissingPathError):
            data.user.pluck("id").email.value()

    def test_a_literal_fallback_keeps_the_mode_for_what_comes_after_it(self):
        data = Chain({}, strict=True)

        with self.assertRaises(MissingPathError):
            data.user.fallback({"name": "anonymous"}).email.value()

    def test_the_mode_survives_copy_and_pickle(self):
        data = Chain({"user": {}}, strict=True)

        for restored in (
            copy.copy(data),
            copy.deepcopy(data),
            pickle.loads(pickle.dumps(data)),
        ):
            with self.assertRaises(MissingPathError):
                restored.user.address.value()


class TestTheStrictContextManager(unittest.TestCase):
    def test_it_reaches_data_someone_else_wrapped(self):
        data = Chain({"user": {}})

        assert data.user.email.value() is None
        with strict():
            with self.assertRaises(MissingPathError):
                data.user.email.value()
        assert data.user.email.value() is None

    def test_it_restores_the_previous_mode_even_when_the_block_raises(self):
        data = Chain({"user": {}})

        with self.assertRaises(MissingPathError):
            with strict():
                data.user.email.value()

        assert data.user.email.value() is None

    def test_it_nests(self):
        data = Chain({"user": {}})

        with strict():
            with strict():
                with self.assertRaises(MissingPathError):
                    data.user.email.value()
            with self.assertRaises(MissingPathError):
                data.user.email.value()

    def test_a_chain_pinned_tolerant_opts_out_of_the_region(self):
        with strict():
            assert Chain({"user": {}}, strict=False).user.email.value() is None

    def test_a_chain_pinned_strict_ignores_the_absence_of_a_region(self):
        assert Chain({"user": {}}, strict=True).user.exists()

        with self.assertRaises(MissingPathError):
            Chain({"user": {}}, strict=True).user.email.value()

    def test_the_region_does_not_leak_into_another_thread(self):
        data = Chain({"user": {}})
        seen = []

        def read_tolerantly():
            seen.append(data.user.email.value())

        with strict():
            worker = threading.Thread(target=read_tolerantly)
            worker.start()
            worker.join()

        assert seen == [None]

    def test_the_region_does_not_leak_into_a_concurrent_task(self):
        data = Chain({"user": {}})

        async def strict_reader():
            with strict():
                # Yield to the loop mid-region: each task carries its own copy
                # of the context, so the other one keeps reading tolerantly.
                await asyncio.sleep(0)
                with self.assertRaises(MissingPathError) as caught:
                    data.user.email.value()
            return str(caught.exception)

        async def tolerant_reader():
            await asyncio.sleep(0)
            return data.user.email.value()

        async def main():
            return await asyncio.gather(
                asyncio.create_task(strict_reader()),
                asyncio.create_task(tolerant_reader()),
            )

        strict_result, tolerant_result = asyncio.run(main())

        assert strict_result == "user.email: missing"
        assert tolerant_result is None
