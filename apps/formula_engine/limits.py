"""Bounded DSL execution; settings overrides are deployment configuration."""
from dataclasses import dataclass
from django.conf import settings


@dataclass(frozen=True)
class Limits:
    expression_length: int = 8000
    nodes: int = 512
    depth: int = 40
    graph_nodes: int = 200
    graph_depth: int = 40
    steps: int = 50000
    trace_rows: int = 1000
    numeric_digits: int = 64
    precision: int = 38
    magnitude: int = 100


def limits():
    values = getattr(settings, "FORMULA_LIMITS", {})
    defaults = Limits()
    # Absolute ceilings prevent a bad setting re-enabling unbounded execution.
    ceilings = {"expression_length": 16000, "nodes": 1024, "depth": 60,
        "graph_nodes": 500, "graph_depth": 60, "steps": 100000, "trace_rows": 2000,
        "numeric_digits": 128, "precision": 64, "magnitude": 200}
    return Limits(**{key: max(1, min(int(values.get(key, getattr(defaults, key))), maximum))
        for key, maximum in ceilings.items()})
