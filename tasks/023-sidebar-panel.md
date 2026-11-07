# 023 — Sidebar panel

Status: in-review (round 1: APPROVE)
Roadmap: Configuration v2 (docs/CONFIG-DESIGN.md "Tasks", row 023)
Spec sections: SPEC §2 (options: `panel`; YAML mode), §4.1 (card: serving, layout, `hass` gate), §6 (minimum HA
version); CONFIG-DESIGN "Full configuration" (`panel`), "Configure (options)" → General, "Decisions" (no tab in the
built-in Energy panel)

## Goal
When "Show in sidebar" is on (General options, or `panel.show: true` in the YAML block), Home Assistant's sidebar
gets an entry with the configured title and icon that opens a full-width page with the cost view: the existing card
(its own period picker, device table, comparison and "by period" sections) inside a panel with a standard top bar.
Turning the option off, changing the title or icon, reloading the YAML block or unloading / removing the integration
updates the sidebar immediately, without a restart. No entities are added, and the card bundle is still loaded once.

## Context
### Decisions
- **Custom element panel, not an iframe.** The panel is registered with `panel_custom.async_register_panel(...,
  embed_iframe=False)`; its element `energy-cost-stats-panel` lives in the **same bundle** as the card
  (`custom_components/energy_cost_stats/frontend/energy-cost-stats-card.js`) and renders an
  `energy-cost-stats-card` inside. No second bundle, no new static path.
- **Same module URL as the extra module.** `module_url` is exactly the versioned URL already passed to
  `add_extra_js_url` (`CARD_URL?v=<content hash>`). The frontend loads a panel's `module_url` with a new
  `<script type="module" src=...>` every time (no dedupe in `load_resource.ts`), but browsers evaluate an ES module
  once per URL, so an identical URL means the bundle runs once and nothing is defined twice. A different URL (e.g.
  without `?v=`) would evaluate it a second time; `defineCard()` already skips an element that is defined, and the
  panel definition must be guarded the same way. A dashboard resource added by hand (another URL) is therefore also
  harmless. The versioned URL is computed once in `frontend.py` and kept in `hass.data` for the panel.
- **Period picker = the card's own.** CONFIG-DESIGN row 023 says "with Home Assistant's energy date picker". HA's
  picker (`hui-energy-period-selector`) is an internal Lovelace element bound to the Energy dashboard's data
  collection (`energy_collection_key`); it is not a public API, is lazy-loaded with the Energy panel, and would
  drive a collection the card does not use. The card already has a period picker modelled on it (SPEC §4.1), so the
  panel reuses the card unchanged. CONFIG-DESIGN row 023 is reworded accordingly (open question 1).
- **Not admin-only.** The panel only shows what the card shows; the `energy_cost_stats/report` and `/compare`
  websocket commands do not require admin either. `require_admin=False` (open question 2).
- **URL path** `energy-cost-stats` (constant `PANEL_URL_PATH`), element `energy-cost-stats-panel` (constant
  `PANEL_ELEMENT`, mirrored in `frontend/src/panel.ts`). The static path `/energy_cost_stats/...` is not affected.
- **Lifecycle through the entry.** The panel is registered at the end of `async_setup_entry` when the parsed
  `settings.panel` exists with `show: true`, the `frontend` integration is loaded and the card URL is known; removal
  is registered with `entry.async_on_unload`. Options changes (General step) and the YAML `reload` action already
  reload the entry (`_async_update_listener`, `yaml_mode.async_apply_yaml_state`), so show / hide / title / icon
  changes need no extra listener. The YAML block reaches the same `settings.panel` through `async_sync_entry`, so
  YAML mode needs no separate code path — only tests. An entry that fails to set up (`ConfigEntryError`) has no
  panel.
- **Failure is not fatal.** If registration raises `ValueError` (the URL path is already taken, e.g. by a YAML
  `panel_custom` entry of the user), log a warning and continue; the entry still loads and does not remove the
  foreign panel on unload. Removal uses `warn_if_unknown=False`.
- **Panel layout.** A top bar (height and colours from HA theme variables: `--app-header-background-color`,
  `--app-header-text-color`, falling back to `--primary-color` / `--text-primary-color`) with a menu button and the
  panel title (`panel.title`, i.e. the sidebar title), then the card with page padding (16 px, 8 px when `narrow`)
  and no max width. The menu button is shown when `narrow` and fires `hass-toggle-menu` (bubbles, composed) — the
  event HA's own `ha-menu-button` fires; using our own button avoids depending on an internal element. The card is
  configured with `{ type: "custom:energy-cost-stats-card", title: "" }` so its header does not repeat the title
  (see the card change below; open question 3).
- **`hass` gate.** The panel forwards every new `hass` to the card (the card's own `hasChanged` gate decides about
  re-rendering) but its own `hass` property uses the same `hassChanged` gate, so entity-only updates do not re-render
  the panel either.

### APIs checked (2025.4.0 minimum and current `dev`, 2026-11-07)
- `panel_custom.async_register_panel(hass, frontend_url_path, webcomponent_name, sidebar_title=None,
  sidebar_icon=None, js_url=None, module_url=None, embed_iframe=False, trust_external=False, config=None,
  require_admin=False, config_panel_domain=None)` at
  [2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/components/panel_custom/__init__.py);
  `dev` adds `handle_safe_area=False` at the end
  ([dev](https://github.com/home-assistant/core/blob/dev/homeassistant/components/panel_custom/__init__.py)). It
  stores `{name, embed_iframe, trust_external, module_url}` under `config["_panel_custom"]` and calls
  `frontend.async_register_built_in_panel(component_name="custom", ...)` with keywords. **Call it with keyword
  arguments only** and do not pass `handle_safe_area` (absent in 2025.4).
- `frontend.async_register_built_in_panel(hass, component_name, sidebar_title=None, sidebar_icon=None,
  frontend_url_path=None, config=None, require_admin=False, *, update=False, config_panel_domain=None)` at
  [2025.4.0](https://github.com/home-assistant/core/blob/2025.4.0/homeassistant/components/frontend/__init__.py);
  `dev` inserts `sidebar_default_visible=True` **positionally before `frontend_url_path`** and adds
  `show_in_sidebar=True` ([dev](https://github.com/home-assistant/core/blob/dev/homeassistant/components/frontend/__init__.py)).
  Both raise `ValueError("Overwriting panel ...")` for an existing path unless `update=True`, and fire
  `EVENT_PANELS_UPDATED` (the sidebar refreshes live). We go through `panel_custom` (keyword call) and never call
  this function directly.
- `frontend.async_remove_panel(hass, frontend_url_path, *, warn_if_unknown=True)` — same in 2025.4.0 and `dev`;
  pops the panel and fires `EVENT_PANELS_UPDATED`.
- `frontend.DATA_PANELS: HassKey[dict[str, Panel]] = HassKey("frontend_panels")` in both 2025.4.0 and `dev`;
  `Panel` has `component_name`, `sidebar_title`, `sidebar_icon`, `frontend_url_path`, `config`, `require_admin`,
  `config_panel_domain` in both (`dev` adds `sidebar_default_visible`, `show_in_sidebar`). Tests assert only the
  common attributes.
- `frontend.add_extra_js_url(hass, url, es5=False)` / `remove_extra_js_url` — unchanged; the card keeps using it.
- Frontend side, `ha-panel-custom.ts` at
  [20250401.0](https://github.com/home-assistant/frontend/blob/20250401.0/src/panels/custom/ha-panel-custom.ts) and
  [dev](https://github.com/home-assistant/frontend/blob/dev/src/panels/custom/ha-panel-custom.ts): with
  `embed_iframe: false` it awaits `loadCustomPanel(config)` (`loadModule(module_url)`, a script tag of type module,
  [load_resource.ts](https://github.com/home-assistant/frontend/blob/dev/src/common/dom/load_resource.ts)), then
  `document.createElement(config.name)`
  ([create-custom-panel-element.ts](https://github.com/home-assistant/frontend/blob/dev/src/util/custom-panel/create-custom-panel-element.ts)),
  sets the properties `panel`, `hass`, `narrow`, `route` and appends it; later changes of these properties are
  forwarded as property sets. `panel.config` holds our `config` plus `_panel_custom`; `panel.title` /
  `panel.icon` / `panel.url_path` are the sidebar values. If the element is not yet defined when created (bundle
  still waiting for `<home-assistant>`), it is upgraded on definition; Lit's `ReactiveElement` keeps properties set
  before the upgrade, so no special handling is needed — but a test covers it.
- `ha-menu-button` fires `hass-toggle-menu` and is shown only when `narrow` or the sidebar is "always hidden"
  ([dev](https://github.com/home-assistant/frontend/blob/dev/src/components/ha-menu-button.ts)). Our button follows
  the `narrow` part only (open question 4).
- **Unverified (confirm in CI):** hassfest's dependency check is expected to require `panel_custom` in the manifest
  (`after_dependencies`) once `homeassistant.components.panel_custom` is imported; the `hassfest` job confirms it.

### Why the integration tests do not need the real frontend
The `frontend` integration needs `home-assistant-frontend`, which is not in the lock file (see
`tests/integration/test_card_resource.py`). Tests mark `frontend` as loaded (`hass.config.components.add`) and set
`hass.data[DATA_PANELS] = {}`, then let the code call the **real** `panel_custom.async_register_panel` /
`frontend.async_remove_panel`. This exercises the real signatures on both CI legs (HA 2025.4.0 and latest), which is
the main risk of this task; `add_extra_js_url` is patched as today.

## Files
- create: `custom_components/energy_cost_stats/panel.py` — `async_setup_panel(hass, entry, settings) -> None`
  (register when shown, `entry.async_on_unload` removal, `ValueError` → warning); the only module importing
  `panel_custom` / `async_remove_panel`.
- modify: `custom_components/energy_cost_stats/frontend.py` — keep the versioned card URL in `hass.data` (a
  `HassKey[str]`, e.g. `DATA_CARD_MODULE_URL`) and expose `card_module_url(hass) -> str | None`.
- modify: `custom_components/energy_cost_stats/const.py` — `PANEL_URL_PATH = "energy-cost-stats"`,
  `PANEL_ELEMENT = "energy-cost-stats-panel"`; drop "not implemented yet" from the panel defaults comment.
- modify: `custom_components/energy_cost_stats/__init__.py` — call `async_setup_panel` at the end of
  `async_setup_entry`; module docstring (one sidebar panel, still no per-device entities).
- modify: `custom_components/energy_cost_stats/settings.py` — `PanelSettings` docstring only.
- modify: `custom_components/energy_cost_stats/manifest.json` — `"after_dependencies": ["frontend", "energy",
  "panel_custom"]`.
- modify: `custom_components/energy_cost_stats/strings.json` and `translations/en.json` — General step sidebar
  description: no longer "not available yet" (describe what it does; a hint that an empty title/icon keeps the
  current value is fine).
- create: `frontend/src/panel.ts` — `EnergyCostStatsPanel` (LitElement): properties `hass` (with `hassChanged`),
  `narrow`, `route`, `panel`; top bar + card; card config from `panel.config.card` if present (reserved, not sent by
  the backend in this task) merged over `{ type: "custom:energy-cost-stats-card", title: "" }`.
- modify: `frontend/src/index.ts` — `defineCard()` also defines `energy-cost-stats-panel` (guarded by
  `registry.get`), not added to `window.customCards`.
- modify: `frontend/src/card.ts` — an empty-string `title` hides the card's title text (today `""` renders an empty
  title div; make the header row collapse cleanly, keep `undefined` → default title).
- modify: `frontend/src/i18n.ts` — only if the panel needs a string (e.g. the menu button's `aria-label`).
- create: `frontend/test/panel.test.ts`; modify: `frontend/test/register.test.ts`, `frontend/test/card.test.ts`.
- modify: `custom_components/energy_cost_stats/frontend/energy-cost-stats-card.js` — rebuilt bundle.
- create: `tests/integration/test_panel.py`.
- modify: `docs/SPEC.md` (§2 `panel` option now effective, new "Sidebar panel" paragraph in §4.1 or a §4.1.1),
  `docs/CONFIG-DESIGN.md` (row 023 wording: "integration panel with the card and its period picker").

## Tests to write first
| Level | Test | Asserts |
|---|---|---|
| integration | `tests/integration/test_panel.py::test_panel_registered_when_shown` | frontend marked loaded, `hass.data[DATA_PANELS] = {}`; entry with `panel: {show: true, title: "Energy cost", icon: "mdi:cash-multiple"}` loads → panel `energy-cost-stats` exists with `component_name == "custom"`, those sidebar title/icon, `require_admin is False`, `config["_panel_custom"]` has `name == "energy-cost-stats-panel"`, `embed_iframe is False` and `module_url` equal to the URL passed to `add_extra_js_url` |
| integration | `test_panel.py::test_no_panel_when_hidden_or_unset` | `panel.show: false` → no panel; no `panel` option at all → no panel |
| integration | `test_panel.py::test_no_panel_without_frontend` | frontend not loaded → entry loads, nothing registered, no error logged |
| integration | `test_panel.py::test_options_change_updates_panel_live` | through the General options step: show on → panel present; change title and icon → the same path has the new values (exactly one panel of ours); show off → panel gone; only entry reloads, no HA restart |
| integration | `test_panel.py::test_unload_and_remove_drop_panel` | `async_unload` → panel gone; set up again → back; `async_remove` → gone; no "Removing unknown panel" warning in `caplog` |
| integration | `test_panel.py::test_path_conflict_is_not_fatal` | a foreign panel already at `energy-cost-stats` → entry state `LOADED`, a warning logged, the foreign panel untouched, still present after our entry unloads |
| integration | `test_panel.py::test_yaml_mode_panel` | YAML block with `panel: {show: true, title: "Costs", icon: "mdi:flash"}` → panel with those values; block changed to `show: false` and `energy_cost_stats.reload` called → panel gone; back to `true` → present |
| integration | `test_panel.py::test_card_extra_module_registered_once` | with the panel shown, across setup and one options reload `add_extra_js_url` is called exactly once; the panel's `module_url` is that same URL |
| card | `frontend/test/panel.test.ts::renders the card with hass` | mount the panel with `hass`, `narrow: false`, `panel: {title: "Energy cost", config: {}}` → shadow root has one `energy-cost-stats-card` (instance of `EnergyCostStatsCard`) whose `hass` is the given object; a `report` `callWS` is made |
| card | `panel.test.ts::shows the panel title in the top bar` | the top bar text equals `panel.title`; the card's own title text is empty |
| card | `panel.test.ts::menu button only when narrow` | `narrow: false` → no menu button; `narrow: true` → button present, click dispatches `hass-toggle-menu` with `bubbles` and `composed` true |
| card | `panel.test.ts::forwards hass updates without re-rendering` | spy on the panel's `render`; entity-only `hass` update → panel not re-rendered, card `hass` is the new object, no new `callWS`; language change → panel re-rendered |
| card | `panel.test.ts::properties set before definition survive` | create the element by tag name before it is defined, set `hass` / `narrow` / `panel`, then define → rendered with those values |
| card | `panel.test.ts::card config from panel.config.card` | `panel.config.card = {period: "last_month"}` → the card's initial period is last month; an invalid card config shows an error message in the panel instead of throwing |
| card | `register.test.ts::defines the panel once and not as a card` | `defineCard()` twice → both elements defined once, no throw; `window.customCards` has only the card |
| card | `card.test.ts::an empty title hides the title text` | `title: ""` → no title text node, header controls still rendered; no `title` → default title |

## Acceptance criteria
- [x] Tests above written first (failing), then green: `uv run --group ha pytest -m integration tests/integration/test_panel.py`
      and `npm test` (in `frontend/`).
- [ ] `script/test` (container) → all tests pass, coverage gate met; both CI legs (`test (py3.13, HA 2025.4.0)`,
      `test (py3.14, HA latest)`) green — the panel tests call the real `panel_custom` / `frontend` functions.
- [x] `uv run pytest -m unit`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run --group ha pyright` → pass.
- [x] `npm run typecheck` → no errors; `npm run build` run and the bundle committed; `npm run check-bundle` → passes.
- [x] `grep -rn "panel_custom\|async_remove_panel" custom_components/` → only `panel.py` (and `manifest.json`).
- [x] `grep -rn "async_register_built_in_panel" custom_components/` → no matches (positional-argument drift).
- [x] No new entity or platform: the `PLATFORMS` / `async_forward_entry_setups` lines in
      `custom_components/energy_cost_stats/` are unchanged against the base branch (`git diff` shows none).
- [ ] `hassfest` and `hacs` CI jobs green with the manifest change.
- [x] `strings.json` and `translations/en.json` identical for the General step; the "not available yet" text is gone.
- [x] `docs/SPEC.md` describes the panel (path, element, same module URL, not admin-only, lifecycle via entry reload,
      conflict handling, YAML mode) and §2 no longer says the `panel` option has no effect; CONFIG-DESIGN row 023
      reworded.
- [ ] Manual (dev HA, `script/develop`): enabling "Show in sidebar" adds the entry without a restart; the page shows
      the card full width; title / icon changes and disabling apply immediately; reloading the browser on the panel
      URL works; a dashboard with the card still works; devtools Network shows the bundle requested once per page
      load (same `?v=` URL); on a phone-width viewport the menu button opens the sidebar.
- [ ] Implementation notes record whether hassfest needed `panel_custom` declared.

## Out of scope
- Using HA's Energy date picker (`hui-energy-period-selector`) or the Energy dashboard's data collection.
- A tab inside the built-in Energy panel (rejected in CONFIG-DESIGN "Decisions").
- Panel-level card options in the integration settings (`panel.card`: period, grouping, entities) — `panel.config.card`
  is read by the element but the backend sends none; a follow-up may add it to the schema and the General step.
- Admin-only option, sidebar visibility default (`sidebar_default_visible` / `show_in_sidebar` exist only on newer HA).
- Russian translations of the General step (task 024).
- Several panels or per-user panels.

## Open questions
1. **Energy date picker.** Default: the card's own period picker (HA's picker is internal and bound to the Energy
   dashboard collection). Alternative: try to embed `hui-energy-period-selector` with a private collection —
   fragile across frontend releases. Confirm and accept the CONFIG-DESIGN rewording.
2. **Admin-only.** Default: visible to all users (same data as the card, websocket commands not admin-only).
   Alternative: `require_admin: true`, or a `panel.require_admin` option (schema change in UI and YAML).
3. **Card title inside the panel.** Default: hidden (the top bar shows the panel title). Alternative: keep the card's
   default title as well.
4. **Menu button visibility.** Default: shown when `narrow`. Alternative: also when the user's sidebar is set to
   "always hidden" — needs the frontend's UI settings, not part of the panel properties.
5. **URL path.** Default: fixed `energy-cost-stats`. Alternative: make it configurable (`panel.url_path`) to resolve
   conflicts — not needed unless a conflict is reported.

## Implementation notes
- `panel_custom.async_register_panel` is a coroutine in both HA versions, so `async_setup_panel` in `panel.py` is
  async and awaited at the end of `async_setup_entry`. It is called with keyword arguments only.
- Open questions: planner defaults used (card's own period picker, not admin-only, card title hidden, menu button
  when `narrow`, fixed URL path).
- `panel.ts` declares `hass` with `noAccessor` and its own accessor: every new `hass` is forwarded to the card at
  once, while the panel re-renders only under `hassChanged`. The card element is created in `willUpdate` and
  rebuilt only when its config changes; an invalid card config renders an alert instead of throwing.
- Card: an empty `title` omits the title text; the header row is rendered only if there is a title or the loading
  hint. `menu` string added in English and Russian.
- `defineCard()` defines the card first, then the panel; each is guarded separately by `registry.get`.
- hassfest: `panel_custom` was added to `after_dependencies` as planned; whether hassfest requires it is confirmed
  only by the CI `hassfest` job (not run locally).
- Not done locally: the manual dev-HA check, CI legs (3.13 / HA 2025.4.0), hassfest and hacs.
## Follow-ups
