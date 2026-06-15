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
print(data.this.is.missing)  # None
```


### Usage: Typed defaults with `.value()`
For most uses, calling a Chain with `()` is enough to unwrap it. But when you want a fallback for missing data — or you want to coerce the value to a particular type — use `.value()`:

```python
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
```

This replaces the common `... or "default"` pattern at the end of a chain. Because the default's type pins the return type, your IDE and type checker can infer it correctly when the chain is annotated.

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


## Contributing
Feel free to report bugs and suggest features through GitHub Issues, or open a PR for improvements.
