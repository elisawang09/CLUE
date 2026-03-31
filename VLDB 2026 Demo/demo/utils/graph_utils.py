"""
graph_utils.py
--------------
Pure graph traversal helpers: adjacency maps, ancestor lookup, and
path-edge extraction.

No rendering or styling concerns live here — this module has zero
dependency on streamlit-flow or any UI library.
"""

from __future__ import annotations

from collections import defaultdict

from data.graph_data import EDGES


# ---------------------------------------------------------------------------
# Adjacency maps (built once at import time)
# ---------------------------------------------------------------------------

def _build_adjacency() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    children: dict[str, list[str]] = defaultdict(list)
    parents:  dict[str, list[str]] = defaultdict(list)
    for e in EDGES:
        children[e.source].append(e.target)
        parents[e.target].append(e.source)
    return dict(children), dict(parents)


CHILDREN, PARENTS = _build_adjacency()


# ---------------------------------------------------------------------------
# Traversal helpers
# ---------------------------------------------------------------------------

def ancestors_of(node_id: str) -> set[str]:
    """Return all ancestor node IDs inclusive of the node itself."""
    visited: set[str] = set()
    stack = [node_id]
    while stack:
        cur = stack.pop()
        if cur in visited:
            continue
        visited.add(cur)
        stack.extend(PARENTS.get(cur, []))
    return visited


def path_edges(node_id: str) -> set[tuple[str, str]]:
    """Return (source, target) pairs on the root-to-node path."""
    anc = ancestors_of(node_id)
    return {(e.source, e.target) for e in EDGES if e.source in anc and e.target in anc}
