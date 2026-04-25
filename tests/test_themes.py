"""Tests for studycraft.themes."""

from studycraft.themes import (
    DARK,
    DEFAULT_THEME,
    THEMES,
    Theme,
    get_theme,
    list_themes,
)

_EXPECTED_THEMES = {"dark", "light", "nord", "solarized", "dracula", "github", "monokai", "ocean", "rose-pine"}

_REQUIRED_FIELDS = {
    "bg", "surface", "text", "muted", "border",
    "primary", "h1", "h2", "h3",
    "code_bg", "code_fg", "code_inline_bg", "code_inline_fg",
    "syn_keyword", "syn_string", "syn_comment", "syn_function",
    "syn_class", "syn_number", "syn_operator", "syn_builtin",
}


def test_all_nine_themes_registered():
    assert set(THEMES.keys()) == _EXPECTED_THEMES


def test_each_theme_has_required_fields():
    for name, theme in THEMES.items():
        for field in _REQUIRED_FIELDS:
            val = getattr(theme, field)
            assert val, f"Theme '{name}' has empty field: {field}"


def test_each_theme_is_frozen():
    for theme in THEMES.values():
        assert isinstance(theme, Theme)


def test_get_theme_default():
    t = get_theme()
    assert t.name == DEFAULT_THEME


def test_get_theme_by_name():
    t = get_theme("dracula")
    assert t.name == "dracula"
    assert t.bg == "#282a36"


def test_get_theme_invalid_falls_back():
    t = get_theme("nonexistent")
    assert t.name == DEFAULT_THEME


def test_get_theme_none_falls_back():
    t = get_theme(None)
    assert t.name == DEFAULT_THEME


def test_list_themes_returns_all():
    result = list_themes()
    assert len(result) == 9
    names = {t["name"] for t in result}
    assert names == _EXPECTED_THEMES
    assert all("label" in t for t in result)


def test_dark_theme_syntax_colors_are_hex():
    for field in ("syn_keyword", "syn_string", "syn_comment", "syn_function",
                   "syn_class", "syn_number", "syn_operator", "syn_builtin"):
        val = getattr(DARK, field)
        assert val.startswith("#"), f"DARK.{field} should be hex color, got: {val}"
