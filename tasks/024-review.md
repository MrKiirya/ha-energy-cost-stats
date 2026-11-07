# 024 — Review (round 1)

Verdict: CHANGES_REQUESTED

## Checks run
- `uv run --no-sync pytest -m unit` (devcontainer) → `515 passed, 420 deselected`
- `uv run --no-sync pytest -m unit tests/unit/test_metadata.py -v` → `13 passed` (parametrized `en`, `ru`,
  `strings.json` cases all present)
- `uv run --no-sync ruff check .` → `All checks passed!`; `uv run --no-sync ruff format --check .` →
  `120 files already formatted`
- `npm test` (frontend) → `Test Files 5 passed (5)`, `Tests 136 passed (136)`
- `npm run check-bundle` → `Card bundle is up to date.`
- Mutation check on a throw-away copy of the repo (working tree untouched): renaming `{count}` to `{cnt}` in
  `options.step.sensors.description` fails with
  `placeholder mismatch (expected, actual): {'options.step.sensors.description': (['count', 'sensors'], ['cnt', 'sensors'])}`;
  deleting `options.error.invalid_glob` fails with `missing keys: ['options.error.invalid_glob']`.
- Key tree and key order of `ru.json` compared programmatically with `strings.json` → identical.
- HA UI names checked against the Russian frontend translation bundled with the installed Home Assistant
  (`hass_frontend/static/translations/config/ru-*.json`): `areas.caption` «Пространства», `labels.caption`
  «Ярлыки», `repairs.caption` «Устранение проблем», `panel.energy` «Энергия», tools tab `actions` «Действия»,
  `generic.headers.entity_id` «Идентификатор объекта» — all match `ru.json`. There is no `developer_tools`
  panel in that release (see Suggestion 1).

## Acceptance criteria
- [x] `pytest -m unit tests/unit/test_metadata.py` passes incl. `en` and `ru` cases — verified (13 passed).
- [x] `pytest -m unit` passes — verified (515 passed).
- [x] Renaming a placeholder or deleting a key fails with the key path in the message — verified on a copy.
- [x] `ruff check` / `ruff format --check` clean — verified.
- [x] `strings.json` and `translations/en.json` unchanged — `git diff --stat` lists neither.
- [x] `ru.json` UTF-8 with literal Cyrillic, 2-space indent, trailing newline, key order as `strings.json` —
      verified by reading the file and by a key-order comparison.
- [x] Terminology spot-checks: every `spike_limit` label is «Порог выбросов», every `valid_from` label is
      «Действует с», `Energy Cost Stats` untranslated, globs are «маски», templates «шаблоны» — verified.
- [x] hassfest / hacs not regressed — `strings.json` and `en.json` untouched; the new value-rule test also passes
      on `strings.json`. CI itself not run here.
- [ ] Optional manual dev-HA check — not done (optional).
- [x] `docs/SPEC.md` and `CLAUDE.md` updated as listed — verified.

## Findings
### Required
1. `custom_components/energy_cost_stats/translations/ru.json:590` — `selector.tariff_base.options.single_rate`
   is «Один тариф». In the "Start from" selector of a new tariff, "single rate" means a one-zone tariff. «Один
   тариф» reads as "one tariff", which makes little sense when choosing how to build *a* tariff. It also
   collides with the unrelated options-menu entry «Один тариф на весь период» (`applied_single`). The sibling
   options are «Две зоны (день и ночь)» and «Три зоны (…)», so a zone-based label fits.
   Proposed: «Одна зона (круглосуточно)» (or «Однотарифный (одна зона)»).

### Suggestions
1. `ru.json:178` `options.step.yaml_mode.description` — «Панель разработчика» could not be verified against the
   installed Home Assistant (2026.9): it no longer has a Developer tools panel. The YAML/actions tabs now live
   under Settings → Tools (RU `ui.panel.config.dashboard.tools.main` = «Инструментарий», tab `yaml` = «YAML»).
   The English source has the same outdated reference, so this belongs in a follow-up that rewords `strings.json`
   / `en.json` / `ru.json` together, e.g. EN "(Developer tools or, in newer releases, Settings → Tools, YAML)",
   RU «(Панель разработчика или, в новых версиях, Настройки → Инструментарий, YAML)». Record it in the task's
   Follow-ups.
2. **English text inside placeholders (follow-up).** Several placeholders are filled with hard-coded English in
   Python, so a Russian UI still shows mixed text: `{applied}` → "Applied from …" / "Not applied"
   (`tariff_flow.py:578`), `{zones}` → "Zone N: …" (`tariff_flow.py:479`), `{versions}` → table header
   "| Valid from | Prices |" (`engine/tariff_edit.py:286`), `{spike_limit}` → "off" and `{sidebar}` →
   "shown"/"hidden" (`config_flow.py:389-396`), `{max}` → "31 days for hourly grouping" / "N days"
   (`report_api.py:174-177`). Fixing this is outside this task's file list. It conflicts with the goal "every
   integration text in Russian", though, so add a follow-up (move the words into translated strings and
   pass only data through placeholders).
3. Placeholder grammar in titles: a nominative tariff name after a noun reads unnaturally («Новая версия
   Домашний»). The terminology table prescribes «Новая версия {name}», so adjust the table as well if adopted:
   - `config_subentries.tariff.step.new_version.title`: «Новая версия {name}» → «Новая версия тарифа «{name}»»
   - `…step.edit_first_version.title`: «Изменение первой версии {name}» → «Изменение первой версии тарифа «{name}»»
   - `…step.edit_version.title`: «Изменение версии {name}» → «Изменение версии тарифа «{name}»»
   - `…step.rename.title`: «Переименование {name}» → «Переименование тарифа «{name}»»
4. HA wording alignment:
   - `options.step.general.sections.sidebar.data.icon`: «Значок» → «Иконка» (HA RU uses «Иконка» for every
     "Icon" field).
   - `options.step.sensors_select.data_description.mode`: «…использует отдельные устройства из панели
     «Энергия»…» → «…использует потребителей энергии из панели «Энергия»…» (HA RU
     `energy.device_consumption.title` is «Потребители энергии»); same for `options.error.no_dashboard_devices`:
     «В панели «Энергия» нет отдельных устройств.» → «В панели «Энергия» не настроены потребители энергии.»
5. Grammar and punctuation:
   - `config_subentries.tariff.error.invalid_price`: «Введите цену, например 10.30 (цифры с необязательной
     дробной частью, не отрицательная).» → «Введите цену, например 10.30 (неотрицательное число, дробная часть
     необязательна).»
   - `…step.new_version.sections.hours.description` and `…step.edit_version.sections.hours.description`:
     «Меняйте часы только если…» → «Меняйте часы, только если…».
   - `services.get_report.fields.end.description`: «Конец периода, не включается, в тех же форматах, что и
     начало. Например, 2026-02-01 завершает период после января.» → «Конец периода (не включается) в тех же
     форматах, что и начало. Например, 2026-02-01 означает, что период заканчивается вместе с январём.»
   - `exceptions.unknown_entity.message`: «{entity_id} не входит в выбранные датчики энергии.» → «{entity_id} не
     входит в число выбранных датчиков энергии.»
6. Calques that read awkwardly:
   - `config.step.user.data_description.time_zone`: «Не следует за последующими изменениями часового пояса Home
     Assistant.» → «Последующие изменения часового пояса Home Assistant на него не влияют.»
   - `config_subentries.tariff.step.tariff_id.description`: «Идентификатор определяет тариф … и не путается с
     его названием.» → «Идентификатор обозначает тариф в конфигурации и вызовах API; в отличие от названия, он
     однозначен.»
   - `config_subentries.tariff.error.applied_order`: «История применения начинает этот тариф с даты, которая
     здесь меняется. Новая дата изменила бы порядок в истории применения. …» → «В истории применения этот тариф
     начинается с даты, которую вы меняете. Новая дата нарушила бы порядок истории применения. Сначала измените
     историю применения.»
   - `config_subentries.tariff.error.applied_without_version`: «История применения использует этот тариф с даты,
     для которой не было бы версии.» → «В истории применения этот тариф используется с даты, для которой не
     останется версии.»
   - `services.get_report.fields.start.description`: «…читаются в часовом поясе интеграции.» → «…
     интерпретируются в часовом поясе интеграции.»
7. `options.error.invalid_glob`: «только строчные буквы, цифры…» → «только строчные латинские буквы, цифры…»
   (the rule is ASCII-only; the English source is ambiguous in the same way).
8. Scope bookkeeping: the card string `compare.empty` and the rebuilt bundle were changed although the task's
   Out of scope lists "Card strings and the card bundle". The change is small, correct and matches the
   resolution of Open question 1. Update the Out of scope line (or the open question) so the task file
   matches the diff.
9. `tests/unit/test_metadata.py` — the drift tests use only the standard library plus `pytest`, carry the `unit`
   marker and pass without HA, so they run in the Windows job. Optional hardening: assert in
   `test_russian_values_are_translated` that every allowlisted key's English value really has no letters outside
   placeholders and the brand, so the allowlist cannot silently grow to hide untranslated text.

# 024 — Review (round 2)

Verdict: CHANGES_REQUESTED

## Checks run
- `uv run --no-sync pytest -m unit` → `515 passed, 420 deselected`
- `uv run --no-sync ruff check .` → `All checks passed!`; `ruff format --check .` → `121 files already formatted`
- `npm run check-bundle` → `Card bundle is up to date.`
- `cmp strings.json translations/en.json` → identical.
- Installed Home Assistant (2026.9.3) frontend translations: EN `panel.config` "Settings",
  `ui.panel.config.dashboard.tools.main` "Tools", tab `tools.tabs.yaml.title` "YAML"; RU «Настройки»,
  «Инструментарий», «YAML». "Settings → Tools → YAML" / «Настройки → Инструментарий → YAML» match the current UI.

## Previous required items
1. `selector.tariff_base.options.single_rate` — resolved: «Однотарифный (одна зона)», consistent with «Две зоны
   (день и ночь)» / «Три зоны (…)».

## Wording changes (round 1 suggestions)
Checked one by one: the tariff-name titles («Новая версия тарифа «{name}»» etc., terminology table updated),
«Иконка», «потребители энергии», `invalid_price`, the «, только если» commas, `get_report` `start`/`end`,
`unknown_entity`, `time_zone`, `tariff_id`, `applied_order`, `applied_without_version` and `invalid_glob`. All read
naturally, keep their placeholders (the placeholder test passes) and follow the terminology table. The hard-coded
English placeholder values are recorded under Follow-ups; the card-string exception is recorded under Out of scope.

## Findings
### Required
1. `custom_components/energy_cost_stats/strings.json` / `translations/en.json` / `ru.json`
   `options.step.yaml_mode.description`, and `README.md:15` — "Settings → Tools → YAML" exists only in recent
   Home Assistant releases. The minimum supported version (2025.4, `docs/SPEC.md` §6) still has these tabs under
   **Developer tools**, so users on that version cannot find the place the text names. Mention both, e.g. EN
   "(Settings → Tools → YAML; Developer tools → YAML in older releases)", RU «(Настройки → Инструментарий → YAML;
   в старых версиях — Панель разработчика → YAML)». Also update `docs/SPEC.md:88`, which still says "Developer
   tools, YAML", so the docs agree.
2. `tasks/024-ru-translation.md:124` and the Out of scope list — the acceptance criterion "`strings.json` and
   `translations/en.json` unchanged by this task" is checked although both files now change, and Out of scope
   still lists "Changing English texts in `strings.json` / `en.json`". Reword both to allow the single
   `yaml_mode.description` change. The criterion should then say what was verified: `en.json` identical to
   `strings.json`, no other English text changed.

### Suggestions
- None beyond the items above.

# 024 — Review (round 3)

Verdict: APPROVE

## Checks run
- `uv run --no-sync pytest -m unit` → `515 passed, 420 deselected`
- `cmp strings.json translations/en.json` → identical.

## Previous required items
1. Both locations are now named in `options.step.yaml_mode.description`. EN (`strings.json` = `en.json`):
   "(Settings → Tools → YAML; Developer tools → YAML in older releases)". RU: «(Настройки → Инструментарий →
   YAML; в старых версиях — Панель разработчика → YAML)». `README.md:15` and `docs/SPEC.md:88` use the same
   wording. In `strings.json`, only this one line differs from `HEAD`. Resolved.
2. The task file's acceptance criterion now says `en.json` is identical to `strings.json` and that the YAML tab
   location is the only English change. The Out of scope entry allows exactly that exception. Resolved.

## Findings
### Required
- None.
### Suggestions
- None.
