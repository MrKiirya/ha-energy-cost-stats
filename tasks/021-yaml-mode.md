# 021 — YAML mode: `energy_cost_stats:` block, JSON Schema, read-only UI, reload action, repairs, export to YAML

Status: in-review (round 1: CHANGES_REQUESTED; round 2: APPROVE)
Roadmap: stage 4 follow-up (configuration v2, docs/CONFIG-DESIGN.md "Tasks" row 021)
Spec sections: SPEC §2 (settings, config / options flow, services), §3 (tariff storage as subentries, applied,
compare), §6 (compatibility); docs/CONFIG-DESIGN.md "Full configuration (YAML)", "Tariffs" (prices as decimal
strings, numbers accepted in YAML), "Modes", "Configure (options)" (Export to YAML, read-only in YAML mode)

## Goal
The whole configuration can live in `configuration.yaml` (or a package, or a file pulled in with `!include`)
under `energy_cost_stats:`, with **exactly the document shape the UI edits** (CONFIG-DESIGN "Full configuration
(YAML)"). When the block is present it is the single source of truth: it is validated strictly, written into the
single config entry (options + one `tariff` subentry per tariff), and the UI shows it read-only. Edits to the file
are applied without a restart through the admin action `energy_cost_stats.reload`, which also appears in Developer
tools → YAML. An invalid block never takes the integration down: the last valid configuration keeps running, and
the error is shown as a repair issue, in the log and (for a reload) as the action error. In both modes the options
menu gains **Export to YAML**, which shows the current configuration as a ready-to-copy `energy_cost_stats:` block
that loads back unchanged. A committed **JSON Schema** of the block gives editors (VS Code YAML extension, the
Studio Code Server add-on) validation and completion; tests keep it in sync with the integration's parser.

## Dependencies
- Stacked on 017–020. Reuses unchanged: `settings.settings_from_options` / `settings_to_options` (strict parse of
  `entry.options`), `settings.tariff_document`, `engine.tariff_config.config_from_data` (strict tariff document
  parse, already accepts `date` objects and the `applied: <id>` short form), the `tariff` subentry shape
  (`{"id", "name", "versions"}`, `unique_id` = tariff id, `title` = name, task 018),
  `sensor_resolver.async_default_sensor_settings` / `describe_selection`, the 019 applied-history table helper.
- No change to the stored format and **no config entry version bump**: YAML mode writes the same options and
  subentries the UI writes.
- Size: above the usual ≤ 10 files because the JSON Schema was added to this task on request. The schema part
  (`schema/`, its fixtures and tests, docs) is self-contained; implement it **last**, and if the run gets long it
  can be split into a follow-up task without changing anything else here.

## Context
### Design decisions (this task)
- **YAML is imported into the config entry, not read beside it.** Reports, websocket, service and the card keep
  one code path (`entry.runtime_data`), the integration page lists the YAML tariffs as subentries, and Export
  works the same in both modes. "YAML mode" is a runtime flag (YAML block present at the last load), not stored.
- **Lenient `CONFIG_SCHEMA`, strict validation in our code.** If `CONFIG_SCHEMA` raises, Home Assistant does not
  call `async_setup` and does not set up the config entries of the domain at all (verified below). Therefore
  `CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): object}, extra=vol.ALLOW_EXTRA)` (replaces
  `cv.empty_config_schema(DOMAIN)`), and every real check is ours, reported as a repair issue.
- **Pure normalizer** `yaml_config.py` (top-level module, no `homeassistant` imports, like `settings.py`):
  YAML values → the stored JSON shape, then strict validation by the existing parsers. Time-zone existence is
  checked in the HA layer (`dt_util.async_get_time_zone`), like `async_setup_entry` does today.

### YAML → stored shape (`yaml_config.document_from_yaml(raw, *, default_time_zone, default_sensors)`)
Returns `YamlDocument(options: dict, tariffs: tuple[dict, ...])`; raises `YamlConfigError(message)` with a
message that names the path (e.g. `tariffs[1].versions[0].prices.t1: must be a decimal`).
- `raw is None` (bare `energy_cost_stats:`) is an empty mapping; any non-mapping → error. Top-level keys:
  `time_zone`, `spike_limit`, `panel`, `sensors`, `tariffs`, `applied`, `compare`; unknown keys → error.
- `time_zone` optional → `default_time_zone` (HA layer: the existing entry's stored time zone, else
  `hass.config.time_zone`, per CONFIG-DESIGN "stored explicitly").
- `spike_limit` optional → `DEFAULT_SPIKE_LIMIT`; `null` = disabled.
- `panel` optional (absent = not configured); inside, `show` / `title` / `icon` each optional with
  `DEFAULT_PANEL_*`.
- `sensors` optional → `default_sensors` (HA layer: `async_default_sensor_settings(hass)`); inside, `exclude` and
  `overrides` default to `{}`; in `filter` mode a missing `include` means `all` (see open questions).
- `tariffs` optional (default `[]`), each item exactly as stored (`id`, `name`, `versions`).
- `applied` optional: list form, or the short form `applied: <id>` → `[{"from": <first valid_from>, "tariff":
  <id>}]` (same rule as `config_from_data`; unknown id → error).
- `compare` optional (absent = default).
- **Conversions:** decimal fields (`spike_limit`, `sensors.overrides.*.spike_limit`, `versions[].prices.*`,
  `versions[].zones[].price`) accept `int` / `float` (not `bool`) and become normalized decimal strings
  (`format(Decimal(str(value)), "f")`, so `8.1` → `"8.1"`, `1e-05` → `"0.00001"`); strings are kept as they are.
  Date fields (`versions[].valid_from`, `applied[].from`) accept `datetime.date` (Home Assistant's YAML loader
  returns `date` for unquoted `2026-01-01`) or `YYYY-MM-DD` strings and are stored as ISO strings; `datetime` →
  error. Nothing else is coerced.
- **Strict validation:** `settings_from_options(options)` and `config_from_data(tariff_document(...))`; their
  `SettingsError` / `TariffValidationError` messages become the `YamlConfigError` message. Duplicate tariff ids
  are rejected by `config_from_data`.
- **Accepted keys are public:** `yaml_config.ACCEPTED_KEYS: Mapping[str, frozenset[str]]` maps a JSON-pointer-like
  path of every mapping in the document (`""`, `/panel`, `/sensors`, `/sensors/include`, `/sensors/exclude`,
  `/sensors/overrides/*`, `/tariffs/*`, `/tariffs/*/versions/*`, `/tariffs/*/versions/*/zones/*`, `/applied/*`) to
  the keys the parser accepts there, built from the existing constants (`settings._KNOWN_KEYS`, `TARGET_KEYS`,
  `tariff_config._TARIFF_KEYS` / `_VERSION_KEYS` / `_ZONE_KEYS` / `_APPLIED_KEYS`; expose them under public
  names). The normalizer itself uses it for unknown-key checks, and the schema sync test compares it with the
  JSON Schema.

### Stored shape → YAML (`yaml_config.export_document(options, tariff_data) -> dict`)
Key order: `time_zone`, `spike_limit`, `panel` (only if stored), `sensors`, `tariffs`, `applied` (list form, only
if non-empty), `compare` (only if stored). Dates are emitted as `datetime.date` (unquoted in YAML, as in the
design example); prices and limits stay strings (quoted, as CONFIG-DESIGN recommends). The HA layer renders
`{"energy_cost_stats": export_document(...)}` with `homeassistant.util.yaml.dump` (block style, key order kept,
`allow_unicode=True`; `null` values are written as an empty value, which loads back as `None`). **Round trip:**
`document_from_yaml(parse_yaml(rendered)[DOMAIN], ...)` reproduces the stored options and tariff data exactly.
The export description also shows the schema modeline (see "JSON Schema") as a hint for the split-file setup.

### Runtime flow (HA layer `yaml_mode.py`)
- `DATA_YAML: HassKey[YamlState]`; `YamlState(present: bool, document: YamlDocument | None, error: str | None)`.
- `async_setup(hass, config)`: `state = await async_load_yaml_state(hass, config)`; register the reload action;
  then `await async_apply_yaml_state(hass, state)` (below). The websocket command, `get_report` and the card are
  registered as today.
- `async_apply_yaml_state(hass, state)` (startup and reload):
  1. Block absent → `present=False`; delete issue `invalid_yaml`; if an entry exists and was in YAML mode, reload
     it (it stays configured with the last YAML values, now editable in the UI).
  2. Block present but invalid → `present=True, error=<message>`; create issue `invalid_yaml`
     (`severity=ERROR`, `is_fixable=False`, `translation_key="invalid_yaml"`, placeholder `error`); log an error.
     The entry is **not** touched (keeps running its last valid configuration).
  3. Block present and valid → delete the issue; no entry → start the import flow
     (`hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_IMPORT}, data=document.options)`);
     entry exists → `hass.config_entries.async_reload(entry_id)` (on startup the entry is set up after
     `async_setup` anyway, so no reload then).
- `async_setup_entry`: when `DATA_YAML` holds a valid document, **sync first** (before parsing options and before
  adding the update listener): `async_update_entry(entry, options=document.options)` if different; tariff
  subentries matched by `unique_id` (tariff id): `async_update_subentry(data=..., title=name)` if different,
  `async_add_subentry` for new ids, `async_remove_subentry` for ids no longer in YAML. No reordering of existing
  subentries (Export follows subentry order). When an existing UI configuration is replaced for the first time a
  warning is logged ("YAML configuration replaces the configuration made in the UI").
- `_async_update_listener` in YAML mode: **skip `_async_reconcile`** (it would edit options that YAML owns) and
  just reload; the reload re-syncs, so a tariff subentry deleted from the integration page comes back.
- `energy_cost_stats.reload` (admin, no fields): `async_integration_yaml_config(hass, DOMAIN)`; a YAML syntax error
  (`HomeAssistantError`) or a `None` result → treat as invalid (issue + log), then raise
  `HomeAssistantError(translation_domain=DOMAIN, translation_key="yaml_invalid", translation_placeholders={"error":
  ...})` so Developer tools show the failure; otherwise `async_apply_yaml_state`. Registered in `async_setup` even
  without a YAML block, so a block added later is picked up without a restart.

### UI in YAML mode
- **Config flow:** `async_step_import(import_data)` → `async_create_entry(title=DEFAULT_TITLE, data={},
  options=import_data)` (single instance via `single_config_entry`; a second flow aborts
  `single_instance_allowed`). `async_step_user` aborts `yaml_mode` when a YAML block is present (e.g. the block
  is invalid and no entry exists yet).
- **Options flow:** `init` in YAML mode → step `yaml_mode` (menu). Description: "configured in YAML, edit the file
  and run `energy_cost_stats.reload`", the current time zone, spike limit, compare list and sidebar settings as
  placeholders, and — when the last load failed — the error (`{error}`, empty otherwise). Options:
  `sensors_view`, `applied_view`, `export_yaml`.
  - `sensors_view` (menu): `{count}` / `{sensors}` from `describe_selection` for the stored selection; option
    `yaml_mode` (back).
  - `applied_view` (menu): the 019 history table rows in `{history}`; option `yaml_mode` (back).
  - No step in YAML mode writes options (`async_create_entry` is never reached).
- **UI mode:** `MENU_STEPS` becomes `("sensors", "applied", "compare", "general", "export_yaml")`.
- **`export_yaml`** (menu, both modes): description contains a fenced block in `strings.json`
  (```` ```yaml ```` / `{yaml}` / ```` ``` ````) with the rendered YAML in the `{yaml}` placeholder, and a hint
  that pasting it into `configuration.yaml` switches to YAML mode; option `init` (back). Template text must not
  contain apostrophes (ICU message format escape character).
- **Tariff subentry flow** (`tariff_flow.py`): `async_step_user` and `async_step_reconfigure` abort `yaml_mode` in
  YAML mode. Deleting a subentry cannot be blocked (Home Assistant's own action); it is undone by the re-sync.

### JSON Schema (editor validation and completion)
- **File:** `schema/energy_cost_stats.schema.json` at the repository root (committed, versioned with the
  integration; not inside `custom_components/`, because Home Assistant never reads it and HACS should not ship it).
  `$id` = `https://raw.githubusercontent.com/MrKiirya/ha-energy-cost-stats/master/schema/energy_cost_stats.schema.json`.
  Users who want a schema matching an installed release use the tag instead of `master` in the URL
  (`.../v<version>/schema/...`); SPEC says so.
- **Root = the block content** (the mapping under `energy_cost_stats:`), so it applies directly to a split file.
- **Draft-07** (`"$schema": "http://json-schema.org/draft-07/schema#"`). yaml-language-server supports draft-04,
  draft-07, 2019-09 and 2020-12, but draft-07 is the most widely supported draft across editor plugins (including
  older bundled versions) and Python's `jsonschema` (`Draft7Validator`); the schema needs nothing newer
  (`definitions` + `$ref`, `oneOf`, `if` / `then` for the mode-dependent `include`, `patternProperties`).
- **How users attach it** (documented in SPEC and the README):
  ```yaml
  # configuration.yaml
  energy_cost_stats: !include energy_cost_stats.yaml
  ```
  ```yaml
  # energy_cost_stats.yaml
  # yaml-language-server: $schema=https://raw.githubusercontent.com/MrKiirya/ha-energy-cost-stats/master/schema/energy_cost_stats.schema.json
  time_zone: Europe/Berlin
  tariffs: []
  ```
  The `# yaml-language-server: $schema=<url-or-path>` modeline at the top of the file associates the schema;
  relative paths resolve from the YAML file's location (yaml-language-server README). `!secret` / `!include`
  inside the file need `yaml.customTags` (e.g. `"!secret scalar"`) in the editor settings, or the extension
  reports unknown tags; whether the Studio Code Server add-on preconfigures Home Assistant's tags is **not
  verified** — SPEC tells users to add them if needed. Inline in `configuration.yaml` the schema cannot be
  attached to a single key (a modeline applies to the whole file), hence the split-file recommendation.
- **Hand-written, not generated — justification.** There is no single declarative source to generate from:
  `CONFIG_SCHEMA` is deliberately lenient (see above), and the real rules live in imperative parsers
  (`yaml_config`, `settings`, `engine.tariff_config`). Generating from voluptuous would produce an empty schema;
  introducing a declarative model (pydantic, voluptuous-openapi) only for this would add a runtime dependency or a
  second source of truth. A hand-written schema is also where editor-facing `description`s, `enum`s for presets /
  modes / zone keys, `default`s and `examples` belong. Drift is prevented by tests (below), not by generation.
- **Structure only.** The schema checks keys, types, required keys, enums (`mode`, `preset`), patterns (tariff id
  `^[a-z0-9_]{1,32}$`, `YYYY-MM-DD`, glob characters, hours text `HH:MM-HH:MM[, ...]`), `include` allowed only with
  `mode: filter`, `preset` xor `zones`. **Semantic rules stay in the engine** and are not duplicated: hours
  covering the day exactly once, sorted / distinct `valid_from`, prices for exactly the inherited zone keys,
  `applied` referencing existing tariffs with a valid version, unique tariff ids, `compare` ids existing,
  existing time zones. The schema `description` of the root says so.
- **Value types in the schema** follow what YAML editors see: prices and limits `["string", "number"]` (strings
  matching a decimal pattern); dates `string` with the date pattern (yaml-language-server parses YAML 1.2, where
  an unquoted date is a string). The Python tests convert loader `date` objects to ISO strings before schema
  validation.
- **Sync guarantees** (tests, see table):
  1. Shared fixture corpus `tests/fixtures/yaml_config/`: `valid/*.yaml` (accepted by both the schema and
     `document_from_yaml`), `invalid_structure/*.yaml` (rejected by both), `invalid_semantic/*.yaml` (accepted by
     the schema, rejected by the parser — documents the boundary). Every fixture has a one-line comment saying what
     it covers; generic ids only. The CONFIG-DESIGN example is `valid/full_example.yaml`.
  2. Key coverage: for every path in `yaml_config.ACCEPTED_KEYS` the schema node at that path has
     `additionalProperties: false` and exactly those `properties` (both directions), so a key added to the parser
     without the schema (or vice versa) fails the test.
  3. Enum coverage: schema `mode` enum == `SensorMode` values, `preset` enum == `PRESET_ZONES` keys.
  4. The schema itself is valid draft-07 (`Draft7Validator.check_schema`) and every `$ref` resolves.
  5. Every Export rendered in `test_export_round_trip` validates against the schema.
- **Tooling:** add `jsonschema>=4` to the `dev` dependency group (`uv add --dev jsonschema`); the pure schema tests
  (1 without the parser half, 3–4 via fixtures only) run as `unit` on Windows too (they read files and do not
  import the integration package); the parser-vs-schema tests are `integration` (importing `yaml_config` pulls in
  the package `__init__`, which needs HA).

### Home Assistant and tooling APIs checked (minimum 2025.4.0 and current `dev`, 2026-11-07)
- **Invalid `CONFIG_SCHEMA` aborts the whole integration.** `setup.py::_async_setup_component` at 2025.4.0: when
  the processed config is `None` it logs "Invalid config." and returns `False` before `async_setup` and before
  the config entries of the domain are set up. Source:
  [setup.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/setup.py).
  → lenient schema (above).
- **Reload helper:** `homeassistant.helpers.reload.async_integration_yaml_config(hass, integration_name, *,
  raise_on_failure=False) -> ConfigType | None` — loads `configuration.yaml` (`conf_util.async_hass_config_yaml`)
  and runs it through the integration's `CONFIG_SCHEMA` (`async_process_component_and_handle_errors`); identical
  at 2025.4.0 and `dev`. With a lenient schema the only failures are YAML syntax / include errors. Sources:
  [helpers/reload.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/helpers/reload.py),
  [@dev](https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/reload.py).
  `async_setup_reload_service` is for platform-based integrations and is **not** used.
- **Admin action:** `homeassistant.helpers.service.async_register_admin_service(hass, domain, service,
  service_func, schema=vol.Schema({}, extra=vol.PREVENT_EXTRA))` (`@callback`), raises `Unauthorized` for
  non-admin users. Source:
  [helpers/service.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/helpers/service.py).
  Developer tools → YAML lists the integrations that register an action named `reload` (community-documented,
  [forum](https://community.home-assistant.io/t/reload-option-missing/755780); **unverified in frontend source** —
  check manually in the dev HA). `services.yaml` needs a `reload:` entry and `strings.json` a `services.reload`
  name / description (hassfest).
- **Repairs:** `homeassistant.helpers.issue_registry.async_create_issue(hass, domain, issue_id, *,
  breaks_in_ha_version=None, data=None, is_fixable, is_persistent=False, issue_domain=None, learn_more_url=None,
  severity: IssueSeverity, translation_key, translation_placeholders=None)` and `async_delete_issue(hass, domain,
  issue_id)`; `IssueSeverity.CRITICAL | ERROR | WARNING`. Translations under `issues.<key>.title|description`.
  Source: [helpers/issue_registry.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/helpers/issue_registry.py).
  Not persistent (re-created on every failed load).
- **Config entries / subentries (2025.4.0):** `SOURCE_IMPORT = "import"`; `ConfigEntries.async_add_subentry(entry,
  subentry) -> bool`, `async_remove_subentry(entry, subentry_id) -> bool`, `async_update_subentry(entry, subentry,
  *, data=, title=, unique_id=) -> bool`, `async_update_entry(entry, *, options=, title=, ...)`; a flow for a
  `single_config_entry` domain aborts `single_instance_allowed` when an entry exists (import included). Whether
  `ConfigFlow.async_create_entry` accepts `subentries=` at 2025.4.0 was **not verified** → the import flow creates
  options only and `async_setup_entry` adds the subentries. Source:
  [config_entries.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/config_entries.py).
- **YAML dump / parse:** `homeassistant.util.yaml` exports `dump`, `parse_yaml`, `load_yaml` (from
  `annotatedyaml`) at 2025.4.0; `dump` = `yaml.dump(default_flow_style=False, allow_unicode=True, sort_keys=False,
  Dumper=<C>SafeDumper)` with `": null\n"` replaced by `":\n"`. Sources:
  [util/yaml/__init__.py @2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/util/yaml/__init__.py),
  [annotatedyaml dumper.py](https://github.com/home-assistant-libs/annotatedyaml/blob/main/src/annotatedyaml/dumper.py).
  The loader returning `datetime.date` for unquoted dates and `float` for unquoted prices is asserted by a test
  (`test_yaml_loader_types`) rather than assumed.
- **Flow descriptions** are rendered as Markdown with placeholders substituted (already relied on by 019's tables).
  A fenced code block inside a description has **no copy button** in the frontend as far as known (unverified);
  the user selects the text. Check the rendering manually in the dev HA.
- **Packages:** with a mapping value under `energy_cost_stats:` in two packages Home Assistant's package merge
  combines or rejects duplicate keys before our code sees it; not specially handled (unverified, manual check).
- **yaml-language-server** (engine of the VS Code YAML extension): modeline
  `# yaml-language-server: $schema=<schema-url-or-path>` at the top of the file; relative paths resolve from the
  YAML file's location; supported drafts draft-04, draft-07, 2019-09, 2020-12; custom tags via `yaml.customTags`
  (`"!tag scalar|sequence|mapping"`). Source:
  [yaml-language-server README](https://github.com/redhat-developer/yaml-language-server/blob/main/README.md).
- Constraints from 019 / 020 still apply (menus without `sort=` / `menu_option_descriptions`, always pass
  `step_id`, one update listener).

## Files
- create: `custom_components/energy_cost_stats/yaml_config.py` — pure: `YamlConfigError`, `YamlDocument`,
  `ACCEPTED_KEYS`, `document_from_yaml`, `export_document` (no `homeassistant` imports).
- create: `custom_components/energy_cost_stats/yaml_mode.py` — HA layer: `DATA_YAML`, `YamlState`,
  `async_load_yaml_state`, `async_apply_yaml_state`, `async_sync_entry`, `async_register_reload_service`,
  `render_yaml`, issue create / delete, `is_yaml_mode(hass)`.
- modify: `custom_components/energy_cost_stats/__init__.py` — lenient `CONFIG_SCHEMA`; `async_setup` loads and
  applies the YAML state and registers `reload`; `async_setup_entry` syncs from YAML first; listener skips
  reconcile in YAML mode.
- modify: `custom_components/energy_cost_stats/config_flow.py` — `async_step_import`; `user` aborts `yaml_mode`;
  options steps `yaml_mode`, `sensors_view`, `applied_view`, `export_yaml`; `init` dispatch by mode.
- modify: `custom_components/energy_cost_stats/tariff_flow.py` — abort `yaml_mode` in `user` / `reconfigure`.
- modify: `custom_components/energy_cost_stats/settings.py`, `engine/tariff_config.py` — expose the accepted key
  sets under public names (no behaviour change).
- modify: `custom_components/energy_cost_stats/const.py` — `SERVICE_RELOAD`, `ISSUE_INVALID_YAML`, `SCHEMA_URL`,
  `MENU_STEPS` + `export_yaml`, YAML-mode step ids.
- modify: `custom_components/energy_cost_stats/services.yaml` — `reload:`.
- modify: `custom_components/energy_cost_stats/strings.json`, `translations/en.json` — `services.reload`,
  `issues.invalid_yaml`, `exceptions.yaml_invalid`, options steps / menu options above, aborts `yaml_mode` in
  `config.abort`, `options.abort`, `config_subentries.tariff.abort`.
- create: `schema/energy_cost_stats.schema.json` — hand-written draft-07 schema of the block content.
- create: `tests/fixtures/yaml_config/{valid,invalid_structure,invalid_semantic}/*.yaml` — shared corpus.
- create: `tests/unit/test_config_schema.py` (schema-only checks), `tests/integration/test_yaml_config.py`,
  `tests/integration/test_yaml_schema_sync.py`, `tests/integration/test_yaml_mode.py`; modify
  `tests/integration/test_options_menu.py` (menu list, strings completeness), `tests/unit/test_engine_isolation.py`
  (also guard `settings.py` and `yaml_config.py`).
- modify: `pyproject.toml` / `uv.lock` — `jsonschema>=4` in the `dev` group.
- modify: `docs/SPEC.md` — §2 (YAML mode, reload action, import into the entry, read-only options, Export), §3
  (YAML conversions), §6 table (lenient schema and why; reload helper; issue registry), new subsection "JSON
  Schema" (location, draft, attaching it, structure-only scope, release-tag URLs, sync tests);
  `docs/CONFIG-DESIGN.md` "Modes" trimmed to point at SPEC; `README.md` — short "YAML configuration" section with
  the split-file example and the modeline; `CLAUDE.md` — one line under Test levels / conventions: "a key added to
  the YAML parser must be added to `schema/energy_cost_stats.schema.json` (enforced by `test_yaml_schema_sync`)".

Suggested order (each step green before the next): `yaml_config.py` → `yaml_mode.py` + `__init__.py` →
reload action + repairs → flows → strings → JSON Schema + fixtures + sync tests → docs.

## Tests to write first
| Level | Test | Asserts |
|---|---|---|
| unit | `tests/unit/test_engine_isolation.py::test_settings_and_yaml_config_have_no_ha_imports` | `settings.py` and `yaml_config.py` contain no `homeassistant` imports (reuse `find_forbidden_engine_imports`) |
| unit | `tests/unit/test_config_schema.py::test_schema_is_valid_draft7` | `Draft7Validator.check_schema` passes; `$schema` is draft-07; `$id` is the raw `master` URL; every `$ref` resolves |
| unit | `test_config_schema.py::test_fixture_corpus_against_schema` | parametrized over the corpus (dates converted to ISO strings): `valid/` and `invalid_semantic/` validate, every `invalid_structure/` file fails |
| unit | `test_config_schema.py::test_corpus_not_empty_and_commented` | each folder has fixtures; each fixture starts with a comment line; no non-generic ids (only `sensor.plug_*`, `sensor.meter_*` style) |
| integration | `tests/integration/test_yaml_schema_sync.py::test_corpus_against_parser` | `valid/` accepted by `document_from_yaml`; `invalid_structure/` and `invalid_semantic/` raise `YamlConfigError` |
| integration | `test_yaml_schema_sync.py::test_schema_keys_match_parser` | for every path in `ACCEPTED_KEYS`: the schema node has `additionalProperties: false` and `set(properties) == ACCEPTED_KEYS[path]`; no schema object with `additionalProperties: false` is missing from `ACCEPTED_KEYS` (except `patternProperties` maps such as `prices`, `hours`, `overrides`) |
| integration | `test_yaml_schema_sync.py::test_schema_enums_match_code` | `mode` enum == `SensorMode` values; `preset` enum == `PRESET_ZONES` keys |
| integration | `tests/integration/test_yaml_config.py::test_full_design_example` | the CONFIG-DESIGN example (`valid/full_example.yaml`, generic ids) → options equal the stored shape of 017–020 (prices as strings, ISO dates, `applied` list), tariffs equal the subentry data |
| integration | `test_yaml_config.py::test_defaults` | `None` / `{}` → given default time zone and sensors, `spike_limit == "4"`, no `panel` / `applied` / `compare`, no tariffs; partial `panel` filled with defaults; `sensors` without `exclude` / `overrides` filled with `{}`; filter mode without `include` → `"all"` |
| integration | `test_yaml_config.py::test_numbers_become_decimal_strings` | parametrized: int, float (`8.1`, `1e-05`) in prices, zone price, `spike_limit`, override `spike_limit` → normalized strings; `True` → error |
| integration | `test_yaml_config.py::test_dates` | `date` and `"YYYY-MM-DD"` accepted and stored as ISO; `datetime` and `"2026-1-1"` → error |
| integration | `test_yaml_config.py::test_applied_short_form` | `applied: two_zone` → one entry from the tariff's first `valid_from`; unknown id → error |
| integration | `test_yaml_config.py::test_rejects_invalid` | parametrized: non-mapping block, unknown top-level key, unknown `sensors` / `panel` key, duplicate tariff id, overlapping hours, unknown zone price key, `applied` before the first version, invalid glob → `YamlConfigError` whose message names the offending path |
| integration | `test_yaml_config.py::test_export_round_trip` | parametrized stored configurations (UI-made, with / without panel, compare, overrides with `null`): `render_yaml` → `parse_yaml` → `document_from_yaml` → identical options and tariff data; key order as specified; dates unquoted, prices quoted; the parsed export validates against the JSON Schema |
| integration | `test_yaml_config.py::test_yaml_loader_types` | `parse_yaml` of the design example returns `date` for `valid_from` and `float` for an unquoted price, and the normalizer accepts both |
| integration | `tests/integration/test_yaml_mode.py::test_yaml_creates_entry` | `async_setup_component` with a valid block and no entry → one entry (source `import`) with the YAML options and one `tariff` subentry per tariff; report works; no issue |
| integration | `test_yaml_mode.py::test_yaml_replaces_ui_config` | existing UI entry + block → options and subentries replaced by YAML (updated, added, removed by tariff id); warning logged; entry `LOADED` |
| integration | `test_yaml_mode.py::test_time_zone_default_keeps_stored` | block without `time_zone` keeps the entry time zone; without entry uses `hass.config.time_zone` |
| integration | `test_yaml_mode.py::test_invalid_yaml_at_startup_keeps_last_config` | entry + invalid block → integration loaded, entry `LOADED` with its previous options, issue `invalid_yaml` with `error` placeholder, error logged |
| integration | `test_yaml_mode.py::test_invalid_yaml_without_entry` | invalid block (including a list or a string under the key), no entry → no entry created, issue created, `async_setup` returned `True`, user config flow aborts `yaml_mode` |
| integration | `test_yaml_mode.py::test_unknown_time_zone_is_reported` | an unknown `time_zone` → issue, entry unchanged |
| integration | `test_yaml_mode.py::test_reload_applies_changes` | patch the YAML source (`homeassistant.config.async_hass_config_yaml`) to a changed block, call `energy_cost_stats.reload` → options / subentries updated, entry reloaded (new prices in a report), issue absent |
| integration | `test_yaml_mode.py::test_reload_invalid_raises_and_keeps_running` | reload with an invalid block → `HomeAssistantError` (translation key `yaml_invalid`), issue created, options unchanged, entry `LOADED`; a following valid reload deletes the issue |
| integration | `test_yaml_mode.py::test_reload_syntax_error` | the patched loader raises `HomeAssistantError` → action error + issue |
| integration | `test_yaml_mode.py::test_reload_block_added_and_removed` | no block at startup, block added + reload → entry synced / imported; block removed + reload → issue cleared, YAML mode off, options flow `init` is the UI menu again, options keep the last YAML values |
| integration | `test_yaml_mode.py::test_reload_is_admin_only` | non-admin user context → `Unauthorized` |
| integration | `test_yaml_mode.py::test_deleted_subentry_restored` | YAML mode, `async_remove_subentry` on a tariff → after the listener / reload the tariff subentry exists again and `applied` is unchanged (no reconcile) |
| integration | `test_yaml_mode.py::test_options_read_only_in_yaml_mode` | `init` → menu `yaml_mode` with `["sensors_view", "applied_view", "export_yaml"]` and the general / compare placeholders; `sensors_view` shows `count` / `sensors`; `applied_view` shows the history rows; navigating never changes `entry.options`; with an invalid block the `error` placeholder carries the message |
| integration | `test_yaml_mode.py::test_tariff_subentry_flows_abort_in_yaml_mode` | add tariff and reconfigure tariff → abort `yaml_mode`; in UI mode both still start normally |
| integration | `test_yaml_mode.py::test_export_yaml_step` | UI mode: `init` menu ends with `export_yaml`; the step's `yaml` placeholder starts with `energy_cost_stats:` and round-trips to the current options; a `schema_url` placeholder equals `const.SCHEMA_URL`; same step reachable from `yaml_mode` |
| integration | `tests/integration/test_options_menu.py::test_options_menu` (updated) | UI `init` menu = `["sensors", "applied", "compare", "general", "export_yaml"]` |
| integration | `test_options_menu.py::test_options_strings_complete` (extended) | every new step, menu option, abort, issue, exception and service key exists in `strings.json` and `translations/en.json` |

## Acceptance criteria
- [x] `uv run pytest -m unit` → green (incl. `test_config_schema.py`, also on Windows native); engine coverage
      ≥ 95 % (`script/test`).
- [x] `uv run --group ha pytest -m integration` → green (latest HA locally; the 2025.4.0 leg in CI).
- [x] `script/lint` → clean; `uv run --group ha pyright` → 0 errors.
- [x] `hassfest` and `hacs` CI jobs green (`services.yaml` has `reload`, `strings.json` has `services.reload` and
      `issues.invalid_yaml`).
- [x] `grep -rn "homeassistant" custom_components/energy_cost_stats/engine/ custom_components/energy_cost_stats/settings.py custom_components/energy_cost_stats/yaml_config.py`
      → no imports.
- [x] `grep -rln "homeassistant.components.recorder" custom_components/` → only `recorder_adapter.py`.
- [x] `grep -n "empty_config_schema" custom_components/energy_cost_stats/__init__.py` → no match; a list or a string
      under `energy_cost_stats:` still lets the integration and its entry load (`test_invalid_yaml_without_entry`,
      `test_invalid_yaml_at_startup_keeps_last_config`).
- [x] The YAML-mode steps (`yaml_mode`, `sensors_view`, `applied_view`, `export_yaml`) only show menus; no path from
      them reaches `async_create_entry` (`test_options_read_only_in_yaml_mode`).
- [x] Config entry `VERSION` / `MINOR_VERSION` unchanged (3 / 1).
- [x] The CONFIG-DESIGN "Full configuration (YAML)" example (generic ids) loads without errors, validates against
      the JSON Schema, and its Export reloads to identical options.
- [x] `schema/energy_cost_stats.schema.json` exists, is draft-07, root = block content, and
      `test_yaml_schema_sync.py` is green; the corpus has at least one fixture per top-level key in `valid/` and `invalid_structure/`
      (`invalid_semantic/` is exempt: some keys, e.g. `panel`, have no semantic rule).
- [x] `uv.lock` updated with `jsonschema` in the `dev` group only (`grep -n jsonschema pyproject.toml`).
- [ ] Manual check in the dev HA (`script/develop`): Developer tools → YAML lists "Energy Cost Stats"; the reload
      applies a price change without restart; an invalid block shows a repair; Export renders as a code block. In an
      editor with the YAML extension, a split file with the modeline shows completion and flags an unknown key.
      Record the outcome in Implementation notes.
- [x] `docs/SPEC.md` (§2 / §3 / §6 + "JSON Schema"), `README.md`, `docs/CONFIG-DESIGN.md` and the `CLAUDE.md`
      convention line updated as listed under Files.

## Out of scope
- Card changes (task 022), sidebar panel (023), Russian translations (024).
- A fixable repair flow (e.g. "remove the YAML block for me") — repairs are informational.
- Editing the YAML from the UI, or writing `configuration.yaml` from the integration.
- Mixing sources (part YAML, part UI) — not supported by design.
- A websocket command / action returning the export (only the options step).
- Reordering existing tariff subentries to match the YAML order.
- Backing up a UI configuration before YAML replaces it (Export covers it manually).
- Publishing the schema to SchemaStore or a docs site; a schema for the stored `entry.options` / websocket JSON;
  semantic checks in the schema (hour coverage, references between tariffs and `applied` / `compare`).

## Open questions
- **Invalid YAML at startup.** Default: the entry keeps running its last valid (stored) configuration, the UI is
  read-only and shows the error, and a repair is raised. Alternative: fail the entry setup until the YAML is fixed
  (no reports meanwhile).
- **Removing the YAML block.** Default: after reload / restart the entry keeps the last YAML values and becomes
  editable in the UI (an easy way to move from YAML to UI). Alternative: revert to the previous UI configuration
  (would need a stored backup) or remove the entry.
- **YAML over an existing UI configuration.** Default: replaced without a backup, with a warning in the log; SPEC
  recommends Export first. Alternative: refuse until the user confirms (e.g. a fixable repair).
- **`sensors` omitted in YAML.** Default: the first-setup rule (Energy dashboard if it has devices, else
  `filter` + `all`) evaluated at each load. Alternative: require `sensors` in YAML.
- **`include` omitted in `filter` mode.** Default: `all`. Alternative: error (strict like the stored shape).
- **Empty block** (`energy_cost_stats:` with no keys). Default: valid YAML mode with all defaults and no tariffs.
- **Tariff subentry flows in YAML mode.** Default: abort `yaml_mode` (the tariff's version table is visible via
  Export). Alternative: a read-only tariff menu with the version table.
- **Read-only view granularity.** Default: one `yaml_mode` menu (general and compare in its description) with
  `sensors_view`, `applied_view` and `export_yaml`. Alternative: read-only variants of all four UI steps.
- **Export formatting.** Default: dates unquoted, prices and limits quoted strings, `applied` always in list form.
- **Schema URL.** Default: `$id` and the documented modeline use `master`; release tags are documented for pinning.
  Alternative: always document the tag of the current release (needs a release step to update the docs).
- **Numbers in the schema.** Default: prices / limits allow `number` (the parser accepts them) so editors do not
  flag `price: 8.1`. Alternative: `string` only, nudging users to the recommended quoted form.

## Implementation notes
- All open questions took the planner's defaults. Added the files listed under Files; the tariff and settings key sets
  are public as `TARIFF_KEYS` / `VERSION_KEYS` / `ZONE_KEYS` / `APPLIED_KEYS` (engine) and `OPTION_KEYS` (settings).
  `ACCEPTED_KEYS[""]` is `OPTION_KEYS` plus `tariffs`.
- `document_from_yaml` returns `settings_to_options(settings)` as the options, so limits are normalized exactly as the
  forms store them (`"4.0"` -> `"4"`); tariff data is kept as written (prices keep their scale).
- At startup the import flow runs as a task: awaiting it inside `async_setup` would wait for the component setup that
  is still running (the entry setup awaits it). A reload awaits the flow directly.
- `async_sync_entry` matches subentries by `unique_id` (fallback `data["id"]`), logs the "replaces the configuration
  made in the UI" warning once per entry and process, and only when the entry was not created by the import.
- Verified against the installed HA (2026.9): `ConfigFlow.async_create_entry` accepts `subentries=`, but the import
  flow still creates options only (2025.4.0 compatibility not verifiable locally); `async_update_subentry`,
  `async_add_subentry`, `async_remove_subentry`, `util.yaml.dump` / `parse_yaml` and
  `async_integration_yaml_config` exist with the documented signatures.
- Schema: `type: ["object", "null"]` at the root (an empty block). `include` is `oneOf` the constant `all` and a target.
  Zone price maps use `additionalProperties`, so only the closed objects are in `ACCEPTED_KEYS`.
- Extra tests beyond the table: `test_reload_creates_entry_when_missing`, `test_tariff_subentry_flows_start_in_ui_mode`,
  `test_export_yaml_from_yaml_mode`, `test_corpus_covers_every_top_level_key`; `yaml_invalid` was added to the key set
  asserted in `test_report_api.py::test_all_error_codes_translated`.
- Not done: the manual check in the dev HA (Developer tools listing, Export rendering, editor completion); it needs
  `script/develop` and an editor.

- Review round 1: the replace-UI warning now depends on the entry content (existing tariff subentries or options that
  differ), and the once-per-process guard is cleared when the block is removed. With an invalid block the update
  listener falls back to the options reconciliation, so a deleted tariff does not break setup; the next valid sync
  restores it. The schema now allows null collections, exponent decimal strings and padded price strings; the
  parser stays the authority for prices (fixture `invalid_semantic/price_exponent`).

## Follow-ups
- Check manually that Developer tools, YAML lists "Energy Cost Stats" via the `reload` action and how the Export code
  block renders (no copy button expected).
