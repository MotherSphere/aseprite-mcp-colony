"""Bundled creative presets: palettes, dither patterns, tile templates, animation cycles, reference data.

Layout (relative to repo root):

    presets/
      palettes/
        manifest.json
        <slug>.gpl
      dither/
        manifest.json
        patterns.json
        kernels.json
      tiles/
        manifest.json
        <slug>.json          # template definition (size + layers + guide pixels)
      animation/
        manifest.json
        cycles.json
      reference/
        pixel_art_principles.json
        sprite_size_conventions.json
        color_theory.json
        easing_curves.json
        dither_guidance.json
        animation_principles.json

Each manifest.json has shape:

    {
      "version": 1,
      "category": "<name>",
      "entries": [
        {"slug": "...", "name": "...", "tags": [...], ...category-specific...}
      ]
    }

The loader caches manifests on first read. All paths returned are absolute.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    # aseprite_mcp/presets.py -> repo root one level up from package dir
    return Path(__file__).resolve().parent.parent


def presets_dir() -> Path:
    return _repo_root() / "presets"


def category_dir(category: str) -> Path:
    safe = {"palettes", "dither", "tiles", "animation", "reference"}
    if category not in safe:
        raise ValueError(f"Unknown preset category: {category}")
    return presets_dir() / category


@lru_cache(maxsize=16)
def load_manifest(category: str) -> dict[str, Any]:
    path = category_dir(category) / "manifest.json"
    if not path.exists():
        return {"version": 1, "category": category, "entries": []}
    with path.open() as f:
        data = json.load(f)
    if "entries" not in data:
        data["entries"] = []
    return data


def load_json(category: str, name: str) -> dict[str, Any]:
    """Load an arbitrary json sibling of manifest.json under a category."""
    path = category_dir(category) / name
    if not path.exists():
        raise FileNotFoundError(str(path))
    with path.open() as f:
        return json.load(f)


def find_entry(category: str, slug: str) -> dict[str, Any] | None:
    manifest = load_manifest(category)
    for entry in manifest["entries"]:
        if entry.get("slug") == slug:
            return entry
    return None


def entry_file(category: str, slug: str, key: str = "file") -> Path:
    entry = find_entry(category, slug)
    if entry is None:
        raise KeyError(f"No {category} preset with slug={slug!r}")
    fname = entry.get(key)
    if not fname:
        raise KeyError(f"Preset {slug!r} has no {key!r} field")
    p = category_dir(category) / fname
    if not p.exists():
        raise FileNotFoundError(str(p))
    return p


def list_entries(
    category: str,
    tag: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """Return entries optionally filtered by tag (exact) or search (case-insensitive name/desc/tag substring)."""
    manifest = load_manifest(category)
    entries = manifest["entries"]
    if tag:
        entries = [e for e in entries if tag in (e.get("tags") or [])]
    if search:
        q = search.lower()
        kept = []
        for e in entries:
            hay = " ".join(
                str(v).lower()
                for k, v in e.items()
                if k in {"name", "slug", "description", "creator"}
                or (k == "tags" and isinstance(v, list))
            )
            if isinstance(e.get("tags"), list):
                hay = hay + " " + " ".join(t.lower() for t in e["tags"])
            if q in hay:
                kept.append(e)
        entries = kept
    return entries


def reference_topics() -> list[str]:
    d = category_dir("reference")
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json") if p.name != "manifest.json")


def load_reference(topic: str) -> dict[str, Any]:
    safe = topic.replace("/", "_").replace("..", "_")
    path = category_dir("reference") / f"{safe}.json"
    if not path.exists():
        raise FileNotFoundError(f"Reference topic {topic!r} not found at {path}")
    with path.open() as f:
        return json.load(f)
