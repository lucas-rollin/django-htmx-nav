#!/usr/bin/env python3
"""Cross-platform runner for the repository's full CI checks.

Mirrors the checks defined in `.github/workflows/ci.yml`.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(
    label: str,
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
) -> None:
    print(f"\n==> {label}")
    print(f"    {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def _uv_run(
    groups: list[str],
    args: list[str],
    *,
    offline: bool = False,
) -> list[str]:
    cmd = ["uv", "run", "--frozen"]
    if offline:
        cmd.append("--offline")
    for group in groups:
        cmd.extend(["--group", group])
    cmd.extend(args)
    return cmd


def run_lint(*, offline: bool) -> None:
    _run("Ruff lint", _uv_run(["lint"], ["ruff", "check", "."], offline=offline))
    _run(
        "Ruff format check",
        _uv_run(["lint"], ["ruff", "format", "--check", "."], offline=offline),
    )
    _run(
        "djLint template check",
        _uv_run(["lint"], ["djlint", "--check", "example/"], offline=offline),
    )
    _run("Mypy type check", _uv_run(["lint"], ["mypy"], offline=offline))


def run_test(*, offline: bool) -> None:
    _run("Package unit tests", _uv_run(["test"], ["pytest", "tests/"], offline=offline))


def run_example(*, offline: bool) -> None:
    _run(
        "Example application tests",
        _uv_run(
            ["test", "example"],
            ["pytest", "-c", "example/pytest.ini", "example/"],
            offline=offline,
        ),
    )


def run_build(*, offline: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="htmx-nav-ci-") as tmp:
        tmp_path = Path(tmp)
        dist_dir = tmp_path / "dist"
        site_dir = tmp_path / "site"

        build_cmd = ["uv", "build", "--out-dir", str(dist_dir)]
        if offline:
            build_cmd.append("--offline")
        _run("Build sdist and wheel", build_cmd)

        wheels = list(dist_dir.glob("*.whl"))
        if not wheels:
            raise RuntimeError(f"No wheel found in {dist_dir}")

        smoke_cmd = ["uv", "run", "--isolated", "--no-project"]
        if offline:
            smoke_cmd.append("--offline")
        smoke_script = (
            "import importlib.metadata, htmx_nav; "
            'v = importlib.metadata.version("django-htmx-nav"); '
            'print(f"Verified {htmx_nav.__name__} {v}")'
        )
        smoke_cmd.extend(["--with", str(wheels[0]), "python", "-c", smoke_script])
        _run("Smoke-test built wheel", smoke_cmd)

        static_env = {
            **os.environ,
            "ENVIRONMENT": "static_generation",
            "STATIC_ROOT": str(site_dir / "static"),
            "STATIC_URL": "/django-htmx-nav/static/",
        }
        _run(
            "Collect static files",
            _uv_run(
                ["docs", "example"],
                ["python", "example/manage.py", "collectstatic", "--noinput"],
                offline=offline,
            ),
            env=static_env,
        )
        _run(
            "Freeze static site",
            _uv_run(
                ["docs", "example"],
                [
                    "python",
                    "example/manage.py",
                    "freeze_static_pages",
                    "--out",
                    str(site_dir),
                    "--prefix",
                    "/django-htmx-nav/",
                ],
                offline=offline,
            ),
            env=static_env,
        )
        _run(
            "Build Sphinx docs",
            _uv_run(
                ["docs", "example"],
                ["sphinx-build", "-b", "html", "docs", str(site_dir / "docs")],
                offline=offline,
            ),
            env=static_env,
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        choices=("lint", "test", "example", "build"),
        help="Run only a single CI stage.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip wheel build, static freeze, and Sphinx docs build.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Pass --offline to uv commands.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    stages = {
        "lint": run_lint,
        "test": run_test,
        "example": run_example,
        "build": run_build,
    }

    if args.only:
        selected = [args.only]
    elif args.quick:
        selected = ["lint", "test", "example"]
    else:
        selected = ["lint", "test", "example", "build"]

    try:
        for name in selected:
            stages[name](offline=args.offline)
    except subprocess.CalledProcessError as exc:
        print(f"\nCI check failed (exit code {exc.returncode}).", file=sys.stderr)
        return exc.returncode

    print("\nAll selected CI checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
