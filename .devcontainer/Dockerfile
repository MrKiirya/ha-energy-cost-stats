FROM mcr.microsoft.com/devcontainers/python:3-3.14-trixie

# Pinned exact uv version (uv Docker guide recommends COPY --from, no "latest").
COPY --from=ghcr.io/astral-sh/uv:0.12.18 /uv /uvx /bin/

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    ffmpeg \
    libturbojpeg0 \
    libpcap-dev && \
    rm -rf /var/lib/apt/lists/*

# go2rtc: default_config's go2rtc integration looks for this binary
# (shutil.which) and fails default_config's dependencies without it when
# running in Docker (see tasks/008-dev-ha-fixes.md). Pinned to the version and
# digest HA core itself uses in its production Dockerfile, which is kept in
# sync with go2rtc's RECOMMENDED_VERSION const
# (homeassistant/components/go2rtc/const.py) by Renovate; bump both together
# (see CLAUDE.md "Bumping latest HA").
COPY --from=ghcr.io/alexxit/go2rtc:1.9.14@sha256:675c318b23c06fd862a61d262240c9a63436b4050d177ffc68a32710d9e05bae /usr/local/bin/go2rtc /bin/go2rtc

# Keep the uv-managed venv and cache out of the Windows bind mount (see
# .devcontainer/devcontainer.json and tasks/002-devcontainer.md decision 2).
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_LINK_MODE=copy

# Pre-create every named-volume mount point with vscode ownership: an empty named
# volume otherwise gets mounted as root:root 755, which would block script/develop
# (runs as vscode) from writing to /home/vscode/.ha-config.
RUN install -d -o vscode -g vscode /opt/venv /home/vscode/.cache/uv /home/vscode/.ha-config
