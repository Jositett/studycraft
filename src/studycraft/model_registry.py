"""
StudyCraft -- Model registry.

Fetches available models from the OpenRouter API, caches them locally
as JSON, and provides query/filter methods (free, vision, etc.).

Includes model health testing: sends a 1-token probe to verify a model
is actually responding before using it for generation.

Cache lives at ~/.studycraft/models.json and refreshes every 24h.
Health results cached at ~/.studycraft/model_health.json (refreshes every 6h).
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()

_CACHE_DIR = Path.home() / ".studycraft"
_CACHE_FILE = _CACHE_DIR / "models.json"
_HEALTH_FILE = _CACHE_DIR / "model_health.json"
_CACHE_TTL = 86400  # 24 hours
_HEALTH_TTL = 21600  # 6 hours
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
        if _CACHE_FILE.exists():
            data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            return data.get("models", [])
        return []

    models = _normalize(raw.get("data", []))

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
        input_modalities = arch.get("input_modalities", [])
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


# ── Model health testing ──────────────────────────────────────────────────────


def test_model(api_key: str, model_id: str, timeout: int = 15) -> bool:
    """Send a 1-token probe to verify a model responds. Returns True if OK."""
    try:
        payload = json.dumps(
            {
                "model": model_id,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }
        ).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return bool(data.get("choices"))
    except Exception:
        return False


def get_verified_free_models(
    api_key: str | None = None, force: bool = False
) -> list[dict[str, Any]]:
    """Return free models that have passed a 1-token health check.

    Results are cached for 6 hours. If no api_key is provided,
    returns unverified free models sorted by context length.
    """
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("STUDYCRAFT_API_KEY")
    if not api_key:
        return get_free_models()

    # Check health cache
    if not force and _HEALTH_FILE.exists():
        try:
            data = json.loads(_HEALTH_FILE.read_text(encoding="utf-8"))
            if time.time() - data.get("tested_at", 0) < _HEALTH_TTL:
                healthy_ids = set(data.get("healthy", []))
                models = get_free_models()
                verified = [m for m in models if m["id"] in healthy_ids]
                if verified:
                    return verified
        except (json.JSONDecodeError, KeyError):
            pass

    console.print("[dim]Testing free models (1-token probe)...[/dim]")
    free = get_free_models()
    # Test top 15 by context length to keep it fast
    candidates = free[:15]
    healthy = []
    for m in candidates:
        ok = test_model(api_key, m["id"])
        status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
        console.print(f"  [dim]{m['id']}: {status}[/dim]")
        if ok:
            healthy.append(m)

    # Cache results
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _HEALTH_FILE.write_text(
        json.dumps(
            {
                "tested_at": time.time(),
                "healthy": [m["id"] for m in healthy],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    console.print(f"[dim]{len(healthy)}/{len(candidates)} free models healthy[/dim]")
    return healthy


def get_fallback_chain(api_key: str | None = None) -> list[str]:
    """Return an ordered list of model IDs to try as fallbacks.

    Prefers verified free models, sorted by context length descending.
    """
    verified = get_verified_free_models(api_key)
    if verified:
        return [m["id"] for m in verified]
    # Fallback: unverified free models
    return [m["id"] for m in get_free_models()[:10]]


# ── Query helpers ─────────────────────────────────────────────────────────────


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
