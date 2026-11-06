"""The JSON Schema of the energy_cost_stats block and its fixture corpus (task 021).

Reads files only; it does not import the integration package. The parser side of the
corpus is checked in tests/integration/test_yaml_schema_sync.py.
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "schema" / "energy_cost_stats.schema.json"
CORPUS = REPO_ROOT / "tests" / "fixtures" / "yaml_config"
FOLDERS = ("valid", "invalid_structure", "invalid_semantic")
SCHEMA_ID = (
    "https://raw.githubusercontent.com/MrKiirya/ha-energy-cost-stats/master/"
    "schema/energy_cost_stats.schema.json"
)


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def corpus_files(folder: str) -> list[Path]:
    return sorted((CORPUS / folder).glob("*.yaml"))


def iso_dates(value: Any) -> Any:
    """Editors read unquoted dates as strings; the Python loader returns ``date``."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: iso_dates(item) for key, item in value.items()}  # pyright: ignore[reportUnknownVariableType]
    if isinstance(value, list):
        return [iso_dates(item) for item in value]  # pyright: ignore[reportUnknownVariableType]
    return value


def load_fixture(path: Path) -> Any:
    return iso_dates(yaml.safe_load(path.read_text(encoding="utf-8")))


def _refs(node: Any) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():  # pyright: ignore[reportUnknownVariableType]
            if key == "$ref":
                found.append(str(value))  # pyright: ignore[reportUnknownArgumentType]
            else:
                found.extend(_refs(value))
    elif isinstance(node, list):
        for item in node:  # pyright: ignore[reportUnknownVariableType]
            found.extend(_refs(item))
    return found


def test_schema_is_valid_draft7():
    schema = load_schema()
    Draft7Validator.check_schema(schema)
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert schema["$id"] == SCHEMA_ID
    refs = _refs(schema)
    assert refs
    for ref in refs:
        assert ref.startswith("#/definitions/"), ref
        assert ref.removeprefix("#/definitions/") in schema["definitions"], ref


@pytest.mark.parametrize(
    "path",
    [path for folder in FOLDERS for path in corpus_files(folder)],
    ids=lambda path: f"{path.parent.name}/{path.stem}",
)
def test_fixture_corpus_against_schema(path: Path):
    validator = Draft7Validator(load_schema())
    errors = list(validator.iter_errors(load_fixture(path)))
    if path.parent.name == "invalid_structure":
        assert errors, f"{path.name} should be rejected by the schema"
    else:
        assert not errors, [error.message for error in errors]


def test_corpus_not_empty_and_commented():
    generic = re.compile(r"sensor\.(?:plug_|meter_|sub_meter_|\*)")
    for folder in FOLDERS:
        files = corpus_files(folder)
        assert files, folder
        for path in files:
            text = path.read_text(encoding="utf-8")
            assert text.startswith("# "), path.name
            for found in re.finditer(r"sensor\.[A-Za-z0-9_*]+", text):
                assert generic.match(found.group()), (path.name, found.group())


def test_corpus_covers_every_top_level_key():
    """Every key has a valid and an invalid_structure fixture.

    invalid_semantic/ is exempt: some keys (for example panel) have no semantic rule.
    """
    schema = load_schema()
    for folder in ("valid",):
        used: set[str] = set()
        for path in corpus_files(folder):
            document = load_fixture(path)
            if isinstance(document, dict):
                used.update(document)  # pyright: ignore[reportUnknownArgumentType]
        assert used == set(schema["properties"]), folder
    structural: set[str] = set()
    for path in corpus_files("invalid_structure"):
        document = load_fixture(path)
        if isinstance(document, dict):
            structural.update(document)  # pyright: ignore[reportUnknownArgumentType]
    assert set(schema["properties"]) <= structural
