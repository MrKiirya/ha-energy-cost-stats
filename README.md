# Energy Cost Stats

[![CI](https://github.com/MrKiirya/ha-energy-cost-stats/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/MrKiirya/ha-energy-cost-stats/actions/workflows/ci.yml)

Home Assistant custom integration and Lovelace card that calculates electricity cost
**per device, split by tariff zones** (day/night, peak/semi-peak/off-peak), for any period —
retroactively, from Home Assistant's existing long-term statistics, without creating per-device entities.

> **Status:** work in progress, not ready for use yet.

## Development

Two setups, managed with [uv](https://docs.astral.sh/uv/):
- **Windows native:** `uv sync` installs cross-platform tooling only (pytest, ruff, pyright); run engine
  unit tests and lint here (`uv run pytest -m unit`, `uv run ruff check .`).
- **Linux container / CI:** `script/setup` (= `uv sync --group ha`) additionally installs Home Assistant;
  run integration tests, `pyright` and the dev HA instance here (`script/test`, `script/lint`,
  `uv run --group ha pytest -m integration`).

See [CLAUDE.md](CLAUDE.md) for the full command reference and project conventions.

## License

[MIT](LICENSE)
