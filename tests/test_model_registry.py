"""Tests for studycraft.model_registry."""

from unittest.mock import patch

from studycraft.model_registry import (
    _normalize,
    get_free_models,
    get_vision_models,
    get_model,
    search_models,
)


_SAMPLE_API_DATA = [
    {
        "id": "meta-llama/llama-3.3-70b-instruct:free",
        "name": "Llama 3.3 70B Instruct (free)",
        "context_length": 131072,
        "pricing": {"prompt": "0", "completion": "0"},
        "architecture": {"modality": "text->text", "input_modalities": ["text"]},
        "description": "A free Llama model.",
    },
    {
        "id": "openai/gpt-4o",
        "name": "GPT-4o",
        "context_length": 128000,
        "pricing": {"prompt": "0.0025", "completion": "0.01"},
        "architecture": {"modality": "text+image->text", "input_modalities": ["text", "image"]},
        "description": "OpenAI GPT-4o with vision.",
    },
    {
        "id": "google/gemini-2.0-flash-001",
        "name": "Gemini 2.0 Flash",
        "context_length": 1048576,
        "pricing": {"prompt": "0", "completion": "0"},
        "architecture": {"modality": "text+image->text", "input_modalities": ["text", "image"]},
        "description": "Free Gemini with vision.",
    },
]

_NORMALIZED = _normalize(_SAMPLE_API_DATA)


def _mock_fetch(force=False):
    return _NORMALIZED


# ── _normalize tests ──────────────────────────────────────────────────────────


def test_normalize_extracts_fields():
    models = _normalize(_SAMPLE_API_DATA)
    assert len(models) == 3
    assert models[0]["id"] == "meta-llama/llama-3.3-70b-instruct:free"
    assert models[0]["context_length"] == 131072
    assert models[0]["name"] == "Llama 3.3 70B Instruct (free)"


def test_normalize_detects_free():
    models = _normalize(_SAMPLE_API_DATA)
    assert models[0]["is_free"] is True
    assert models[1]["is_free"] is False
    assert models[2]["is_free"] is True


def test_normalize_detects_vision():
    models = _normalize(_SAMPLE_API_DATA)
    assert models[0]["has_vision"] is False
    assert models[1]["has_vision"] is True
    assert models[2]["has_vision"] is True


def test_normalize_pricing():
    models = _normalize(_SAMPLE_API_DATA)
    assert models[0]["prompt_price"] == 0.0
    assert models[1]["prompt_price"] == 0.0025
    assert models[1]["completion_price"] == 0.01


def test_normalize_handles_missing_pricing():
    data = [{"id": "test/model", "pricing": {}}]
    models = _normalize(data)
    assert models[0]["is_free"] is True
    assert models[0]["prompt_price"] == 0.0


# ── Filter/query helper tests ────────────────────────────────────────────────


@patch("studycraft.model_registry.fetch_models", side_effect=_mock_fetch)
def test_get_free_models(mock):
    result = get_free_models()
    assert len(result) == 2
    assert all(m["is_free"] for m in result)
    # Should be sorted by context_length descending
    assert result[0]["context_length"] >= result[1]["context_length"]


@patch("studycraft.model_registry.fetch_models", side_effect=_mock_fetch)
def test_get_free_models_vision_only(mock):
    result = get_free_models(vision_only=True)
    assert len(result) == 1
    assert result[0]["id"] == "google/gemini-2.0-flash-001"
    assert result[0]["is_free"] is True
    assert result[0]["has_vision"] is True


@patch("studycraft.model_registry.fetch_models", side_effect=_mock_fetch)
def test_get_vision_models(mock):
    result = get_vision_models()
    assert len(result) == 2
    assert all(m["has_vision"] for m in result)


@patch("studycraft.model_registry.fetch_models", side_effect=_mock_fetch)
def test_get_vision_models_free_only(mock):
    result = get_vision_models(free_only=True)
    assert len(result) == 1
    assert result[0]["is_free"] is True


@patch("studycraft.model_registry.fetch_models", side_effect=_mock_fetch)
def test_get_model_found(mock):
    result = get_model("openai/gpt-4o")
    assert result is not None
    assert result["id"] == "openai/gpt-4o"


@patch("studycraft.model_registry.fetch_models", side_effect=_mock_fetch)
def test_get_model_not_found(mock):
    result = get_model("nonexistent/model")
    assert result is None


@patch("studycraft.model_registry.fetch_models", side_effect=_mock_fetch)
def test_search_models_by_id(mock):
    result = search_models("llama")
    assert len(result) == 1
    assert "llama" in result[0]["id"]


@patch("studycraft.model_registry.fetch_models", side_effect=_mock_fetch)
def test_search_models_by_name(mock):
    result = search_models("Gemini")
    assert len(result) == 1
    assert "Gemini" in result[0]["name"]


@patch("studycraft.model_registry.fetch_models", side_effect=_mock_fetch)
def test_search_models_no_match(mock):
    result = search_models("nonexistent_xyz")
    assert result == []
