# Daisies
Daisies is a Python library that provides easy, safe navigation for complex objects.

```python

from daisies import Chain

raw = {
    "never": {
        "gonna": {
            "give": {
                "you": {
                    "up": "never gonna let you down"
                }
            }
        }
    },
    "artists": [
        {
            "name": "Rick Astley",
            "genre": "Pop"
        },
        {
            "name": "Michael Jackson",
            "genre": "Pop"
        }
    ]
}
data = Chain(raw)


# Accessing nested dict keys that may or may not exist
print(data.never.gonna.give.you.up)  # "never gonna let you down"
print(data.let.you.down)  # None

# Navigating through lists
print(data.artists[0].name)  # "Rick Astley"
print(data.artists[1].name)  # "Michael Jackson"
print(data.artists[2].name)  # None
```


## Installation and Support
Daisies is available on PyPI, so you can install it like any other Python package, using the packager of your choice.

```bash
pip install daisies
```

Daisies is [automatically tested with 100% coverage](https://github.com/SerenitySoftware/daisies/blob/master/.github/workflows/verify.yml) on Python 3.10 and above for Ubuntu, macOS, and Windows.


## Why Daisies?

Daisies makes data navigation easy and safe so you don't have to constantly null-check, coalesce, try/except, and if/else.

You want data? Just go get it.

Simply wrap your raw data in a `Chain` object, which allows you to access its attributes using the dot notation.
If a key, attribute, or list index does not exist, the Chain object will return `None` instead of raising an exception.

This is particularly useful when dealing with complex data structures, such as JSON responses from APIs, where you can't always guarantee the presence of every key or index.

## Usage
Daisies aims to be as simple and intuitive as possible, so you can use it without having to write tons of code for null-checking and type validation.

For the most part, you can just use Daisies and pretend that you're working with the raw data directly.
However, there are some important differences to be aware of, especially when working with scalar values, arithmetic operations, and identity comparisons.

### Usage: Scalar values
Daisies allows you to seamlessly work with scalar values, such as strings, integers, and Booleans.
This allows you to operate on your data naturally.

```python
data = Chain({
    "name": "John Doe",
    "age": 30,
    "is_active": True
})

print(data.name)  # "John Doe"
print(data.age)  # 30
print(data.is_active)  # True
```

You can operate at any point on the Chain object, and it will return the expected result.

```python
data = Chain({
    "name": "John Doe",
    "age": 30,
    "is_active": True
})

print(data.name.upper())  # "JOHN DOE"
print(data.age + 10)  # 40
```


### Usage: Numeric values and arithmetic operations
Daisies allows you to work with numeric values and perform arithmetic operations on them,
but certain operations work differently from usual to ensure that you don't raise errors,
such as coercing `None` values to zero.

```python
data = Chain({
    "price": 100,
    "quantity": 5
})

print(data.price * data.quantity)  # 500
print(data.missing + 10)  # 10
print(data.quantity ** 3)  # 125

# Chain even allows division by zero, returning 0 instead.
# Not even Stephen Hawking could do that.
print(data.missing / 0)  # 0
```

### Usage: Lists and other iterables
Daisies allows you to work with lists, sets, and other iterables in a natural way.
You can access items by index and iterate over them. If they don't exist, Daisies will return `None`.

Iterating a `Chain` yields `Chain`-wrapped items, so you can keep navigating each element safely inside the loop — no need to unwrap and re-wrap. Missing fields on an element still resolve to `None` instead of raising.

```python
data = Chain({
    "names": ["Alice", "Bob", "Charlie"],
    "users": [{"name": "Alice"}, {"name": "Bob"}]
})

print(data.names[0])  # "Alice"
print(data.names[50])  # None

# Each item is a Chain, so nested access keeps working through the loop:
for user in data.users:
    print(user.name)  # "Alice", then "Bob"
```

### Working with dicts and nested data
Daisies allows you to work with nested data structures quickly and easily. No more null-checking or catching KeyErrors.

```python
data = Chain({
    "user": {
        "name": "Alice",
        "address": {
            "city": "Wonderland",
            "country": "Fairyland"
        }
    }
})

print(data.user.name)  # "Alice"
print(data.user.address.city)  # "Wonderland"
print(data.user.phone.number)  # None: a missing path is safe, no KeyError
```


### Usage: Typed defaults with `.value()`
For most uses, calling a Chain with `()` is enough to unwrap it. But when you want a fallback for missing data — or you want to coerce the value to a particular type — use `.value()`:

```python
from decimal import Decimal

data = Chain({
    "user": {
        "role": None,
        "age": "30",
    }
})

# Fallback for missing or None values
print(data.user.role.value(default="guest"))  # "guest"
print(data.user.missing.value(default="n/a"))  # "n/a"

# Coerce to a type, with a typed fallback
print(data.user.age.value(int, default=0))  # 30
print(data.user.missing.value(int, default=0))  # 0

# Coercion failures fall back too — never raises
print(data.user.role.value(int, default=-1))  # -1
print(Chain({"amt": "n/a"}).amt.value(Decimal, default=Decimal("0")))  # Decimal('0')
```

"Never raises" here means whatever the sender put in the field: text where you expected a number, a number too big to fit, a dict where you expected a date. You get your default back instead of an exception. The one thing it won't hide is a bug in your own conversion function — if that breaks, you'll hear about it.

This replaces the common `... or "default"` pattern at the end of a chain. Because the default's type pins the return type, your IDE and type checker can infer it correctly when the chain is annotated.

### Usage: Missing values and `.fallback()`
Use `.exists()` and `.is_missing()` when you need to distinguish a failed lookup from a value that is present but falsy—or explicitly `None`:

```python
data = Chain({
    "user": {"nickname": None},
    "contact": {"email": "ada@example.com"},
})

print(data.user.nickname.exists())  # True: the key is present
print(data.user.email.is_missing())  # True: the key is absent
```

`.fallback()` chooses another `Chain` or a plain value only when navigation is missing, and keeps the result wrapped:

```python
email = data.user.email.fallback(data.contact.email).fallback("noreply@example.com")
print(email)  # "ada@example.com"

# An explicit None is still a resolved value, so it does not fall back.
print(data.user.nickname.fallback("anonymous").value())  # None
```

`.value(default=...)` continues to treat both missing values and explicit `None` as reasons to use its terminal default. Use `.fallback()` when the distinction matters.

### Usage: Getting data back out with `.json()`, `.dict()`, and `.list()`
Once you've navigated to the part of a payload you care about, you usually want to send it back out — re-serialize it for another API, log it, cache it, or hand it to a template. Daisies gives you three unwrapping methods so you never have to reach for `json.dumps(...)` or the private `._wrapped` attribute.

```python
data = Chain({
    "user": {
        "name": "Alice",
        "roles": ["admin", "editor"],
    }
})

# .json() serializes to a JSON string; kwargs are forwarded to json.dumps
print(data.user.json())  # '{"name": "Alice", "roles": ["admin", "editor"]}'
print(data.user.json(indent=2))  # pretty-printed

# .dict() and .list() return plain, unwrapped containers
print(data.user.dict())  # {"name": "Alice", "roles": ["admin", "editor"]}
print(data.user.roles.list())  # ["admin", "editor"]
```

True to the rest of the library, these never raise on missing or mismatched data. A missing value serializes to JSON `null`, and `.dict()` / `.list()` return an empty container when the data isn't the shape you asked for:

```python
print(data.missing.json())  # "null"
print(data.missing.dict())  # {}
print(data.user.name.list())  # [] — a string isn't list-like
```

`.json()` extends that promise to values `json.dumps` doesn't understand — a `datetime`, `Decimal`, or `set` degrades to its string form instead of raising `TypeError`. Pass your own `default=` to override:

```python
from datetime import date

print(Chain({"when": date(2026, 7, 9)}).json())  # '{"when": "2026-07-09"}'
```

### Usage: Trimming a payload with `.pluck()`
Third-party payloads are usually much bigger than the part you're allowed to pass along. `.pluck()` picks out just the keys you name, so you can hand a trimmed, predictable object to the next system instead of forwarding whatever arrived:

```python
customer = Chain({
    "id": 42,
    "email": "ada@example.com",
    "internal_notes": "do not share",
    "card_token": "tok_secret",
})

print(customer.pluck("id", "email").dict())  # {"id": 42, "email": "ada@example.com"}
print(customer.pluck("id", "email").json())  # '{"id": 42, "email": "ada@example.com"}'
```

Keys come back in the order you asked for them, and a key that isn't there is simply left out rather than filled in with `None` — so a field the sender explicitly nulled still shows up, and one that was never sent doesn't. Like everything else in Daisies, it never raises: a missing node, or a value that isn't a dict at all, plucks to an empty dict.

```python
print(customer.pluck("id", "nickname").dict())  # {"id": 42} — "nickname" wasn't sent
print(Chain({"nickname": None}).pluck("nickname").dict())  # {"nickname": None} — sent as null
print(customer.missing.pluck("id").dict())  # {}
```

The result is still a Chain, so you can keep navigating it or hand it straight to `.dict()` or `.json()`.

### Usage: Dict views with `.keys()`, `.values()`, and `.items()`
Reach a wrapped dict's keys, values, or items as plain lists — null-tolerant, so a missing or non-dict node answers with `[]` instead of raising:

```python
settings = Chain({"user": {"theme": "dark", "lang": "en"}})
print(settings.user.keys())    # ["theme", "lang"]
print(settings.user.values())  # ["dark", "en"]
print(settings.user.items())   # [("theme", "dark"), ("lang", "en")]
print(settings.user.missing.keys())  # [] — never raises
```

A field literally named `keys`/`values`/`items` still wins on attribute access (`data.items[0]` navigates the field); reach the view via the method call on a dict that doesn't have that key.

### Usage: Absent vs. falsy with `.exists()` and `.is_missing()`
`if data.count:` can't tell a genuine `0` from a missing key. `.exists()` and `.is_missing()` can — a present-but-falsy value (`0`, `""`, `[]`, `False`) exists; an absent one doesn't:

```python
data = Chain({"count": 0})
print(data.count.exists())      # True — present, even though it's 0
print(data.missing.exists())    # False
print(data.missing.is_missing())  # True
```

(A key set literally to `None` reads as missing, since a missing hop is itself `None`.)

### Usage: Inspecting shape with `.tree()`
When you're handed an unfamiliar payload, print its shape before writing any navigation. `.tree()` shows keys, value types, and list lengths — tuned for exploration rather than dumping every value — and uses the first element as a representative for lists of objects.

```python
data = Chain({
    "user": {"name": "Ada", "age": 36},
    "roles": ["admin", "editor"],
})

print(data.tree())
# dict
# ├─ user: dict
# │  ├─ name: str = 'Ada'
# │  └─ age: int = 36
# └─ roles: list[2] of str (e.g. 'admin')
```

It returns a string — so you can log it or paste it into a bug report — and never raises. For large payloads, cap the output with `max_depth` and `max_items`. There's also a module-level `daisies.tree(data)` shorthand for when you haven't wrapped your data yet.

### Usage: Explaining an empty result with `.trace()`
Safe navigation has one blind spot: when a chain comes back `None`, it won't tell you *why*. Did the field move? Did the vendor stop sending it? Did you just typo a key? `.trace()` answers that in one line you can drop straight into a log.

```python
data = Chain({
    "user": {"name": "Alice"}
})

print(data.user.name.trace())          # "user.name: resolved"
print(data.user.address.trace())       # "user.address: missing"
print(data.user.address.city.trace())  # "user.address.city: missing at user.address"
```

That last line is the useful one. `city` never had a chance — `address` is the hop that wasn't there, and that's the thing to go fix.

A key that's present but set to `None` is a resolved value, not a missing one, and `.trace()` keeps the two apart:

```python
data = Chain({
    "user": {"nickname": None}
})

print(data.user.nickname.trace())  # "user.nickname: resolved (None)"
print(data.user.absent.trace())    # "user.absent: missing"
```

Indexes and bracket lookups read the way you wrote them, including inside a loop, so a bad row in a batch names itself:

```python
data = Chain({"users": [{"name": "Ada"}, {"name": "Bob"}]})

print(data.users[0].name.trace())  # "users[0].name: resolved"
print(data.users[1].email.trace())  # "users[1].email: missing"
```

Tracing only records where navigation went — it never changes what navigation returns.

### Usage: Watching for fields that disappear with `on_missing()`
Daisies surviving a field the vendor stopped sending is the point — but it also means nobody finds out. `daisies.on_missing()` turns that silent degradation into a signal: register a callback once and every failed hop becomes a countable, loggable event naming the field that went away.

```python
import daisies
from daisies import Chain

daisies.on_missing(lambda path: print(f"missing: {path}"))

data = Chain({"user": {"name": "Ada"}})
data.user.email.value()  # prints "missing: user.email"
```

The path arrives as a string in the same notation `.trace()` uses, so the same absent field always groups under the same key — exactly what you want for a counter:

```python
from collections import Counter

misses = Counter()
daisies.on_missing(lambda path: misses.update([path]))

data = Chain({"users": [{"id": 1}, {"id": 2}]})
for row in data.users:
    row.email.value()

# Indexed rows name themselves, so a bad row in a batch stays attributable:
print(misses)  # Counter({'users[0].email': 1, 'users[1].email': 1})
```

Only the *first* failure in a chain fires. `data.user.address.city` with no `address` reports `user.address` once, not three misses for one absent field — you get the field that actually vanished, not the fallout.

The observer is a bystander and behaves like one:

- It never changes what navigation returns.
- Anything the callback raises is swallowed rather than surfacing at the call site, so a broken metric can't break a data read.
- A callback that navigates missing data itself won't call itself back.
- An explicit `None` is a value the vendor sent, not a field that vanished, so it reports nothing.
- With no observer registered, a miss costs one context lookup.

Pass `None` to unregister. The return value works as a context manager if you'd rather scope the registration — handy in tests — and restores whatever was registered before it:

```python
seen = []

with daisies.on_missing(seen.append):
    Chain({"user": {}}).user.email.value()

assert seen == ["user.email"]
```

### Usage: Catching your own typos with strict mode
Never raising is the whole point of Daisies — but it means a *typo* looks exactly like a field the vendor didn't send. `data.user.emial` quietly comes back `None`, and nothing tells you until the wrong thing ships.

Strict mode is the opt-in fix: same navigation code, but unwrapping a path that never resolved raises `MissingPathError` instead of handing you a `None`. Turn it on in your tests and leave it off in production — fail fast on your own mistakes, stay null-tolerant about the vendor's.

```python
from daisies import Chain, MissingPathError

data = Chain({"user": {"email": "ada@example.com"}}, strict=True)

print(data.user.email.value())  # "ada@example.com" — resolved, so nothing changes
print(data.user.emial.value())  # raises MissingPathError: user.emial: missing
```

The error message is the same one-liner `.trace()` gives you, so it names the hop that actually failed, not just the path you asked for:

```python
data = Chain({"user": {}}, strict=True)

data.user.address.city.value()  # MissingPathError: user.address.city: missing at user.address
```

Strictness follows the data. Every chain you navigate off a strict one is strict too, all the way down through keys, indexes, loops, and `.pluck()`.

#### Telling Daisies you meant it
An absence you've explicitly handled isn't a mistake, so strict mode leaves it alone. Naming a default — or a fallback — is how you say the field is allowed to be missing:

```python
data = Chain({"user": {}}, strict=True)

print(data.user.email.value(default="noreply@example.com"))  # "noreply@example.com"
print(data.user.email.fallback("anonymous").value())         # "anonymous"

# Asking whether it's there is never a mistake either:
print(data.user.email.exists())      # False
print(data.user.email.is_missing())  # True
print(data.user.email.trace())       # "user.email: missing"
```

Only *unwrapping* is refused — `.value()` with no default, calling the chain, `.dict()`, `.list()`, `.json()`, and `.pluck()`. Navigating through a missing hop is still fine, and an explicit `None` is a resolved value, so a field the vendor deliberately nulled out never raises.

#### Turning it on for code you didn't wrap
When the `Chain` is built somewhere you don't control — a fixture, a client library, a helper — use the `daisies.strict()` context manager instead of the constructor flag:

```python
import daisies

payload = load_fixture()  # a Chain somebody else made

with daisies.strict():
    payload.user.emial.value()  # raises MissingPathError
```

The region covers the current thread (or async task) and restores whatever was in force when it exits, so a single `with daisies.strict():` in a pytest fixture makes a whole test suite strict. A chain built with an explicit `Chain(raw, strict=False)` opts back out of it.

### Usage: Special values and identity comparisons
When you access items through a `Chain`, it's not directly returning the value, it's returning a `Chain` wrapping the value.
A `Chain` is a very powerful and dynamic object that allows all sorts of operations on it, but it's not the same as the raw value.

This means there are a few special cases to be aware of. Because values are wrapped in a `Chain`, you can't use the identity operator `is` to check if a value is `None`, `True`, or `False` like usual.

But good news! If you want to compare identity, you can call the key like it's a function, and it'll return the raw value.

```python

data = Chain({
    "name": "John Doe",
    "age": 30,
    "is_active": True
})
print(data.is_active is True)  # False :(
print(data.missing.key is None)  # False :(
print(data.is_active() is True)  # True :)
print(data.missing.key() is None)  # True :)
```

### Usage: Navigating reserved words and invalid keys
Certain names are reserved in Python, so if your data contains keys that are reserved words or against the Python grammar,
you can still access them by using the square bracket notation. In fact, you never have to use the dot notation if you hate it! Either way Daisies will make sure it's safe navigation.

```python
data = Chain({
    "123": "Hello World!",
    "jeffrey-epstein": "Didn't kill himself"
})

print(data.123)  # SyntaxError :(
print(data["123"])  # "Hello World!"

print(data.jeffrey-epstein)  # SyntaxError :(
print(data["jeffrey-epstein"])  # "Didn't kill himself"
```

Square brackets are as forgiving as the dots. Asking for a name on something
that turned out to be a list, or a string, or a number — the sort of surprise a
third party springs on you — comes back `None` rather than blowing up, and the
miss is recorded so `.trace()` and `on_missing` can name it:

```python
weather = Chain({"current": {"wind": []}})  # the API usually sends a dict here

print(weather.current["wind"]["speed_mph"])  # None, not TypeError
print(weather.current["wind"]["speed_mph"].trace())
# current['wind']['speed_mph']: missing
```


## Cookbook
For real-world recipes — parsing a Stripe webhook, walking a paginated REST API, hardening against a flaky third-party service, forwarding only the fields you're allowed to share, and exploring an unknown payload with `.tree()` — see the [Cookbook](docs/cookbook.md).

## Contributing
Feel free to report bugs and suggest features through GitHub Issues, or open a PR for improvements.
