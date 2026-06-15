# Daisies Cookbook

Real-world recipes, not toy examples. The README sells the syntax; this page
shows Daisies solving the problems people actually reach for it: messy webhooks,
paginated APIs, flaky third parties, and undocumented payloads.

Every snippet on this page is mirrored by an assertion in
[`test_cookbook.py`](../daisies/tests/test_cookbook.py), so the docs can't
silently drift away from the implementation.

- [Parsing a Stripe webhook](#parsing-a-stripe-webhook)
- [Walking a paginated REST response](#walking-a-paginated-rest-response)
- [Hardening against a flaky third-party API](#hardening-against-a-flaky-third-party-api)
- [Exploring an unknown payload with `.tree()`](#exploring-an-unknown-payload-with-tree)


## Parsing a Stripe webhook

Webhook payloads are deeply nested and full of optional fields that are present
on one event type and absent on the next. The usual handler is a thicket of
`payload.get("data", {}).get("object", {}).get(...)`. With Daisies you just walk
the path you want and supply a default where it matters.

```python
from daisies import Chain

raw_event = {
    "id": "evt_1NG8Du2eZvKYlo2C",
    "type": "checkout.session.completed",
    "data": {
        "object": {
            "id": "cs_test_a1b2c3",
            "amount_total": 2000,             # in cents
            "currency": "usd",
            "customer_details": {
                "email": "buyer@example.com",
                "name": None,                 # Stripe nulls optional fields
            },
            "metadata": {"order_id": "order_789"},
        }
    },
}

event = Chain(raw_event)
session = event.data.object

event_type = event.type.value()                       # "checkout.session.completed"
amount_cents = session.amount_total.value(int, default=0)  # 2000
email = session.customer_details.email.value()        # "buyer@example.com"
order_id = session.metadata.order_id.value()          # "order_789"

# Optional fields that Stripe nulls out don't blow up:
name = session.customer_details.name.value(default="(no name)")  # "(no name)"

# A field that only exists on a *different* event shape simply yields None
# instead of raising KeyError:
refund_reason = event.data.object.refund.reason.value()          # None
```


## Walking a paginated REST response

A list of records plus a pagination cursor that disappears on the last page.

Iterating a `Chain` yields `Chain`-wrapped items, so you can keep navigating each
row safely inside the loop — no re-wrapping needed, and missing fields still
resolve cleanly. (Once wildcard traversal lands — `page.data[*].name` — this gets
terser still; see the project TODO.)

```python
from daisies import Chain

response = {
    "data": [
        {"id": 1, "name": "Ada Lovelace", "team": {"name": "Engineering"}},
        {"id": 2, "name": "Alan Turing", "team": None},   # team present but null
        {"id": 3, "name": "Grace Hopper"},                # no team key at all
    ],
    "pagination": {"next_cursor": "eyJpZCI6M30", "has_more": True},
}

page = Chain(response)

# Each row is itself a Chain, so nested fields default cleanly with no re-wrap:
names = [row.name.value() for row in page.data]
teams = [row.team.name.value(default="Unassigned") for row in page.data]
# names -> ["Ada Lovelace", "Alan Turing", "Grace Hopper"]
# teams -> ["Engineering", "Unassigned", "Unassigned"]

# Indexed access returns a Chain directly, so single-row reads stay terse:
first_team = page.data[0].team.name.value()           # "Engineering"

# Drive pagination off a cursor that may or may not be there:
cursor = page.pagination.next_cursor.value()          # "eyJpZCI6M30"
has_more = page.pagination.has_more.value(bool, default=False)  # True

# On the last page those keys are gone — no special-casing needed:
last_page = Chain({"data": []})
last_page.pagination.next_cursor.value()              # None
last_page.pagination.has_more.value(bool, default=False)  # False
```


## Hardening against a flaky third-party API

The classic case Daisies was built for: an API that's inconsistent between
calls. Fields go missing, come back `null`, or arrive as the wrong type. Lean on
`.value(type_, default=...)` to coerce and fall back in one step.

```python
from daisies import Chain

raw = {
    "location": {"city": "Austin", "region": None},
    "current": {
        "temp_f": "88.6",        # sometimes a string!
        "humidity": 41,
        "wind": {},              # sometimes an empty object
    },
    # the "forecast" key is entirely absent on some responses
}

weather = Chain(raw)

city = weather.location.city.value(default="Unknown")        # "Austin"
region = weather.location.region.value(default="N/A")        # "N/A" (was null)

# Coerce a stringly-typed number, with a safe fallback if it can't parse:
temp = weather.current.temp_f.value(float, default=0.0)      # 88.6
humidity = weather.current.humidity.value(int, default=0)    # 41

# Deeply missing paths just resolve to the default — no KeyError, no None checks:
wind_mph = weather.current.wind.speed_mph.value(float, default=0.0)     # 0.0
tomorrow_high = weather.forecast.tomorrow.high_f.value(int, default=0)  # 0

# Arithmetic tolerates the gaps too — a missing number coerces to zero:
total_alerts = weather.alerts.count + 5                      # 5
```


## Exploring an unknown payload with `.tree()`

Before writing any navigation against an undocumented endpoint, look at the
*shape* of what came back. `.tree()` prints keys, types, and list lengths —
tuned for exploration, not a full dump — and a representative element for lists
of objects.

```python
from daisies import Chain

payload = {
    "users": [
        {"name": "Ada", "age": 36, "email": None},
        {"name": "Bob", "age": 40, "email": "bob@example.com"},
    ],
    "meta": {"next": None, "count": 2},
    "tags": ["a", "b", "c"],
    "ok": True,
}

print(Chain(payload).tree())
# dict
# ├─ users: list[2]
# │  └─ [0]: dict
# │     ├─ name: str = 'Ada'
# │     ├─ age: int = 36
# │     └─ email: None
# ├─ meta: dict
# │  ├─ next: None
# │  └─ count: int = 2
# ├─ tags: list[3] of str (e.g. 'a')
# └─ ok: bool = True
```

For big payloads, rein in the output with `max_depth` and `max_items`:

```python
from daisies import tree   # module-level shorthand for Chain(data).tree()

print(tree(huge_payload, max_depth=2, max_items=10))
```

Wide levels are truncated with a `… (+N more)` line, and branches past
`max_depth` collapse to `dict {…}` / `list[N] [...]` so the overall shape stays
on one screen.
