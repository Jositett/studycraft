"""
StudyCraft – Theme registry.

Each theme defines colors for all export formats (HTML, PDF, DOCX, EPUB).
Use get_theme(name) to retrieve; defaults to "dark".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    label: str

    # Page
    bg: str
    surface: str
    text: str
    muted: str
    border: str

    # Accent
    primary: str
    primary_light: str
    accent: str

    # Headings
    h1: str
    h2: str
    h3: str

    # Code
    code_bg: str
    code_fg: str
    code_inline_bg: str
    code_inline_fg: str

    # Blockquote
    quote_border: str
    quote_bg: str
    quote_fg: str

    # Table
    th_bg: str
    th_fg: str
    td_border: str
    td_alt_bg: str

    # Cover
    cover_bg_start: str
    cover_bg_end: str
    cover_fg: str

    # TOC sidebar
    toc_bg: str
    toc_border: str
    toc_hover_bg: str

    # Syntax highlighting
    syn_keyword: str
    syn_string: str
    syn_comment: str
    syn_function: str
    syn_class: str
    syn_number: str
    syn_operator: str
    syn_builtin: str


# ── Theme definitions ─────────────────────────────────────────────────────────

DARK = Theme(
    name="dark",
    label="Dark",
    bg="#0f1117",
    surface="#1a1d2e",
    text="#e2e8f0",
    muted="#8892b0",
    border="#2a2f45",
    primary="#6d9fff",
    primary_light="rgba(109,159,255,.1)",
    accent="#a78bfa",
    h1="#6d9fff",
    h2="#93b4ff",
    h3="#a78bfa",
    code_bg="#0d1117",
    code_fg="#c9d1d9",
    code_inline_bg="#1e293b",
    code_inline_fg="#a78bfa",
    quote_border="#6d9fff",
    quote_bg="rgba(109,159,255,.08)",
    quote_fg="#93b4ff",
    th_bg="#2a2f45",
    th_fg="#e2e8f0",
    td_border="#2a2f45",
    td_alt_bg="#141722",
    cover_bg_start="#1e2540",
    cover_bg_end="#0f1117",
    cover_fg="#e2e8f0",
    toc_bg="#1a1d2e",
    toc_border="#2a2f45",
    toc_hover_bg="rgba(109,159,255,.1)",
    syn_keyword="#ff79c6",
    syn_string="#a3be8c",
    syn_comment="#6272a4",
    syn_function="#61afef",
    syn_class="#e5c07b",
    syn_number="#bd93f9",
    syn_operator="#ff79c6",
    syn_builtin="#8be9fd",
)

LIGHT = Theme(
    name="light",
    label="Light",
    bg="#f9fafb",
    surface="#ffffff",
    text="#111827",
    muted="#6b7280",
    border="#e5e7eb",
    primary="#2563eb",
    primary_light="#eff6ff",
    accent="#7c3aed",
    h1="#2563eb",
    h2="#1e3a8a",
    h3="#7c3aed",
    code_bg="#1e293b",
    code_fg="#e2e8f0",
    code_inline_bg="#f1f5f9",
    code_inline_fg="#7c3aed",
    quote_border="#2563eb",
    quote_bg="#eff6ff",
    quote_fg="#1e40af",
    th_bg="#2563eb",
    th_fg="#ffffff",
    td_border="#e5e7eb",
    td_alt_bg="#f8fafc",
    cover_bg_start="#2563eb",
    cover_bg_end="#7c3aed",
    cover_fg="#ffffff",
    toc_bg="#ffffff",
    toc_border="#e5e7eb",
    toc_hover_bg="#eff6ff",
    syn_keyword="#d73a49",
    syn_string="#032f62",
    syn_comment="#6a737d",
    syn_function="#6f42c1",
    syn_class="#e36209",
    syn_number="#005cc5",
    syn_operator="#d73a49",
    syn_builtin="#005cc5",
)

NORD = Theme(
    name="nord",
    label="Nord",
    bg="#2e3440",
    surface="#3b4252",
    text="#eceff4",
    muted="#d8dee9",
    border="#4c566a",
    primary="#88c0d0",
    primary_light="rgba(136,192,208,.1)",
    accent="#b48ead",
    h1="#88c0d0",
    h2="#81a1c1",
    h3="#b48ead",
    code_bg="#2e3440",
    code_fg="#d8dee9",
    code_inline_bg="#3b4252",
    code_inline_fg="#a3be8c",
    quote_border="#88c0d0",
    quote_bg="rgba(136,192,208,.08)",
    quote_fg="#88c0d0",
    th_bg="#4c566a",
    th_fg="#eceff4",
    td_border="#4c566a",
    td_alt_bg="#3b4252",
    cover_bg_start="#4c566a",
    cover_bg_end="#2e3440",
    cover_fg="#eceff4",
    toc_bg="#3b4252",
    toc_border="#4c566a",
    toc_hover_bg="rgba(136,192,208,.1)",
    syn_keyword="#81a1c1",
    syn_string="#a3be8c",
    syn_comment="#616e88",
    syn_function="#88c0d0",
    syn_class="#ebcb8b",
    syn_number="#b48ead",
    syn_operator="#81a1c1",
    syn_builtin="#8fbcbb",
)

SOLARIZED = Theme(
    name="solarized",
    label="Solarized",
    bg="#002b36",
    surface="#073642",
    text="#93a1a1",
    muted="#657b83",
    border="#586e75",
    primary="#268bd2",
    primary_light="rgba(38,139,210,.1)",
    accent="#d33682",
    h1="#268bd2",
    h2="#2aa198",
    h3="#d33682",
    code_bg="#002b36",
    code_fg="#839496",
    code_inline_bg="#073642",
    code_inline_fg="#cb4b16",
    quote_border="#268bd2",
    quote_bg="rgba(38,139,210,.08)",
    quote_fg="#268bd2",
    th_bg="#586e75",
    th_fg="#fdf6e3",
    td_border="#586e75",
    td_alt_bg="#073642",
    cover_bg_start="#073642",
    cover_bg_end="#002b36",
    cover_fg="#93a1a1",
    toc_bg="#073642",
    toc_border="#586e75",
    toc_hover_bg="rgba(38,139,210,.1)",
    syn_keyword="#859900",
    syn_string="#2aa198",
    syn_comment="#586e75",
    syn_function="#268bd2",
    syn_class="#b58900",
    syn_number="#d33682",
    syn_operator="#859900",
    syn_builtin="#cb4b16",
)

DRACULA = Theme(
    name="dracula",
    label="Dracula",
    bg="#282a36",
    surface="#44475a",
    text="#f8f8f2",
    muted="#6272a4",
    border="#6272a4",
    primary="#bd93f9",
    primary_light="rgba(189,147,249,.1)",
    accent="#ff79c6",
    h1="#bd93f9",
    h2="#8be9fd",
    h3="#ff79c6",
    code_bg="#282a36",
    code_fg="#f8f8f2",
    code_inline_bg="#44475a",
    code_inline_fg="#50fa7b",
    quote_border="#bd93f9",
    quote_bg="rgba(189,147,249,.08)",
    quote_fg="#bd93f9",
    th_bg="#44475a",
    th_fg="#f8f8f2",
    td_border="#6272a4",
    td_alt_bg="#383a4a",
    cover_bg_start="#44475a",
    cover_bg_end="#282a36",
    cover_fg="#f8f8f2",
    toc_bg="#44475a",
    toc_border="#6272a4",
    toc_hover_bg="rgba(189,147,249,.1)",
    syn_keyword="#ff79c6",
    syn_string="#f1fa8c",
    syn_comment="#6272a4",
    syn_function="#50fa7b",
    syn_class="#8be9fd",
    syn_number="#bd93f9",
    syn_operator="#ff79c6",
    syn_builtin="#8be9fd",
)

GITHUB = Theme(
    name="github",
    label="GitHub",
    bg="#ffffff",
    surface="#ffffff",
    text="#1f2328",
    muted="#656d76",
    border="#d1d9e0",
    primary="#0969da",
    primary_light="#ddf4ff",
    accent="#8250df",
    h1="#1f2328",
    h2="#1f2328",
    h3="#656d76",
    code_bg="#f6f8fa",
    code_fg="#1f2328",
    code_inline_bg="#eff1f3",
    code_inline_fg="#0550ae",
    quote_border="#d1d9e0",
    quote_bg="#f6f8fa",
    quote_fg="#656d76",
    th_bg="#f6f8fa",
    th_fg="#1f2328",
    td_border="#d1d9e0",
    td_alt_bg="#f6f8fa",
    cover_bg_start="#0969da",
    cover_bg_end="#8250df",
    cover_fg="#ffffff",
    toc_bg="#ffffff",
    toc_border="#d1d9e0",
    toc_hover_bg="#ddf4ff",
    syn_keyword="#cf222e",
    syn_string="#0a3069",
    syn_comment="#6e7781",
    syn_function="#8250df",
    syn_class="#953800",
    syn_number="#0550ae",
    syn_operator="#cf222e",
    syn_builtin="#0550ae",
)

MONOKAI = Theme(
    name="monokai",
    label="Monokai",
    bg="#272822",
    surface="#3e3d32",
    text="#f8f8f2",
    muted="#75715e",
    border="#49483e",
    primary="#a6e22e",
    primary_light="rgba(166,226,46,.1)",
    accent="#f92672",
    h1="#a6e22e",
    h2="#66d9ef",
    h3="#f92672",
    code_bg="#272822",
    code_fg="#f8f8f2",
    code_inline_bg="#3e3d32",
    code_inline_fg="#e6db74",
    quote_border="#a6e22e",
    quote_bg="rgba(166,226,46,.08)",
    quote_fg="#a6e22e",
    th_bg="#49483e",
    th_fg="#f8f8f2",
    td_border="#49483e",
    td_alt_bg="#3e3d32",
    cover_bg_start="#3e3d32",
    cover_bg_end="#272822",
    cover_fg="#f8f8f2",
    toc_bg="#3e3d32",
    toc_border="#49483e",
    toc_hover_bg="rgba(166,226,46,.1)",
    syn_keyword="#f92672",
    syn_string="#e6db74",
    syn_comment="#75715e",
    syn_function="#a6e22e",
    syn_class="#66d9ef",
    syn_number="#ae81ff",
    syn_operator="#f92672",
    syn_builtin="#66d9ef",
)

OCEAN = Theme(
    name="ocean",
    label="Ocean",
    bg="#1b2838",
    surface="#1e3148",
    text="#c7d5e0",
    muted="#7a8fa6",
    border="#2a475e",
    primary="#66c0f4",
    primary_light="rgba(102,192,244,.1)",
    accent="#4fc3f7",
    h1="#66c0f4",
    h2="#4fc3f7",
    h3="#81d4fa",
    code_bg="#0f1923",
    code_fg="#c7d5e0",
    code_inline_bg="#1e3148",
    code_inline_fg="#66c0f4",
    quote_border="#66c0f4",
    quote_bg="rgba(102,192,244,.08)",
    quote_fg="#66c0f4",
    th_bg="#2a475e",
    th_fg="#c7d5e0",
    td_border="#2a475e",
    td_alt_bg="#1e3148",
    cover_bg_start="#2a475e",
    cover_bg_end="#1b2838",
    cover_fg="#c7d5e0",
    toc_bg="#1e3148",
    toc_border="#2a475e",
    toc_hover_bg="rgba(102,192,244,.1)",
    syn_keyword="#66c0f4",
    syn_string="#a3be8c",
    syn_comment="#546e7a",
    syn_function="#4fc3f7",
    syn_class="#81d4fa",
    syn_number="#f48fb1",
    syn_operator="#66c0f4",
    syn_builtin="#80cbc4",
)

ROSE_PINE = Theme(
    name="rose-pine",
    label="Rosé Pine",
    bg="#191724",
    surface="#1f1d2e",
    text="#e0def4",
    muted="#908caa",
    border="#26233a",
    primary="#c4a7e7",
    primary_light="rgba(196,167,231,.1)",
    accent="#ebbcba",
    h1="#c4a7e7",
    h2="#9ccfd8",
    h3="#ebbcba",
    code_bg="#191724",
    code_fg="#e0def4",
    code_inline_bg="#26233a",
    code_inline_fg="#f6c177",
    quote_border="#c4a7e7",
    quote_bg="rgba(196,167,231,.08)",
    quote_fg="#c4a7e7",
    th_bg="#26233a",
    th_fg="#e0def4",
    td_border="#26233a",
    td_alt_bg="#1f1d2e",
    cover_bg_start="#26233a",
    cover_bg_end="#191724",
    cover_fg="#e0def4",
    toc_bg="#1f1d2e",
    toc_border="#26233a",
    toc_hover_bg="rgba(196,167,231,.1)",
    syn_keyword="#c4a7e7",
    syn_string="#f6c177",
    syn_comment="#6e6a86",
    syn_function="#9ccfd8",
    syn_class="#ebbcba",
    syn_number="#ea9a97",
    syn_operator="#c4a7e7",
    syn_builtin="#9ccfd8",
)

# ── Registry ──────────────────────────────────────────────────────────────────

THEMES: dict[str, Theme] = {
    t.name: t
    for t in [DARK, LIGHT, NORD, SOLARIZED, DRACULA, GITHUB, MONOKAI, OCEAN, ROSE_PINE]
}

DEFAULT_THEME = "dark"


def get_theme(name: str | None = None) -> Theme:
    """Return a theme by name, falling back to the default."""
    return THEMES.get(name or DEFAULT_THEME, THEMES[DEFAULT_THEME])


def list_themes() -> list[dict[str, str]]:
    """Return list of {name, label} for all available themes."""
    return [{"name": t.name, "label": t.label} for t in THEMES.values()]
