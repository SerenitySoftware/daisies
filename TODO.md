# TODO

A focused list of improvements surfaced in the May 2026 product review.

- [ ] **Real-world recipe docs, not toy examples.** Add a "Cookbook" page covering the patterns people actually reach for Daisies for: parsing a Stripe webhook, walking a paginated REST response, defending against a flaky third-party API. Right now the README sells the syntax; users need to see it solve their problem.
- [ ] **Wildcard / map traversal.** `data.users[*].email` to extract a single field across every item in a list (or every value in a dict) in one call. The single most-asked-for feature in safe-navigation libraries (cf. jq, JMESPath, Glom); without it, users still drop back to comprehensions for any non-trivial extraction. Likely the biggest expansion of the library's reach beyond single-path access.
