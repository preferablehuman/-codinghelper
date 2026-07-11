import json
from typing import Any


def parse_json_object(text: str, *, wrapper_keys: tuple[str, ...] = ()) -> dict[str, Any]:
    value = _parse_first_json_value(text)
    value = _unwrap_single_object(value)
    if isinstance(value, dict):
        for key in wrapper_keys:
            nested = _unwrap_single_object(value.get(key))
            if isinstance(nested, dict):
                return nested
    if not isinstance(value, dict):
        raise ValueError(f"Model response must contain a JSON object, got {type(value).__name__}.")
    return value


def parse_json_array(text: str) -> list[Any]:
    value = _parse_first_json_value(text)
    if not isinstance(value, list):
        raise ValueError(f"Model response must contain a JSON array, got {type(value).__name__}.")
    return value


def require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Model response field '{key}' must be a non-empty string.")
    return value.strip()


def optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value).strip()


def _parse_first_json_value(text: str) -> Any:
    decoder = json.JSONDecoder()
    stripped = text.strip()
    for index, char in enumerate(stripped):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(stripped[index:])
            return value
        except json.JSONDecodeError:
            continue
    raise ValueError("Model response did not contain valid JSON.")


def _unwrap_single_object(value: Any) -> Any:
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        return value[0]
    return value


def response_preview(text: str, limit: int = 1200) -> str:
    preview = " ".join(text.strip().split())
    if len(preview) <= limit:
        return preview
    return f"{preview[:limit]}..."
