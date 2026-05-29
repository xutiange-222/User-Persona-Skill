from __future__ import annotations

import re


class ValidationError(Exception):
    pass


def validate(instance, schema):
    _validate(instance, schema, "$", root=schema)


class Draft202012Validator:
    @staticmethod
    def check_schema(schema):
        if not isinstance(schema, dict):
            raise ValidationError("schema must be an object")


def _type_ok(value, expected):
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _validate(instance, schema, path, root):
    if not isinstance(schema, dict):
        return

    if "enum" in schema and instance not in schema["enum"]:
        raise ValidationError(f"{path}: {instance!r} not in enum {schema['enum']!r}")

    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        if not any(_type_ok(instance, t) for t in expected_type):
            raise ValidationError(f"{path}: expected one of {expected_type}, got {type(instance).__name__}")
    elif expected_type and not _type_ok(instance, expected_type):
        raise ValidationError(f"{path}: expected {expected_type}, got {type(instance).__name__}")

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                raise ValidationError(f"{path}: missing required property {key!r}")

        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = set(instance) - set(props)
            if extra:
                raise ValidationError(f"{path}: additional properties not allowed: {sorted(extra)!r}")

        for key, value in instance.items():
            if key in props:
                _validate(value, props[key], f"{path}.{key}", root)

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            raise ValidationError(f"{path}: expected at least {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise ValidationError(f"{path}: expected at most {schema['maxItems']} items")
        item_schema = schema.get("items")
        if item_schema:
            for idx, item in enumerate(instance):
                _validate(item, item_schema, f"{path}[{idx}]", root)

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            raise ValidationError(f"{path}: string shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            raise ValidationError(f"{path}: string longer than {schema['maxLength']}")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise ValidationError(f"{path}: {instance!r} does not match pattern {schema['pattern']!r}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise ValidationError(f"{path}: {instance!r} below minimum {schema['minimum']!r}")
        if "maximum" in schema and instance > schema["maximum"]:
            raise ValidationError(f"{path}: {instance!r} above maximum {schema['maximum']!r}")
