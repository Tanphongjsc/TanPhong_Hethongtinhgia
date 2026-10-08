"""Dependency normalization and iterative graph ordering/cycle detection."""
from .ast_nodes import walk
from .errors import FormulaError
from .limits import limits


def references(root):
    found = {}
    for node in walk(root):
        if node.kind in ("symbol", "element", "formula"):
            found.setdefault((node.kind, node.value), node)
    return found


def topological_order(graph, start):
    budget = limits()
    state, order, path = {}, [], []
    stack = [(start, False)]
    while stack:
        key, exiting = stack.pop()
        if exiting:
            path.pop(); state[key] = 2; order.append(key)
            continue
        if state.get(key) == 1:
            cycle = path[path.index(key):] + [key]
            raise FormulaError("Phát hiện phụ thuộc vòng giữa các công thức: " + " → ".join(cycle) + ".")
        if state.get(key) == 2:
            continue
        if len(state) >= budget.graph_nodes or len(path) >= budget.graph_depth:
            raise FormulaError("Phụ thuộc công thức vượt giới hạn số lượng hoặc độ sâu.")
        state[key] = 1; path.append(key); stack.append((key, True))
        stack.extend((child, False) for child in reversed(sorted(graph.get(key, ()))))
    return order
