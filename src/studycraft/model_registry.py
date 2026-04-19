"""
StudyCraft -- Model registry.

Fetches available models from the OpenRouter API, caches them locally
as JSON, and provides query/filter methods (free, vision, etc.).

Cache lives at ~/.studycraft/models.json and refreshes every 24h.
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()

_CACHE_DIR = Path.home() / ".studycraft"
_CACHE_FILE = _CACHE_DIR / "models.json"
_CACHE_TTL = 86400  # 24 hours
_API_URL = "https://openrouter.ai/api/v1/models"


def fetch_models(force: bool = False) -> list[dict[str, Any]]:
    """Fetch models from OpenRouter, using cache if fresh."""
    if not force and _CACHE_FILE.exists():
        try:
            data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            if time.time() - data.get("fetched_at", 0) < _CACHE_TTL:
                return data["models"]
        except (json.JSONDecodeError, KeyError):
            pass

    console.print("[dim]Fetching models from OpenRouter...[/dim]")
    try:
        req = urllib.request.Request(_API_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError) as exc:
        console.print(f"[yellow]Could not fetch models: {exc}[/yellow]")
        # Fall back to cache even if stale
        if _CACHE_FILE.exists():
            data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            return data.get("models", [])
        return []

    models = _normalize(raw.get("data", []))

    # Cache
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(
        json.dumps({"fetched_at": time.time(), "models": models}, indent=2),
        encoding="utf-8",
    )
    console.print(f"[dim]Cached {len(models)} models to {_CACHE_FILE}[/dim]")
    return models


def _normalize(raw_models: list[dict]) -> list[dict[str, Any]]:
    """Extract the fields we care about from the OpenRouter response."""
    out = []
    for m in raw_models:
        model_id = m.get("id", "")
        pricing = m.get("pricing", {})
        prompt_price = float(pricing.get("prompt", "0") or "0")
        completion_price = float(pricing.get("completion", "0") or "0")
        arch = m.get("architecture", {})
        modality = arch.get("modality", "")
        # Vision = input modality includes "image"
        input_modalities = arch.get("input_modalities", [])
        # Also check the modality string for older API format
        has_vision = (
            "image" in input_modalities
            or "image" in modality
            or "vision" in model_id.lower()
        )

        out.append(
            {
                "id": model_id,
                "name": m.get("name", model_id),
                "context_length": m.get("context_length", 0),
                "prompt_price": prompt_price,
                "completion_price": completion_price,
                "is_free": prompt_price == 0 and completion_price == 0,
                "has_vision": has_vision,
                "input_modalities": input_modalities,
                "description": m.get("description", ""),
            }
        )
    return out


def get_free_models(vision_only: bool = False) -> list[dict[str, Any]]:
    """Return free models, optionally filtered to vision-capable only."""
    models = fetch_models()
    result = [m for m in models if m["is_free"]]
    if vision_only:
        result = [m for m in result if m["has_vision"]]
    return sorted(result, key=lambda m: m["context_length"], reverse=True)


def get_vision_models(free_only: bool = False) -> list[dict[str, Any]]:
    """Return vision-capable models, optionally filtered to free only."""
    models = fetch_models()
    result = [m for m in models if m["has_vision"]]
    if free_only:
        result = [m for m in result if m["is_free"]]
    return sorted(result, key=lambda m: m["context_length"], reverse=True)


def get_model(model_id: str) -> dict[str, Any] | None:
    """Look up a specific model by ID."""
    models = fetch_models()
    for m in models:
        if m["id"] == model_id:
            return m
    return None


def search_models(query: str) -> list[dict[str, Any]]:
    """Search models by name or ID substring."""
    models = fetch_models()
    q = query.lower()
    return [m for m in models if q in m["id"].lower() or q in m["name"].lower()]
