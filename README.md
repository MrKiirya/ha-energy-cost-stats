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
- **Linux container / CI:** `script/setup` additionally installs Home Assistant (`uv sync --group ha`) and
  pre-installs the runtime requirements `default_config:` needs, so `script/develop` doesn't install anything
  live; run integration tests, `pyright` and the dev HA instance here (`script/test`, `script/lint`,
  `uv run --group ha pytest -m integration`). Never run a bare `uv sync` here while `script/develop` is
  running — use `script/setup` instead (see CLAUDE.md).

See [CLAUDE.md](CLAUDE.md) for the full command reference and project conventions.

### Devcontainer (recommended for full setup)

Prerequisites: Docker Desktop (Linux containers) and the VS Code Dev Containers extension.
Open the repo in VS Code and pick "Reopen in Container" to get Python 3.14, uv, Node 24 and all
dependency groups installed automatically. Inside the container, `script/develop` starts a dev Home
Assistant with this integration loaded at <http://localhost:8123>.
Performance note: the repo stays a bind mount of the Windows checkout for tool compatibility, but the
Python venv, uv cache and Home Assistant runtime data live inside the container (named Docker volumes /
`/opt/venv`), so they are not slowed down by the Windows bind mount.

### Troubleshooting

- **"Reopen in Container" fails with an error mentioning
  `accessing specified distro mount service ... /run/guest-services/distro-services/<distro>.sock`:** this is
  a Docker Desktop / WSL2 integration issue, not specific to this repo. Fix either by setting the VS Code user
  setting `"dev.containers.mountWaylandSocket": false`, or by enabling the affected WSL distro under Docker
  Desktop → Settings → Resources → WSL integration.

## License

[MIT](LICENSE)
