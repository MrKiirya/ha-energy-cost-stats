"""Metadata smoke tests: manifest.json, hacs.json, custom_components/ layout."""

import ast
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CUSTOM_COMPONENTS_DIR = REPO_ROOT / "custom_components"
INTEGRATION_DIR = CUSTOM_COMPONENTS_DIR / "energy_cost_stats"


def _read_domain_const_via_ast() -> str:
    """Read DOMAIN from const.py via AST, without importing the integration package."""
    source = (INTEGRATION_DIR / "const.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "DOMAIN"
        ):
            assert isinstance(node.value, ast.Constant)
            assert isinstance(node.value.value, str)
            return node.value.value
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "DOMAIN":
                    assert isinstance(node.value, ast.Constant)
                    assert isinstance(node.value.value, str)
                    return node.value.value
    raise AssertionError("DOMAIN not found in const.py")


def test_manifest_matches_domain():
    manifest = json.loads(
        (INTEGRATION_DIR / "manifest.json").read_text(encoding="utf-8")
    )
    domain = _read_domain_const_via_ast()

    assert manifest["domain"] == domain

    required_keys = {
        "domain",
        "name",
        "version",
        "documentation",
        "issue_tracker",
        "codeowners",
        "iot_class",
        "integration_type",
    }
    assert required_keys <= manifest.keys()

    assert manifest["integration_type"] == "service"
    assert manifest["iot_class"] == "calculated"
    assert manifest["config_flow"] is True
    assert manifest["single_config_entry"] is True
    assert "recorder" in manifest["dependencies"]
    assert re.match(r"^\d+\.\d+\.\d+$", manifest["version"])


def test_hacs_json():
    hacs = json.loads((REPO_ROOT / "hacs.json").read_text(encoding="utf-8"))
    assert hacs["name"]
    assert hacs["homeassistant"] == "2025.4.0"


def test_single_integration_dir():
    subdirs = [
        p.name
        for p in CUSTOM_COMPONENTS_DIR.iterdir()
        if p.is_dir() and p.name != "__pycache__"
    ]
    assert subdirs == ["energy_cost_stats"]


def _collect_values(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from _collect_values(value)
    elif isinstance(node, list):
        for value in node:
            yield from _collect_values(value)
    else:
        yield node


def test_strings_match_en_translation():
    strings = json.loads((INTEGRATION_DIR / "strings.json").read_text(encoding="utf-8"))
    en = json.loads(
        (INTEGRATION_DIR / "translations" / "en.json").read_text(encoding="utf-8")
    )
    assert strings == en
    assert "title" not in strings
    assert "title" not in en
    for value in _collect_values(strings):
        assert "[%key:" not in str(value)


TRANSLATIONS_DIR = INTEGRATION_DIR / "translations"
TRANSLATION_FILES = sorted(TRANSLATIONS_DIR.glob("*.json"))
CYRILLIC = re.compile("[\u0400-\u04ff]")
# English values that are only a brand name or a placeholder: nothing to translate.
UNTRANSLATED_ALLOWLIST = {
    "config.step.user.title",
    "config_subentries.tariff.step.select_version.description",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten(obj, prefix: str = "") -> dict[str, str]:
    """Map dotted key paths to leaf values."""
    flat: dict[str, str] = {}
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        else:
            flat[path] = value
    return flat


def _placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{([^{}]*)\}", text))


@pytest.mark.unit
def test_russian_translation_exists():
    path = TRANSLATIONS_DIR / "ru.json"
    assert path.is_file()
    assert isinstance(_load(path), dict)


@pytest.mark.unit
@pytest.mark.parametrize("path", TRANSLATION_FILES, ids=lambda p: p.stem)
def test_translation_keys_match_strings(path):
    strings = _flatten(_load(INTEGRATION_DIR / "strings.json"))
    lang_data = _load(path)
    assert "title" not in lang_data
    lang = _flatten(lang_data)
    missing = sorted(set(strings) - set(lang))
    extra = sorted(set(lang) - set(strings))
    assert not missing, f"missing keys: {missing}"
    assert not extra, f"extra keys: {extra}"
    assert all(isinstance(v, str) for v in lang.values())


@pytest.mark.unit
@pytest.mark.parametrize("path", TRANSLATION_FILES, ids=lambda p: p.stem)
def test_translation_placeholders_match_strings(path):
    strings = _flatten(_load(INTEGRATION_DIR / "strings.json"))
    lang = _flatten(_load(path))
    mismatched = {
        key: (sorted(_placeholders(strings[key])), sorted(_placeholders(lang[key])))
        for key in strings
        if key in lang and _placeholders(lang[key]) != _placeholders(strings[key])
    }
    assert not mismatched, f"placeholder mismatch (expected, actual): {mismatched}"


def _hassfest_problems(values: dict[str, str]) -> list[str]:
    problems = []
    for key, value in values.items():
        if not isinstance(value, str) or not value:
            problems.append(f"{key}: empty or not a string")
            continue
        if "[%key:" in value:
            problems.append(f"{key}: key reference")
        if re.search(r"<[a-zA-Z/][^>]*>", value):
            problems.append(f"{key}: HTML")
        if re.search(r"'\{", value):
            problems.append(f"{key}: placeholder in single quotes")
        if not all(name.isidentifier() for name in _placeholders(value)):
            problems.append(f"{key}: placeholder name is not an identifier")
        if value != value.strip():
            problems.append(f"{key}: leading or trailing whitespace")
    return problems


@pytest.mark.unit
@pytest.mark.parametrize(
    "path", [INTEGRATION_DIR / "strings.json", *TRANSLATION_FILES], ids=lambda p: p.name
)
def test_translation_values_pass_hassfest_rules(path):
    assert _hassfest_problems(_flatten(_load(path))) == []


@pytest.mark.unit
def test_russian_values_are_translated():
    ru = _flatten(_load(TRANSLATIONS_DIR / "ru.json"))
    assert ru
    untranslated = sorted(
        key
        for key, value in ru.items()
        if key not in UNTRANSLATED_ALLOWLIST and not CYRILLIC.search(value)
    )
    assert not untranslated, f"no Cyrillic text in: {untranslated}"
