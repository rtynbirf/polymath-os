"""Tiny fail-closed JSON Schema subset validator (stdlib only).

Supported keywords: type, enum, required, properties, additionalProperties(false),
minLength, minimum. Annotation keywords ($schema, title, description) are ignored.
Any other keyword raises SchemaError: unsupported means unverified, not "passed".
This is NOT a full JSON Schema implementation; use a real validator in production.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
_IGNORED = {"$schema", "title", "description", "$id"}
_SUPPORTED = {"type", "enum", "required", "properties", "additionalProperties", "minLength", "minimum"}


class SchemaError(Exception):
    pass


def load_schema(name: str) -> Dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _type_ok(value, t):
    if t == "string": return isinstance(value, str)
    if t == "object": return isinstance(value, dict)
    if t == "boolean": return isinstance(value, bool)
    if t == "integer": return isinstance(value, int) and not isinstance(value, bool)
    if t == "array": return isinstance(value, list)
    raise SchemaError(f"unsupported type: {t}")


def validate(value: Any, schema: Dict[str, Any], path: str = "$") -> List[str]:
    """Return list of error strings (empty list = valid)."""
    errors: List[str] = []
    for key in schema:
        if key not in _SUPPORTED and key not in _IGNORED:
            raise SchemaError(f"unsupported schema keyword: {key}")
    if "type" in schema and not _type_ok(value, schema["type"]):
        return [f"{path}: expected {schema['type']}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: not in {schema['enum']}")
    if "minLength" in schema and isinstance(value, str) and len(value) < schema["minLength"]:
        errors.append(f"{path}: shorter than {schema['minLength']}")
    if "minimum" in schema and isinstance(value, int) and value < schema["minimum"]:
        errors.append(f"{path}: below {schema['minimum']}")
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required '{req}'")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                errors.extend(validate(v, props[k], f"{path}.{k}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected property '{k}'")
    return errors
