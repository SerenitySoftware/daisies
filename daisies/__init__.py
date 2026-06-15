__all__ = ["Chain", "tree"]

from typing import Any

from .chain import Chain


def tree(data: Any, *, max_depth: int = 6, max_items: int = 50) -> str:
    """Render the shape of ``data`` as a tree. Shorthand for ``Chain(data).tree()``.

    See :meth:`daisies.chain.Chain.tree` for details and options.
    """
    return Chain(data).tree(max_depth=max_depth, max_items=max_items)
