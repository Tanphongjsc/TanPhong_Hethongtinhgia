"""Plain immutable nodes; stored JSON never contains executable objects."""
from dataclasses import dataclass
import hashlib
import json


@dataclass(frozen=True)
class Node:
    kind: str
    value: str
    children: tuple = ()
    position: int = 0

    def as_dict(self):
        return {"kind": self.kind, "value": self.value,
            "children": [child.as_dict() for child in self.children]}


def fingerprint(node):
    document = {"dsl_version": 1, "root": node.as_dict()}
    serialized = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return document, hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def walk(node):
    pending = [node]
    while pending:
        current = pending.pop()
        yield current
        pending.extend(reversed(current.children))
