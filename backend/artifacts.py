"""Markdown artifact parsing, rendering, and validation."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

from models import ALLOWED_TRIGGERS

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
TAG_RE = re.compile(r"[^a-z0-9]+")
RAW_TRACE_MARKERS = (
    "chain-of-thought",
    "tool transcript",
    "raw trace",
    "<analysis>",
    "</analysis>",
)


class ArtifactValidationError(ValueError):
    """Raised when a memory artifact violates the markdown contract."""


@dataclass
class ParsedArtifact:
    frontmatter: Dict[str, Any]
    body: str


def normalize_tag(tag: str) -> str:
    return TAG_RE.sub("-", tag.strip().lower()).strip("-")


def slugify(value: str, max_length: int = 72) -> str:
    slug = normalize_tag(value)
    if len(slug) <= max_length:
        return slug
    return slug[:max_length].rstrip("-")


def parse_markdown(text: str) -> ParsedArtifact:
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ArtifactValidationError("artifact must start with YAML frontmatter")
    raw_frontmatter, body = match.groups()
    data = yaml.safe_load(raw_frontmatter) or {}
    if not isinstance(data, dict):
        raise ArtifactValidationError("frontmatter must parse to a mapping")
    return ParsedArtifact(frontmatter=data, body=body.strip())


def parse_markdown_file(path: Path) -> ParsedArtifact:
    return parse_markdown(path.read_text(encoding="utf-8"))


def validate_artifact(frontmatter: Dict[str, Any], body: str) -> None:
    for field in ("name", "description", "trigger", "tags"):
        if field not in frontmatter:
            raise ArtifactValidationError("missing required frontmatter field: %s" % field)

    name = frontmatter["name"]
    description = frontmatter["description"]
    trigger = frontmatter["trigger"]
    tags = frontmatter["tags"]

    if not isinstance(name, str) or not name.strip():
        raise ArtifactValidationError("name must be a non-empty string")
    if not isinstance(description, str) or not description.strip():
        raise ArtifactValidationError("description must be a non-empty string")
    if trigger not in ALLOWED_TRIGGERS:
        raise ArtifactValidationError("invalid trigger: %r" % trigger)
    if not isinstance(tags, list) or not tags:
        raise ArtifactValidationError("tags must be a non-empty list")

    normalized_tags = [normalize_tag(str(tag)) for tag in tags]
    if any(not tag for tag in normalized_tags):
        raise ArtifactValidationError("tags must normalize to lowercase kebab-case")
    if len(set(normalized_tags)) != len(normalized_tags):
        raise ArtifactValidationError("tags must be unique after normalization")
    if tags != normalized_tags:
        raise ArtifactValidationError("tags must already be lowercase kebab-case")

    if not body.strip():
        raise ArtifactValidationError("body must be non-empty")
    if len(body.split()) > 500:
        raise ArtifactValidationError("body exceeds 500 word MVP maximum")

    lowered = body.lower()
    if any(marker in lowered for marker in RAW_TRACE_MARKERS):
        raise ArtifactValidationError("body appears to contain raw trace content")


def render_markdown(name: str, description: str, trigger: str, tags: List[str], body: str) -> str:
    frontmatter = {
        "name": name.strip(),
        "description": description.strip(),
        "trigger": trigger,
        "tags": [normalize_tag(tag) for tag in tags],
    }
    validate_artifact(frontmatter, body)
    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False)
    return "---\n%s---\n\n%s\n" % (yaml_text, body.strip())


def body_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def memory_id_for_path(path: str) -> str:
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]
    return "mem_%s" % digest


def embedding_text(name: str, description: str, tags: List[str], body: str) -> str:
    return "Name: %s\nDescription: %s\nTags: %s\n\n%s" % (
        name,
        description,
        ", ".join(tags),
        body,
    )


def default_memory_path(repo: str, name: str, date_prefix: str) -> Path:
    return Path(".memories") / "local" / slugify(repo) / ("%s-%s.md" % (date_prefix, slugify(name)))
