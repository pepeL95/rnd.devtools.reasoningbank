"""Hierarchical ReasoningBank configuration discovery and persistence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

CONFIG_BASENAME = ".reasoningbankconfig"


@dataclass
class ReasoningBankConfig:
    path: Path
    root: Optional[str] = None
    repo_path: Optional[str] = None

    def resolved_root(self) -> Optional[Path]:
        if not self.root:
            return None
        value = Path(self.root).expanduser()
        if value.is_absolute():
            return value
        return (self.path.parent / value).resolve()

    def resolved_repo_path(self) -> Optional[Path]:
        if not self.repo_path:
            return None
        value = Path(self.repo_path).expanduser()
        if value.is_absolute():
            return value
        return (self.path.parent / value).resolve()


@dataclass
class EffectiveSettings:
    source: Optional[Path]
    root: Path
    repo_path: Path

    @property
    def repo_name(self) -> str:
        return self.repo_path.name


def config_path_for(directory: Path) -> Path:
    return directory / CONFIG_BASENAME


def global_config_path() -> Path:
    return Path.home() / CONFIG_BASENAME


def load_config(path: Path) -> ReasoningBankConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("config file must contain a mapping")
    root = data.get("root")
    repo_path = data.get("repo_path")
    if root is not None and not isinstance(root, str):
        raise ValueError("config.root must be a string")
    if repo_path is not None and not isinstance(repo_path, str):
        raise ValueError("config.repo_path must be a string")
    return ReasoningBankConfig(path=path, root=root, repo_path=repo_path)


def discover_config(start: Path) -> Optional[ReasoningBankConfig]:
    current = start.resolve()
    for directory in (current, *current.parents):
        candidate = config_path_for(directory)
        if candidate.exists():
            return load_config(candidate)
    candidate = global_config_path()
    if candidate.exists():
        return load_config(candidate)
    return None


def resolve_settings(start: Path, root_override: Optional[str], repo_override: Optional[str]) -> EffectiveSettings:
    config = discover_config(start)
    if root_override:
        root = Path(root_override).expanduser()
        if not root.is_absolute():
            root = (start.resolve() / root).resolve()
    elif config and config.resolved_root():
        root = config.resolved_root()
    else:
        root = (start.resolve() / ".reasoningbank").resolve()

    if repo_override:
        repo_path = Path(repo_override).expanduser()
        if not repo_path.is_absolute():
            repo_path = (start.resolve() / repo_override).resolve()
    elif config and config.resolved_repo_path():
        repo_path = config.resolved_repo_path()
    else:
        repo_path = start.resolve()

    return EffectiveSettings(
        source=config.path if config else None,
        root=root,
        repo_path=repo_path,
    )


def write_config(path: Path, root: str, repo_path: str) -> None:
    payload: Dict[str, Any] = {
        "root": root,
        "repo_path": repo_path,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

