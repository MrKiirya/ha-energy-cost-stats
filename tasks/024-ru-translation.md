# 024 — Russian translation of the integration

Status: in-review (rounds 1–2: CHANGES_REQUESTED; round 3: APPROVE)
Roadmap: SPEC §8 stage 2 (config flow / options flow / tariff subentries) — localisation
Spec sections: SPEC §5 (card language, the "Language" bullet), `strings.json` as the source of all form texts

## Goal
Users with Home Assistant set to Russian see every integration text in Russian: the config flow, options menus
and steps, tariff subentry flows, errors, aborts, selector options, services, exceptions and the repair issue.
A unit test keeps every translation file in step with `strings.json` (same keys, same `{placeholder}` set per
string), so a later string change cannot silently drift. The Russian terms match the card's existing Russian
strings.

## Context
- **HA conventions, checked:**
  - Custom integrations do not use `strings.json` at runtime. They ship finished files in
    `custom_components/<domain>/translations/<BCP 47 code>.json` with the same structure as `strings.json`.
    `en.json` is required and complete, because it is the fallback for every other language. At runtime a
    missing key falls back to English, and a translation whose placeholders differ from the English string is
    dropped in favour of English. `[%key:...%]` references do not work in custom integrations (users would see
    the raw text). Source: https://contributors.home-assistant.io/core/integrations/translations/ (the old
    `developers.home-assistant.io/docs/internationalization/custom_integration/` URL now redirects there).
  - hassfest (`script/hassfest/translations.py`, `dev` branch) validates only `strings.json` and, for custom
    integrations, `translations/en.json` ("Only English needs to be always complete"). It does **not** validate
    `ru.json`. Its value checks are: no HTML, no placeholder inside single quotes (`'{name}'`), placeholder
    names must be identifiers, no leading or trailing whitespace, no URLs unless allowed. Key rules (lowercase
    `[a-z0-9-_]`) apply to keys only. Source:
    https://raw.githubusercontent.com/home-assistant/core/dev/script/hassfest/translations.py
  - Because hassfest does not cover `ru.json`, the new unit test reproduces these value checks for every
    translation file.
- **Placeholder drift matters:** a wrong or missing placeholder in `ru.json` silently drops the string back
  to English (or shows a broken string). The test compares the placeholder set per string.
- Existing test `tests/unit/test_metadata.py::test_strings_match_en_translation` already asserts
  `strings.json == translations/en.json`. The new tests go next to it (unit level, no HA, so they also run in
  the Windows job).
- `strings.json` has roughly 350 leaf strings. Many repeat: the six `zone_N` sections in `first_version` and
  `edit_first_version`, `price_N` / `hours_N` in `new_version` and `edit_version`. Translate them the same way
  each time.
- **Keep unchanged:** the brand name "Energy Cost Stats", `energy_cost_stats` / `configuration.yaml` /
  `energy_cost_stats.reload`, code spans in backticks, the glob example, formats such as `HH:MM-HH:MM`,
  `YYYY-MM-DD`, `07:00-10:00`, `10.30`, `24:00`, `a-z, 0-9 and _`, the Markdown table header structure
  (`| From | Tariff |` → translate the header cells, keep `|---|---|`), `\n` line breaks, and every
  `{placeholder}` with its exact name. Never translate JSON keys (including selector option keys such as
  `ru_two_zone`).
- Use typographic Russian quotes «…» instead of `"…"` inside values (this also avoids JSON escapes). Write
  "ё" where the card does (`отчёт`, `Вперёд`).

### Terminology (use consistently; matches `frontend/src/i18n.ts` RU)
| English | Russian | Note |
|---|---|---|
| tariff | тариф | card: «Тариф», «Сравнение тарифов». Do not use «тарифный план» in new strings. |
| tariff zone / zone | тарифная зона / зона | |
| zone key | ключ зоны | |
| version (of a tariff) | версия | «Новая версия тарифа «{name}»», «Первая версия» |
| valid from | Действует с | |
| applied tariffs (menu/step) | Применяемые тарифы | |
| applied history | история применения тарифов | |
| change (entry of the applied history) | смена тарифа / смена | «Добавить смену», «Изменить или удалить смену» |
| from (date column/field) | С | card `from`: «С» |
| tariff comparison / compared tariffs | сравнение тарифов / тарифы для сравнения | card `compare.title` |
| default set | набор по умолчанию | |
| sensor / energy sensor | датчик / датчик энергии | card: «датчики энергии» |
| device | устройство | |
| upstream device; measured inside another one | устройство выше; измеряется внутри другого | card `nested.*` |
| spike / spike check | выброс / проверка выбросов | card: «исключено (выброс)» |
| spike limit | порог выбросов | per-sensor: «пороги выбросов по датчикам» |
| plausible consumption | правдоподобное потребление | |
| data-quality report | отчёт о качестве данных | card: «Качество данных» |
| price per kWh | цена за кВт·ч | card unit «кВт·ч» |
| re-price past hours | пересчитать стоимость прошлых часов | |
| unpriced hours | неоценённые часы / часы не оцениваются | card: «не оценены» |
| report | отчёт | |
| grouping; hour/day/week/month/total | группировка; Час / День / Неделя / Месяц / Итого | selector labels are nouns; card `total`: «Итого» |
| period | период | |
| time zone | часовой пояс | |
| Energy dashboard | панель «Энергия» | as in HA core Russian UI |
| filter (mode) | фильтр | |
| include / exclude | включить / исключить | |
| entity id pattern (glob) | шаблон идентификатора объекта | use «маска» if it reads better; never the same word as "template" below |
| templates (not supported) | шаблоны (Jinja) | |
| areas / floors / labels | пространства / этажи / метки | as in HA core Russian UI |
| sidebar | боковая панель | |
| action (`energy_cost_stats.reload`) | действие | HA core Russian calls services «действия» |
| Developer tools / YAML tab | Настройки → Инструментарий → YAML | current HA wording (Settings → Tools) |
| repair (issue) | уведомление в разделе «Проблемы» / проблема | check the current HA core Russian name of Repairs and use it |
| reload | перезагрузить | |
| Back | Назад | card `previous` |

For HA UI names (Energy dashboard, areas, floors, labels, Developer tools, Repairs, actions) check the current
HA frontend Russian translation and use its exact wording; adjust the table above in the task file if it differs.

## Files
- create: `custom_components/energy_cost_stats/translations/ru.json` — full Russian translation, same key tree
  and key order as `strings.json`, 2-space indent, UTF-8 (not `\u` escapes), trailing newline.
- modify: `tests/unit/test_metadata.py` — tests below.
- modify: `docs/SPEC.md` — the "Language" bullet (around the card section) states that the integration's forms,
  services and messages are translated into English and Russian, with `strings.json` / `translations/en.json`
  as the source and the unit test as the drift guard.
- modify: `CLAUDE.md` — one line under conventions (or Test levels): any change to `strings.json` must update
  `translations/en.json` and every other `translations/*.json` in the same change; the metadata tests enforce it.

## Tests to write first
All in `tests/unit/test_metadata.py`, marker `unit`, standard library only (no HA, no engine import).
Helpers: `_flatten(obj, prefix="") -> dict[str, str]` (dotted key path → leaf string) and
`_placeholders(s) -> set[str]` using `re.findall(r"\{([^{}]*)\}", s)`.

| Level | Test | Asserts |
|---|---|---|
| unit | `test_metadata.py::test_russian_translation_exists` | `translations/ru.json` exists and parses as a JSON object (so the parametrized tests below cannot pass vacuously). |
| unit | `test_metadata.py::test_translation_keys_match_strings[<lang>]` (parametrized over every `translations/*.json`) | `set(_flatten(lang)) == set(_flatten(strings))`; on failure the message lists missing and extra key paths. Every leaf is a `str`. No root-level `"title"`. |
| unit | `test_metadata.py::test_translation_placeholders_match_strings[<lang>]` | for every key path, `_placeholders(lang[k]) == _placeholders(strings[k])`; on failure lists each key with both sets. |
| unit | `test_metadata.py::test_translation_values_pass_hassfest_rules[<lang>]` | for every value: no `[%key:`; no HTML tag (`re.search(r"<[a-zA-Z/][^>]*>", v)` is None); no `'{` placeholder in single quotes; every placeholder name is a Python identifier; `v == v.strip()`; not empty. Also run on `strings.json`. |
| unit | `test_metadata.py::test_russian_values_are_translated` | every `ru.json` value contains at least one Cyrillic letter, except an explicit allowlist of key paths whose English value is a brand name or placeholder only (`config.step.user.title`, `config_subentries.tariff.step.select_version.description`; add others only if they contain no translatable words). |

Write the tests first with a stub `ru.json` (`{}`) to see them fail, then translate.

## Acceptance criteria
- [x] `uv run pytest -m unit tests/unit/test_metadata.py` → all pass, including the parametrized cases for
      `en` and `ru`.
- [x] `uv run pytest -m unit` → passes (engine coverage gate unaffected).
- [x] Temporarily renaming one placeholder in `ru.json` (e.g. `{count}` → `{cnt}`) or deleting one key makes the
      placeholder / key test fail with a message naming the key path (reviewer check, then revert).
- [x] `uv run ruff check .` and `uv run ruff format --check .` → clean.
- [x] `translations/en.json` is identical to `strings.json`; the only English change is the location in
      `options.step.yaml_mode.description` (plus README.md and docs/SPEC.md), no other English text changed.
- [x] `ru.json` is UTF-8 with Cyrillic as literal characters (no `\u04` escapes), 2-space indent, key order as
      `strings.json`.
- [x] Terminology table followed: e.g. every `spike_limit` label is «Порог выбросов», every "Valid from" is
      «Действует с», `Energy Cost Stats` is untranslated (spot-check with `grep`).
- [x] CI `hassfest` and `hacs` stay green (hassfest does not read `ru.json`, but the job must not regress).
- [ ] Optional manual check in dev HA (`script/develop`): set the user profile language to Russian, open the
      integration's options and a tariff's reconfigure flow — texts are Russian, placeholders filled.
- [x] `docs/SPEC.md` and `CLAUDE.md` updated as listed under Files.

## Out of scope
- Translations into other languages (the tests already cover any future `translations/<lang>.json`).
- Changing English texts in `strings.json` / `en.json`, except the location of the YAML tab in
  `options.step.yaml_mode.description`.
- Card strings (`frontend/src/i18n.ts`) and the card bundle, except the single `compare.empty` Russian string
  aligned with the options menu wording (bundle rebuilt).
- Translating entity names of the global entities (none are defined in `strings.json` yet).

## Open questions
- The card's `compare.empty` (RU) points to «Настроить → Сравнение», while the options menu entry will read
  «Сравнение тарифов». Align the card string in a small follow-up (requires a card rebuild), or leave as is?
- Preferred word for entity id globs in the UI: «шаблон идентификатора» or «маска»? The task defaults to
  «шаблон» unless the implementer finds it collides with the "templates are not supported" error text, in which
  case «маска» is used for globs.

<!-- Filled in by implementer -->
## Implementation notes
- `ru.json` follows the terminology table. HA UI names were checked against the Russian frontend translation
  shipped with the installed Home Assistant: areas are «Пространства», labels are «Ярлыки» (not «метки»),
  Repairs is «Устранение проблем», the Energy dashboard is «Энергия», actions are «Действия». Labels and the
  repair name are used accordingly.
- Entity id globs are «маски» (the error text «Шаблоны здесь не поддерживаются» keeps «шаблон» for templates).
- Open question 1 resolved: the card's Russian `compare.empty` now says «Настроить → Сравнение тарифов»; the
  bundle was rebuilt and `check-bundle` passes.
- Placeholder-mutation check done by hand: renaming `{count}` to `{cnt}` fails the placeholder test with the key path.
- Tests use `@pytest.mark.unit`; the not-covered-by-hassfest value rules are also applied to `strings.json`.
- Review round 1: `single_rate` is now «Однотарифный (одна зона)»; titles with a tariff name read «... тарифа
  «{name}»»; wording fixes applied. The outdated "Developer tools, YAML" reference was reworded to
  "Settings → Tools → YAML" (RU «Настройки → Инструментарий → YAML») in `strings.json`, `translations/en.json`
  (kept identical), `ru.json` and README.md; this is the only change to the English texts.
## Follow-ups
- Hard-coded English placeholder values keep a Russian UI partly English. Move the words into translated strings
  and pass only data through the placeholders: `{applied}` ("Applied from ..." / "Not applied", `tariff_flow.py`),
  `{zones}` ("Zone N: ...", `tariff_flow.py`), `{versions}` (table header "| Valid from | Prices |",
  `engine/tariff_edit.py`), `{spike_limit}` ("off") and `{sidebar}` ("shown"/"hidden") in `config_flow.py`, and
  `{max}` ("31 days for hourly grouping" / "N days", `report_api.py`).
- Optional hardening: assert that every allowlisted key's English value has no translatable words outside
  placeholders and the brand name.
