"""
StudyCraft – Web research helper.

Builds subject-aware search queries and returns enriched context
for each chapter/subchapter.
"""

from __future__ import annotations

from rich.console import Console

console = Console()


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
    try:
        from duckduckgo_search import DDGS

        hits = DDGS().text(query, max_results=max_results)
        if not hits:
            return ""
        lines = []
        for h in hits:
            title = h.get("title", "")
            body = h.get("body", "")
            href = h.get("href", "")
            lines.append(f"**{title}** ({href})\n{body}")
        return "\n\n".join(lines)
    except Exception as exc:
        console.print(f"  [dim yellow]⚠ Search failed: {exc}[/dim yellow]")
        return ""
