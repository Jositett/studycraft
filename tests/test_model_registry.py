"""Tests for studycraft.model_registry."""

from studycraft.model_registry import _normalize


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


def test_normalize_extracts_fields():
    models = _normalize(_SAMPLE_API_DATA)
    assert len(models) == 3
    assert models[0]["id"] == "meta-llama/llama-3.3-70b-instruct:free"
    assert models[0]["context_length"] == 131072


def test_normalize_detects_free():
    models = _normalize(_SAMPLE_API_DATA)
    assert models[0]["is_free"] is True
    assert models[1]["is_free"] is False
    assert models[2]["is_free"] is True


def test_normalize_detects_vision():
    models = _normalize(_SAMPLE_API_DATA)
    assert models[0]["has_vision"] is False  # text only
    assert models[1]["has_vision"] is True   # image in input_modalities
    assert models[2]["has_vision"] is True   # image in input_modalities


def test_normalize_pricing():
    models = _normalize(_SAMPLE_API_DATA)
    assert models[0]["prompt_price"] == 0.0
    assert models[1]["prompt_price"] == 0.0025
    assert models[1]["completion_price"] == 0.01


def test_free_vision_filter():
    models = _normalize(_SAMPLE_API_DATA)
    free_vision = [m for m in models if m["is_free"] and m["has_vision"]]
    assert len(free_vision) == 1
    assert free_vision[0]["id"] == "google/gemini-2.0-flash-001"
