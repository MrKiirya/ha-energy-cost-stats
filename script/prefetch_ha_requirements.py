#!/usr/bin/env python3
"""Pre-install the pip requirements Home Assistant would otherwise install by
itself, at runtime, the first time `script/develop` starts a dev instance.

Background: `homeassistant.util.package.install_package()` shells out to
`python -m uv pip install ...` for every integration requirement that isn't
already present in the venv (see `homeassistant/requirements.py`,
`RequirementsManager._async_process_integration`, which walks both
`dependencies` *and* `after_dependencies`). With `default_config:` enabled,
that includes the frontend package and everything `default_config`'s
dependency tree needs (camera/stream codecs, discovery protocols, ...). Those
installs run concurrently with `script/develop` importing/starting Home
Assistant; if a *separate* `uv sync` (an exact sync) runs at the same time, it
can remove a package HA's own install just added mid-startup and push the dev
instance into recovery mode (see tasks/002-devcontainer.md, "Human report —
HA ends in recovery mode"). Running all of this once, up front, in
`script/setup` avoids any runtime install racing with anything else.

This module is deliberately stdlib-only and split into pure functions (no
`homeassistant` import at module level) so the manifest-walking logic is
unit-testable without Home Assistant installed; only `main()` needs the `ha`
dependency group, and is exercised by `script/setup` itself, not by pytest.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

# default_config: everything a default dev config pulls in.
# frontend: not a dependency of default_config, but the dev UI we always want,
#   and per tasks/002-devcontainer.md follow-up it must never be optional.
ROOT_DOMAINS = ("default_config", "frontend")

# Requirements that must install successfully, or the whole run fails: without
# these, script/develop's first start would still trigger a live runtime
# install (frontend) or Home Assistant would refuse to start at all.
CRITICAL_DOMAINS = ("frontend",)


def find_manifest(components_dir: Path, domain: str) -> dict | None:
    """Load a built-in integration's manifest.json, or None if it has none
    (e.g. a virtual/alias domain with no components/<domain> directory)."""
    manifest_path = components_dir / domain / "manifest.json"
    if not manifest_path.is_file():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _manifest_deps(manifest: dict) -> tuple[str, ...]:
    """Both `dependencies` and `after_dependencies`: Home Assistant's
    requirements manager installs requirements for after_dependencies too
    (checked against homeassistant/requirements.py at implementation time)."""
    return (*manifest.get("dependencies", []), *manifest.get("after_dependencies", []))


def collect_requirements(
    components_dir: Path,
    root_domains: Iterable[str] = ROOT_DOMAINS,
    extra_manifests: Iterable[dict] | None = None,
    critical_domains: Iterable[str] = CRITICAL_DOMAINS,
) -> tuple[list[str], list[str]]:
    """Walk manifest dependencies from the given root domains, plus any
    extra manifests (e.g. our own integration's manifest.json, which is not
    a built-in component under `components_dir`), and return
    `(all_requirements, critical_requirements)`, both sorted and deduplicated.

    `critical_requirements` is the subset that came directly from a manifest
    of one of `critical_domains` (not transitively): the requirements that
    must never be treated as best-effort.
    """
    seen_domains: set[str] = set()
    requirements: set[str] = set()

    def visit(domain: str) -> None:
        if domain in seen_domains:
            return
        seen_domains.add(domain)
        manifest = find_manifest(components_dir, domain)
        if manifest is None:
            return
        requirements.update(manifest.get("requirements", []))
        for dep in _manifest_deps(manifest):
            visit(dep)

    for domain in root_domains:
        visit(domain)

    for manifest in extra_manifests or ():
        requirements.update(manifest.get("requirements", []))
        for dep in _manifest_deps(manifest):
            visit(dep)

    critical_requirements: set[str] = set()
    for domain in critical_domains:
        manifest = find_manifest(components_dir, domain)
        if manifest is not None:
            critical_requirements.update(manifest.get("requirements", []))

    return sorted(requirements), sorted(critical_requirements)


def missing_requirements(requirements: Iterable[str]) -> list[str]:
    """Return the subset of pip requirement strings that are not already
    installed with a satisfying version, so repeat runs of script/setup are
    fast and don't re-hit the network for nothing."""
    from importlib.metadata import PackageNotFoundError, version

    from packaging.requirements import InvalidRequirement, Requirement

    missing: list[str] = []
    for req_str in requirements:
        try:
            req = Requirement(req_str)
        except InvalidRequirement:
            missing.append(req_str)
            continue
        try:
            installed_version = version(req.name)
        except PackageNotFoundError:
            missing.append(req_str)
            continue
        if not req.specifier.contains(installed_version, prereleases=True):
            missing.append(req_str)
    return missing


def install_requirements(
    requirements: Iterable[str],
    constraints: Path,
    python_executable: str | None = None,
) -> list[str]:
    """Install requirements one at a time (mirrors the flags Home Assistant's
    own install_package() uses), so a single package without a wheel for this
    platform doesn't block installing the rest. Returns the requirements that
    failed to install."""
    failures: list[str] = []
    for req in requirements:
        cmd = [
            python_executable or sys.executable,
            "-m",
            "uv",
            "pip",
            "install",
            "--quiet",
            req,
            "--index-strategy",
            "unsafe-first-match",
            "--constraint",
            str(constraints),
        ]
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            failures.append(req)
    return failures


def summarize_failures(
    failures: Iterable[str], critical_requirements: Iterable[str]
) -> int:
    """Classify the requirements that failed to install and print
    diagnostics; return the process exit code for main(): 0 if nothing
    failed, or only best-effort (non-frontend) requirements failed; 1 if any
    critical (frontend) requirement failed, since script/develop would then
    still trigger a live install for it and the frontend must not be
    optional (see tasks/002-devcontainer.md follow-up round)."""
    failures = list(failures)
    if not failures:
        return 0

    critical_set = set(critical_requirements)
    critical_failures = [req for req in failures if req in critical_set]
    for req in failures:
        kind = "critical" if req in critical_failures else "best-effort"
        print(
            f"energy_cost_stats: failed to pre-install {kind} requirement {req!r}"
            " (see uv's output above).",
            file=sys.stderr,
        )

    if critical_failures:
        print(
            "energy_cost_stats: aborting script/setup: a critical requirement "
            "(needed for the frontend to load) failed to install.",
            file=sys.stderr,
        )
        return 1

    print(
        "energy_cost_stats: continuing despite the best-effort failure(s) above; "
        "script/develop may still trigger a live install for those specific "
        "packages on first start (see tasks/002-devcontainer.md decision 6 for "
        "known unrelated default_config failures, e.g. go2rtc without a Docker "
        "socket).",
        file=sys.stderr,
    )
    return 0


def _own_manifest(repo_root: Path) -> dict:
    manifest_path = (
        repo_root / "custom_components" / "energy_cost_stats" / "manifest.json"
    )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be installed and exit without installing anything",
    )
    args = parser.parse_args(argv)

    import homeassistant
    from homeassistant.const import BASE_PLATFORMS

    ha_dir = Path(homeassistant.__file__).resolve().parent
    components_dir = ha_dir / "components"
    constraints = ha_dir / "package_constraints.txt"
    repo_root = Path(__file__).resolve().parent.parent

    # Home Assistant's bootstrap always resolves and installs requirements for
    # every BASE_PLATFORMS domain (homeassistant/bootstrap.py,
    # _async_resolve_domains_and_preload: "Also process all base platforms
    # since we do not require the manifest to list them as dependencies"),
    # regardless of default_config: or any other config -- e.g. radio_frequency
    # and infrared, which are not reachable from default_config's manifest tree
    # at all. Confirmed by observing "Attempting install of rf-protocols"/
    # "infrared-protocols" on a fresh dev instance even though this pre-install
    # step's default_config walk did not include them.
    root_domains = (*ROOT_DOMAINS, *BASE_PLATFORMS)

    all_requirements, critical_requirements = collect_requirements(
        components_dir,
        root_domains=root_domains,
        extra_manifests=[_own_manifest(repo_root)],
    )
    to_install = missing_requirements(all_requirements)

    if not to_install:
        print(
            "energy_cost_stats: all Home Assistant runtime requirements already "
            "installed."
        )
        return 0

    print(
        f"energy_cost_stats: pre-installing {len(to_install)} Home Assistant "
        f"runtime requirement(s) so script/develop won't install them at "
        f"startup: {', '.join(to_install)}"
    )
    if args.dry_run:
        return 0

    failures = install_requirements(to_install, constraints)
    return summarize_failures(failures, critical_requirements)


if __name__ == "__main__":
    raise SystemExit(main())
