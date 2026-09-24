"""Pure-Python calculation engine: hourly deltas + tariff plans -> report table.

Purity rule (CLAUDE.md principle 4): nothing in this package imports `homeassistant`.
Recorder access lives behind the adapter module (`recorder_adapter.py`), one level up.

Imports inside this package must be relative (`from .x import y`), never absolute
`engine...` or `custom_components...` imports, and never `from ..` (which would leave
this package and reach into the `homeassistant`-importing integration code).

Dual-name caveat: these files are imported under two different module names depending
on context:
- `engine.*` in unit tests (via the `pythonpath` pytest setting), with no Home Assistant
  installed;
- `custom_components.energy_cost_stats.engine.*` at integration runtime and in
  integration tests.

Because Python treats these as two distinct module objects, classes defined here are
*not* the same object across the two names: `isinstance` checks, module-level caches and
monkeypatching done through one name do not affect the other. Rule: unit tests import
only `engine...` and never `custom_components.energy_cost_stats...`; integration tests
go through the integration package. See tests/unit/test_engine_isolation.py.
"""
