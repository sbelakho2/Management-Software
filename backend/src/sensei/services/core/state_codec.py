"""State serialization helpers for in-memory services.

Provides a lightweight encoder/decoder for dataclasses and common domain
primitives (UUID, datetime, date, Decimal, Enum) to round-trip through
JSON persistence.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Union, get_args, get_origin
import types
from uuid import UUID


def encode_value(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return encode_dataclass(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {encode_value(k): encode_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [encode_value(v) for v in value]
    return value


def encode_dataclass(obj: Any) -> dict[str, Any]:
    if not is_dataclass(obj):
        raise TypeError("encode_dataclass expects a dataclass instance")
    return {field.name: encode_value(getattr(obj, field.name)) for field in fields(obj)}


def _decode_union(value: Any, type_hint: Any) -> Any:
    args = [arg for arg in get_args(type_hint) if arg is not type(None)]
    if value is None:
        return None
    for arg in args:
        try:
            return decode_value(value, arg)
        except Exception:
            continue
    return value


def decode_value(value: Any, type_hint: Any) -> Any:
    if value is None:
        return None

    origin = get_origin(type_hint)
    if origin in (Union, types.UnionType):
        return _decode_union(value, type_hint)
    if origin is list:
        (item_type,) = get_args(type_hint) or (Any,)
        return [decode_value(v, item_type) for v in value]
    if origin is set:
        (item_type,) = get_args(type_hint) or (Any,)
        return {decode_value(v, item_type) for v in value}
    if origin is tuple:
        args = get_args(type_hint) or (Any,)
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(decode_value(v, args[0]) for v in value)
        return tuple(decode_value(v, t) for v, t in zip(value, args))
    if origin is dict:
        key_type, val_type = get_args(type_hint) or (Any, Any)
        return {decode_value(k, key_type): decode_value(v, val_type) for k, v in value.items()}
    if origin is None and getattr(type_hint, "__origin__", None) is None:
        if is_dataclass(type_hint):
            return decode_dataclass(value, type_hint)
    if origin is None and hasattr(type_hint, "__mro__"):
        if issubclass(type_hint, Enum):
            return type_hint(value)
        if issubclass(type_hint, UUID):
            return UUID(value)
        if issubclass(type_hint, datetime):
            return datetime.fromisoformat(value)
        if issubclass(type_hint, date):
            return date.fromisoformat(value)
        if issubclass(type_hint, Decimal):
            return Decimal(value)
        return value
    if origin is None and getattr(type_hint, "__origin__", None) is None and type_hint is Any:
        return value
    if origin is None and getattr(type_hint, "__origin__", None) is None and getattr(type_hint, "__module__", None) == "typing":
        return value
    return value


def decode_dataclass(data: dict[str, Any], cls: type[Any]) -> Any:
    if not is_dataclass(cls):
        raise TypeError("decode_dataclass expects a dataclass class")
    kwargs: dict[str, Any] = {}
    for field in fields(cls):
        if field.name in data:
            kwargs[field.name] = decode_value(data[field.name], field.type)
    return cls(**kwargs)
