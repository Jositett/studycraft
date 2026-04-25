"""
StudyCraft – Web research helper.

Builds subject-aware search queries and returns enriched context
for each chapter/subchapter.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from rich.console import Console

console = Console()

# Cache configuration
_RESEARCH_CACHE = Path.home() / ".studycraft" / "research_cache.json"
_CACHE_TTL = 3600 * 6  # 6 hours


def _load_cache() -> dict:
    if _RESEARCH_CACHE.exists():
        try:
            with open(_RESEARCH_CACHE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(key: str, result: str) -> None:
    cache = _load_cache()
    cache[key] = {"result": result, "ts": time.time()}
    try:
        _RESEARCH_CACHE.parent.mkdir(parents=True, exist_ok=True)
        with open(_RESEARCH_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except Exception:
        pass


def research(
    subject: str,
    chapter_title: str,
    subchapter_titles: list[str] | None = None,
    max_results: int = 4,
) -> str:
    """
    Run one or more DuckDuckGo searches and return a formatted
    research context string.

    Queries generated:
      - "{subject} {chapter_title} tutorial examples"
      - "{subject} {chapter_title} best practices"
      - One query per subchapter (up to 3 subs)
    """
    queries = _build_queries(subject, chapter_title, subchapter_titles)
    all_results: list[str] = []

    for q in queries:
        results = _search(q, max_results)
        if results:
            all_results.append(f"### Query: {q}\n{results}")

    return "\n\n".join(all_results) if all_results else "(no web results available)"


def _build_queries(
    subject: str,
    chapter_title: str,
    subchapter_titles: list[str] | None,
) -> list[str]:
    queries = [
        f"{subject} {chapter_title} tutorial examples",
        f"{subject} {chapter_title} best practices",
    ]
    if subchapter_titles:
        for sub in subchapter_titles[:3]:
            queries.append(f"{subject} {sub} explained")
    return queries


def _search(query: str, max_results: int) -> str:
    console.print(f"  [dim]🔍 {query!r}[/dim]")
    # Check cache
    key = hashlib.md5(query.encode()).hexdigest()
    cache = _load_cache()
    if key in cache and time.time() - cache[key].get("ts", 0) < _CACHE_TTL:
        return cache[key]["result"]

    try:
        from ddgs import DDGS

        hits = DDGS().text(query, max_results=max_results, timeout=8)
        if not hits:
            _save_cache(key, "")
            return ""
        lines = []
        for h in hits:
            title = h.get("title", "")
            body = h.get("body", "")
            href = h.get("href", "")
            lines.append(f"**{title}** ({href})\n{body}")
        result = "\n\n".join(lines)
        _save_cache(key, result)
        return result
    except Exception as exc:
        console.print(f"  [dim yellow]⚠ Search failed: {exc}[/dim yellow]")
        return ""
