# TODO

Daisies is a small, predictable wrapper for safely reading unreliable nested Python data. New features should directly strengthen that promise without turning the library into a query language, serializer, schema system, or general-purpose data toolkit.

## Core safe navigation

- [x] **Distinguish missing values from explicit `None`.** Introduce an internal missing sentinel so a path that did not resolve is different from a key or index whose value is actually `None`. Keep the public, null-tolerant behavior intact while making `.exists()` return `True` for every resolved value—including `None`, `0`, `False`, `""`, and empty containers—and `.is_missing()` return `True` only when navigation failed.

- [x] **`.fallback(...)` for multi-source defaults.** Express “try this path, then that path, then a literal default” fluently: `data.user.email.fallback(data.contact.email).fallback("noreply@example.com")`. Return the current Chain when it resolved, even to an explicit `None`; otherwise return the Chain-wrapped fallback. Accept either another `Chain` or a plain value, never raise, and remain wrapped so navigation can continue.

- [x] **`.pluck(*keys)` for whitelist projection.** Return a Chain-wrapped dictionary containing only the requested keys from the current mapping, silently skipping absent keys. Missing or non-mapping values produce an empty wrapped dictionary. This should compose directly with `.dict()` and `.json()` for small outbound payloads without becoming a general query API.

## Debugging safe navigation

- [x] **`.trace()` for explaining a missing result.** Record and expose the navigation path and the first hop that failed, so `chain.user.address.city.trace()` can explain whether `user`, `address`, or `city` was missing. Keep the result compact and useful in logs, preserve the distinction between a missing hop and an explicit `None`, and avoid changing normal navigation behavior.

- [ ] **Strict mode for tests and development.** *(PM rec, August 2026)* Never raising is the library's central promise and also its one blind spot: a *typo* is indistinguishable from a genuinely absent field, so `data.user.emial` silently resolves to `None` and ships. Add an opt-in strict mode — `Chain(raw, strict=True)` plus a `daisies.strict()` context manager for code that doesn't own the wrapping — that raises on a missing hop while leaving every other behavior identical, so the same navigation code can run strict under pytest/CI and tolerant in production. Fail-fast on your own mistakes, null-tolerance on the vendor's. Builds directly on the missing sentinel already added above; strictness must be carried through `__getattr__`/`__getitem__` onto derived Chains, and `.fallback()`/`.value(default=...)` must stay non-raising (an explicit default *is* handling the absence). Distinct from `.trace()` — that explains a miss after the fact, this refuses to let one pass silently in the first place.

- [ ] **A missing-path observer hook.** *(PM rec, August 2026)* `daisies.on_missing(callback)` — a process-wide (or context-scoped) callback fired whenever navigation fails, receiving the path that missed. Turns the library's silent degradation into a production signal: counting or logging missing paths is how you find out *which fields a third party stopped sending, and when* — the exact failure Daisies exists to survive but currently hides. Keep it strictly observational (never alters resolution, never raises out of the callback, near-zero cost when unset) and share the recording plumbing with `.trace()` and strict mode above, since all three key off the same failed hop.
