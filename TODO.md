# TODO

A focused list of improvements surfaced in the May 2026 product review.

- [ ] **Add type hints throughout `chain.py`.** The library targets Python 3.10+ but ships zero annotations, so IDE autocomplete and downstream type-checking go silent the moment a `Chain` shows up. This is the single biggest "does this look professional?" signal for a library and unlocks much smoother integration into typed codebases.
- [ ] **Real-world recipe docs, not toy examples.** Add a "Cookbook" page covering the patterns people actually reach for Daisies for: parsing a Stripe webhook, walking a paginated REST response, defending against a flaky third-party API. Right now the README sells the syntax; users need to see it solve their problem.
- [ ] **Wildcard / map traversal.** `data.users[*].email` to extract a single field across every item in a list (or every value in a dict) in one call. The single most-asked-for feature in safe-navigation libraries (cf. jq, JMESPath, Glom); without it, users still drop back to comprehensions for any non-trivial extraction. Likely the biggest expansion of the library's reach beyond single-path access.
- [ ] **Path-typed defaults via a terminal call.** `data.user.role.value(default="guest")` (and variants like `.value(int, default=0)`) to coalesce missing-or-None to a typed fallback in one shot. Today every chained access still ends in `or "default"` in user code — small ergonomic win that pairs naturally with the planned type hints, since the default's type also pins the return type.
