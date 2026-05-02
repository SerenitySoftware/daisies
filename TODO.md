# TODO

A focused list of improvements surfaced in the May 2026 product review.

- [ ] **Add type hints throughout `chain.py`.** The library targets Python 3.10+ but ships zero annotations, so IDE autocomplete and downstream type-checking go silent the moment a `Chain` shows up. This is the single biggest "does this look professional?" signal for a library and unlocks much smoother integration into typed codebases.
- [ ] **Real-world recipe docs, not toy examples.** Add a "Cookbook" page covering the patterns people actually reach for Daisies for: parsing a Stripe webhook, walking a paginated REST response, defending against a flaky third-party API. Right now the README sells the syntax; users need to see it solve their problem.
