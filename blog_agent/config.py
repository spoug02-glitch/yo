import json
import os
from typing import Any

_DEFAULT = os.path.join(os.path.dirname(__file__), "config.json")


def load_config(path: str | None = None) -> dict:
    with open(path or _DEFAULT, "r", encoding="utf-8") as f:
        return json.load(f)


def value(cfg: dict, dotted_key: str) -> Any:
    node: Any = cfg
    for part in dotted_key.split("."):
        node = node[part]
    return node["value"] if isinstance(node, dict) and "value" in node else node
