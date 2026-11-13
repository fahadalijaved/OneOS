"""Walk a bounded DT_NEEDED candidate graph without choosing a provider."""

from collections import deque
from collections.abc import Sequence


def _sequence(value, label, limit):
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{label} must be a sequence")
    count = len(value)
    if count > limit:
        raise ValueError(f"{label} exceeds its bound")
    return [value[index] for index in range(count)]


def _path(value):
    if not isinstance(value, str) or not 0 < len(value) <= 4095 or not value.isprintable() or "\\" in value:
        raise ValueError("Invalid source path")
    parts = value.removeprefix("/").split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("Source path is not canonical")
    return value


def _needed_name(value):
    if (not isinstance(value, str) or not 0 < len(value) <= 255 or not value.isascii()
            or not value.isprintable() or " " in value or "/" in value or "\\" in value or value in (".", "..")):
        raise ValueError("Invalid DT_NEEDED name")
    return value


def walk_graph(seed_paths, describe, candidates, *, max_objects=1024, max_edges=65536):
    """Return all visited objects, ordered references, misses and ambiguities.

    The callbacks are trusted, data-only readers. Each object description
    includes its ordered ``needed`` sequence. Each name's candidates are a
    strictly sorted, unique sequence of canonical source paths. A reference
    costs one edge per candidate, or one edge when unresolved. Repeated
    references remain visible. Each source path and name is queried once.
    """
    if type(max_objects) is not int or not 0 < max_objects <= 1024:
        raise ValueError("Invalid object bound")
    if type(max_edges) is not int or not 0 < max_edges <= 65536:
        raise ValueError("Invalid edge bound")
    if not callable(describe) or not callable(candidates):
        raise ValueError("Graph callbacks must be callable")

    scheduled = {_path(path) for path in _sequence(seed_paths, "Seed paths", max_objects)}
    pending = deque(sorted(scheduled))
    objects, edges, unresolved, known_candidates = {}, {}, {}, {}
    edge_count = 0
    while pending:
        path = pending.popleft()
        description = describe(path)
        if not isinstance(description, dict) or "needed" not in description:
            raise ValueError("Object description must include its DT_NEEDED sequence")
        needed = [_needed_name(name) for name in _sequence(description["needed"], "DT_NEEDED", max_edges - edge_count)]
        objects[path] = {**description, "needed": needed}
        references = []
        for name in needed:
            if edge_count == max_edges:
                raise ValueError("Graph exceeds its edge bound")
            if name not in known_candidates:
                paths = [_path(candidate) for candidate in _sequence(
                    candidates(name), "Candidate paths", min(max_objects, max_edges - edge_count))]
                if any(a >= b for a, b in zip(paths, paths[1:])):
                    raise ValueError("Candidate paths must be strictly sorted and unique")
                known_candidates[name] = paths
            paths = known_candidates[name]
            edge_count += max(1, len(paths))
            if edge_count > max_edges:
                raise ValueError("Graph exceeds its edge bound")
            references.append({"needed": name, "candidates": list(paths)})
            if not paths:
                unresolved.setdefault(name, set()).add(path)
            for target in paths:
                if target in scheduled:
                    continue
                if len(scheduled) == max_objects:
                    raise ValueError("Graph exceeds its object bound")
                scheduled.add(target)
                pending.append(target)
        edges[path] = references

    return {
        "objects": dict(sorted(objects.items())),
        "edges": dict(sorted(edges.items())),
        "unresolved": {name: sorted(callers) for name, callers in sorted(unresolved.items())},
        "ambiguous": {name: paths for name, paths in sorted(known_candidates.items()) if len(paths) > 1},
        "edge_count": edge_count,
    }
