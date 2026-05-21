#!/usr/bin/env python3
"""Smoke test for CLI init plus hierarchical config resolution."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PYTHON = "/opt/homebrew/Caskroom/miniforge/base/envs/reasoningbank/bin/python"


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, str(BACKEND / "cli.py"), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )


def main() -> int:
    sandbox = ROOT / ".smoke_cli_init_config"
    if sandbox.exists():
        shutil.rmtree(sandbox)
    workspace = sandbox / "workspace" / "repo" / "nested"
    workspace.mkdir(parents=True)

    repo_root = workspace.parent

    init_result = run("init", cwd=repo_root)
    assert "initialized" in init_result.stdout
    assert (repo_root / ".reasoningbank").is_dir()
    assert (repo_root / ".reasoningbank" / "reasoningbank.sqlite3").exists()

    config_result = run(
        "config",
        "--root",
        ".reasoningbank",
        "--repo-path",
        str(repo_root),
        cwd=repo_root,
    )
    assert "wrote" in config_result.stdout
    assert (repo_root / ".reasoningbankconfig").exists()

    show_result = run("config", "--show", cwd=workspace)
    output = show_result.stdout
    assert str((repo_root / ".reasoningbank").resolve()) in output
    assert str(repo_root.resolve()) in output
    assert "repo_name: repo" in output

    print("cli init/config smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
