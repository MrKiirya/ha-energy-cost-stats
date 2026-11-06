"""The JSON Schema stays in sync with the YAML parser (task 021).

Tests: the shared fixture corpus, the accepted keys per mapping, and the enums.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from homeassistant.util.yaml import dump, parse_yaml
from jsonschema import Draft7Validator

from custom_components.energy_cost_stats.engine.presets import PRESET_ZONES
from custom_components.energy_cost_stats.engine.sensors import SensorMode
from custom_components.energy_cost_stats.yaml_config import (
    ACCEPTED_KEYS,
    YamlConfigError,
    document_from_yaml,
    export_document,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads(
    (REPO_ROOT / "schema" / "energy_cost_stats.schema.json").read_text(encoding="utf-8")
)
CORPUS = REPO_ROOT / "tests" / "fixtures" / "yaml_config"
DEFAULT_SENSORS: dict[str, Any] = {
    "mode": "filter",
    "include": "all",
    "exclude": {},
    "overrides": {},
}


def _from_text(text: str) -> Any:
    return parse_yaml(text)


def _iso(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _iso(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_iso(item) for item in value]
    return value


def _parse(folder: str, path: Path) -> Any:
    return parse_yaml(path.read_text(encoding="utf-8"))


def _fixtures(folder: str) -> list[Path]:
    return sorted((CORPUS / folder).glob("*.yaml"))


def _load(raw: Any) -> Any:
    return document_from_yaml(
        raw, default_time_zone="Europe/Berlin", default_sensors=DEFAULT_SENSORS
    )


@pytest.mark.parametrize("path", _fixtures("valid"), ids=lambda path: path.stem)
def test_valid_corpus_is_accepted_by_the_parser(path: Path):
    _load(_parse("valid", path))


@pytest.mark.parametrize(
    "path",
    _fixtures("invalid_structure") + _fixtures("invalid_semantic"),
    ids=lambda path: f"{path.parent.name}/{path.stem}",
)
def test_invalid_corpus_is_rejected_by_the_parser(path: Path):
    with pytest.raises(YamlConfigError):
        _load(_parse(path.parent.name, path))


def test_corpus_against_parser():
    """Every folder is non-empty, so the parametrized tests above are not vacuous."""
    for folder in ("valid", "invalid_structure", "invalid_semantic"):
        assert _fixtures(folder), folder


def _resolve(node: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in node:
        node = SCHEMA["definitions"][node["$ref"].removeprefix("#/definitions/")]
    return node


def _child(node: dict[str, Any], key: str) -> dict[str, Any]:
    """The schema under ``key`` of the node or of one of its ``oneOf`` options."""
    for candidate in [node, *(_resolve(option) for option in node.get("oneOf", []))]:
        if key in candidate:
            return candidate[key]
    raise KeyError(key)


def _node_at(path: str) -> dict[str, Any]:
    node = _resolve(SCHEMA)
    for segment in [part for part in path.split("/") if part]:
        if segment == "*":
            try:
                node = _resolve(_child(node, "items"))
            except KeyError:
                node = _resolve(_child(node, "additionalProperties"))
        else:
            node = _resolve(_child(node, "properties")[segment])
    for option in node.get("oneOf", []):
        # A value that is either a keyword or a mapping: follow the mapping.
        if "properties" in _resolve(option):
            return _resolve(option)
    return node


def _closed_objects(node: dict[str, Any], path: str, found: set[str]) -> None:
    """Paths of every schema object with ``additionalProperties: false``."""
    node = _resolve(node)
    if node.get("additionalProperties") is False:
        found.add(path)
    for name, child in node.get("properties", {}).items():
        _closed_objects(child, f"{path}/{name}", found)
    if "items" in node:
        _closed_objects(node["items"], f"{path}/*", found)
    additional = node.get("additionalProperties")
    if isinstance(additional, dict):
        _closed_objects(additional, f"{path}/*", found)  # pyright: ignore[reportUnknownArgumentType]
    for key in ("oneOf", "anyOf", "allOf"):
        for option in node.get(key, []):
            _closed_objects(option, path, found)
    for key in ("if", "then", "else", "not"):
        if key in node:
            _closed_objects(node[key], path, found)


def test_schema_keys_match_parser():
    for path, keys in ACCEPTED_KEYS.items():
        node = _node_at(path)
        assert node.get("additionalProperties") is False, path
        assert set(node["properties"]) == set(keys), path
    found: set[str] = set()
    _closed_objects(SCHEMA, "", found)
    assert found == set(ACCEPTED_KEYS)


def test_schema_enums_match_code():
    mode = _node_at("/sensors")["properties"]["mode"]
    assert set(mode["enum"]) == {item.value for item in SensorMode}
    preset = _node_at("/tariffs/*/versions/*")["properties"]["preset"]
    assert set(preset["enum"]) == set(PRESET_ZONES)


def test_schema_validates_exports():
    """The full export of the design example (options and tariffs) is a valid block."""
    document = _load(_parse("valid", CORPUS / "valid" / "full_example.yaml"))
    text = dump(
        {"energy_cost_stats": export_document(document.options, document.tariffs)}
    )
    block = _from_text(text)["energy_cost_stats"]
    errors = list(Draft7Validator(SCHEMA).iter_errors(_iso(block)))
    assert not errors, [error.message for error in errors]
