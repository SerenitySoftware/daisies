# TODO

Daisies is a small, predictable wrapper for safely reading unreliable nested Python data. New features should directly strengthen that promise without turning the library into a query language, serializer, schema system, or general-purpose data toolkit.

## Core safe navigation

- [ ] **Distinguish missing values from explicit `None`.** Introduce an internal missing sentinel so a path that did not resolve is different from a key or index whose value is actually `None`. Keep the public, null-tolerant behavior intact while making `.exists()` return `True` for every resolved value—including `None`, `0`, `False`, `""`, and empty containers—and `.is_missing()` return `True` only when navigation failed.

- [ ] **`.fallback(...)` for multi-source defaults.** Express “try this path, then that path, then a literal default” fluently: `data.user.email.fallback(data.contact.email).fallback("noreply@example.com")`. Return the current Chain when it resolved, even to an explicit `None`; otherwise return the Chain-wrapped fallback. Accept either another `Chain` or a plain value, never raise, and remain wrapped so navigation can continue.

- [ ] **`.pluck(*keys)` for whitelist projection.** Return a Chain-wrapped dictionary containing only the requested keys from the current mapping, silently skipping absent keys. Missing or non-mapping values produce an empty wrapped dictionary. This should compose directly with `.dict()` and `.json()` for small outbound payloads without becoming a general query API.

## Debugging safe navigation

- [ ] **`.trace()` for explaining a missing result.** Record and expose the navigation path and the first hop that failed, so `chain.user.address.city.trace()` can explain whether `user`, `address`, or `city` was missing. Keep the result compact and useful in logs, preserve the distinction between a missing hop and an explicit `None`, and avoid changing normal navigation behavior.
