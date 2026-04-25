"""
StudyCraft -- TTS Engine abstractions.

Supports multiple TTS engines via dependency injection:
  - ChatterboxTTS (MIT, multilingual, voice cloning)
  - KittenTTS (Apache 2.0, lightweight, CPU-only)
  - CoquiTTS (MPL 2.0, 1100+ languages, XTTS-v2)
  - OpenRouterTTS (cloud-based, free models only)
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path

from rich.console import Console

console = Console()


# ── Base Class ──────────────────────────────────────────────────────────────────


class TTSEngine(ABC):
    """Abstract base class for all TTS engines."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: str | Path,
        voice: str | None = None,
        speed: float = 1.0,
        **kwargs,
    ) -> Path:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize.
            output_path: Path to save the audio file.
            voice: Voice/speaker name or ID (engine-specific).
            speed: Playback speed multiplier.

        Returns:
            Path to the generated audio file.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the engine is properly installed and available."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable engine name."""
        ...

    @property
    @abstractmethod
    def supports_voice_cloning(self) -> bool:
        """Return True if engine supports voice cloning from audio samples."""
        ...

    @property
    @abstractmethod
    def supported_languages(self) -> list[str]:
        """Return list of supported language codes."""
        ...


# ── Chatterbox TTS ───────────────────────────────────────────────────────────


class ChatterboxTTSEngine(TTSEngine):
    """
    Chatterbox TTS engine (Resemble AI).

    Models: Chatterbox-Turbo (350M), Chatterbox-Multilingual (500M), Chatterbox (500M)
    License: MIT
    Languages: English (Turbo), 23+ (Multilingual)
    """

    def __init__(self, model_type: str = "turbo", device: str | None = None):
        """
        Initialize Chatterbox TTS engine.

        Args:
            model_type: 'turbo' (350M, English), 'multilingual' (500M, 23+ langs),
                        or 'standard' (500M, English with CFG tuning)
            device: Torch device (None for auto-detect)
        """
        self._model_type = model_type
        self._device = device
        self._tts = None
        self._available = self._check_available()

    def _check_available(self) -> bool:
        try:
            import chatterbox  # noqa: F401
            import torch  # noqa: F401

            return True
        except ImportError:
            return False

    def _lazy_load(self):
        if self._tts is not None:
            return
        if not self._available:
            raise RuntimeError("Chatterbox TTS not installed. Install with: uv add chatterbox-tts")
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        from chatterbox.tts import ChatterboxTTS
        from chatterbox.tts_turbo import ChatterboxTurboTTS

        if self._model_type == "turbo":
            self._tts = ChatterboxTurboTTS(device=self._device)
        elif self._model_type == "multilingual":
            self._tts = ChatterboxMultilingualTTS(device=self._device)
        else:
            self._tts = ChatterboxTTS(device=self._device)

    def synthesize(
        self,
        text: str,
        output_path: str | Path,
        voice: str | None = None,
        speed: float = 1.0,
        **kwargs,
    ) -> Path:
        self._lazy_load()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        import torchaudio as ta

        # Chatterbox supports voice cloning via audio reference
        audio_prompt_path = kwargs.get("voice_sample_path")
        if audio_prompt_path and self.supports_voice_cloning:
            wav = self._tts.generate(
                text,
                audio_prompt_path=audio_prompt_path,
                exaggeration=kwargs.get("exaggeration", 0.5),
                cfg_weight=kwargs.get("cfg_weight", 0.5),
            )
        else:
            wav = self._tts.generate(text)

        ta.save(str(output_path), wav, self._tts.sr)
        return output_path

    def is_available(self) -> bool:
        return self._available

    @property
    def name(self) -> str:
        return f"Chatterbox-TTS ({self._model_type})"

    @property
    def supports_voice_cloning(self) -> bool:
        return True

    @property
    def supported_languages(self) -> list[str]:
        if self._model_type == "multilingual":
            return [
                "en",
                "es",
                "fr",
                "de",
                "it",
                "pt",
                "pl",
                "zh",
                "ja",
                "ko",
                "ar",
                "ru",
                "hi",
                "tr",
                "nl",
                "sv",
                "da",
                "no",
                "fi",
                "cs",
                "ro",
                "hu",
                "bg",
            ]
        return ["en"]


# ── Kitten TTS ────────────────────────────────────────────────────────────────


class KittenTTSEngine(TTSEngine):
    """
    Kitten TTS engine (KittenML).

    Models: nano (15M), micro (40M), mini (80M)
    License: Apache 2.0
    Languages: English (built-in voices: Bella, Jasper, Luna, Bruno, Rosie, Hugo, Kiki, Leo)
    """

    BUILTIN_VOICES = [
        "Bella",
        "Jasper",
        "Luna",
        "Bruno",
        "Rosie",
        "Hugo",
        "Kiki",
        "Leo",
    ]

    def __init__(self, model_size: str = "mini"):
        """
        Initialize Kitten TTS engine.

        Args:
            model_size: 'nano' (15M), 'micro' (40M), or 'mini' (80M)
        """
        self._model_size = model_size
        self._model = None
        self._available = self._check_available()

    def _check_available(self) -> bool:
        try:
            import kittentts  # noqa: F401

            return True
        except ImportError:
            return False

    def _lazy_load(self):
        if self._model is not None:
            return
        if not self._available:
            raise RuntimeError(
                "Kitten TTS not installed. Install from: "
                "https://github.com/KittenML/KittenTTS/releases"
            )
        from kittentts import KittenTTS

        model_map = {
            "nano": "KittenML/kitten-tts-nano-0.8",
            "micro": "KittenML/kitten-tts-micro-0.8",
            "mini": "KittenML/kitten-tts-mini-0.8",
        }
        model_name = model_map.get(self._model_size, model_map["mini"])
        self._model = KittenTTS(model_name)

    def synthesize(
        self,
        text: str,
        output_path: str | Path,
        voice: str | None = None,
        speed: float = 1.0,
        **kwargs,
    ) -> Path:
        self._lazy_load()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        voice = voice or "Bella"
        if voice not in self.BUILTIN_VOICES:
            console.print(f"[yellow]Unknown voice '{voice}', using Bella[/yellow]")
            voice = "Bella"

        audio = self._model.generate(text, voice=voice, speed=speed)
        self._model.save(audio, str(output_path))
        return output_path

    def is_available(self) -> bool:
        return self._available

    @property
    def name(self) -> str:
        return f"Kitten-TTS ({self._model_size})"

    @property
    def supports_voice_cloning(self) -> bool:
        return False

    @property
    def supported_languages(self) -> list[str]:
        return ["en"]


# ── Coqui TTS / XTTS-v2 ─────────────────────────────────────────────────────


class CoquiTTSEngine(TTSEngine):
    """
    Coqui TTS engine with XTTS-v2 support.

    Models: XTTS-v2 (1.7B), supports 1100+ languages
    License: MPL 2.0
    Features: Zero-shot voice cloning from 6-second audio samples
    """

    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        """
        Initialize Coqui TTS engine.

        Args:
            model_name: TTS model name (default: xtts_v2)
        """
        self._model_name = model_name
        self._tts = None
        self._available = self._check_available()

    def _check_available(self) -> bool:
        try:
            import TTS  # noqa: F401

            return True
        except ImportError:
            return False

    def _lazy_load(self):
        if self._tts is not None:
            return
        if not self._available:
            raise RuntimeError("Coqui TTS not installed. Install with: uv add coqui-tts")
        from TTS.api import TTS as TTSAPI

        self._tts = TTSAPI(model_name=self._model_name, progress_bar=False)

    def synthesize(
        self,
        text: str,
        output_path: str | Path,
        voice: str | None = None,
        speed: float = 1.0,
        **kwargs,
    ) -> Path:
        self._lazy_load()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # XTTS-v2 supports voice cloning via speaker_wav
        speaker_wav = kwargs.get("voice_sample_path")

        self._tts.tts_to_file(
            text=text,
            file_path=str(output_path),
            speaker=speaker_wav or voice,
            language=kwargs.get("language", "en"),
            speed=speed,
        )
        return output_path

    def is_available(self) -> bool:
        return self._available

    @property
    def name(self) -> str:
        return f"Coqui-TTS ({self._model_name.split('/')[-1]})"

    @property
    def supports_voice_cloning(self) -> bool:
        return True

    @property
    def supported_languages(self) -> list[str]:
        return [
            "en",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "pl",
            "tr",
            "ru",
            "nl",
            "cs",
            "ar",
            "zh",
            "ja",
            "ko",
            "hi",
            "hu",
            "uk",
            "vi",
            "sv",
            "no",
            "fi",
            "da",
        ]


# ── OpenRouter TTS (Cloud, Free Models Only) ─────────────────────────────────


class OpenRouterTTSEngine(TTSEngine):
    """
    OpenRouter TTS via chat completions API with audio output.

    Uses models that support audio output modality.
    ONLY uses free models (checks model_registry for pricing).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "openrouter/free",
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """
        Initialize OpenRouter TTS engine.

        Args:
            api_key: OpenRouter API key (or set OPENROUTER_API_KEY env var)
            model: Model ID (must be free)
            base_url: OpenRouter API base URL
        """
        self._api_key = (
            api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("STUDYCRAFT_API_KEY")
        )
        self._model = model
        self._base_url = base_url
        self._available = bool(self._api_key)

    def _check_free_model(self) -> bool:
        """Verify the configured model is free."""
        try:
            from .model_registry import get_free_models, get_model

            model_info = get_model(self._model)
            if model_info:
                return model_info.get("is_free", False)
            free_models = get_free_models()
            return any(m["id"] == self._model for m in free_models)
        except Exception:
            return False

    def synthesize(
        self,
        text: str,
        output_path: str | Path,
        voice: str | None = None,
        speed: float = 1.0,
        **kwargs,
    ) -> Path:
        if not self._available:
            raise RuntimeError("OpenRouter API key not configured.")

        if not self._check_free_model():
            raise RuntimeError(
                f"Model '{self._model}' is not free. OpenRouter TTS only supports free models."
            )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        from openai import OpenAI

        client = OpenAI(base_url=self._base_url, api_key=self._api_key)

        response = client.chat.completions.create(
            model=self._model,
            modalities=["text", "audio"],
            audio={"voice": voice or "alloy", "format": "mp3"},
            messages=[{"role": "user", "content": f"Read the following text aloud: {text}"}],
            stream=True,
        )

        audio_bytes = b""
        for chunk in response:
            if hasattr(chunk, "choices") and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, "audio") and delta.audio:
                    audio_bytes += (
                        delta.audio.encode() if isinstance(delta.audio, str) else delta.audio
                    )

        output_path.write_bytes(audio_bytes)
        return output_path

    def is_available(self) -> bool:
        return self._available and self._check_free_model()

    @property
    def name(self) -> str:
        return f"OpenRouter-TTS ({self._model})"

    @property
    def supports_voice_cloning(self) -> bool:
        return False

    @property
    def supported_languages(self) -> list[str]:
        return ["en"]


# ── Engine Registry ───────────────────────────────────────────────────────────

_ENGINE_REGISTRY: dict[str, type[TTSEngine]] = {
    "chatterbox": ChatterboxTTSEngine,
    "kitten": KittenTTSEngine,
    "coqui": CoquiTTSEngine,
    "openrouter": OpenRouterTTSEngine,
}


def get_engine(name: str, **kwargs) -> TTSEngine:
    """
    Factory function to get a TTS engine by name.

    Args:
        name: Engine name ('chatterbox', 'kitten', 'coqui', 'openrouter')
        **kwargs: Engine-specific initialization arguments

    Returns:
        TTSEngine instance

    Raises:
        ValueError: If engine name is not recognized
    """
    name = name.lower()
    if name not in _ENGINE_REGISTRY:
        available = ", ".join(_ENGINE_REGISTRY.keys())
        raise ValueError(f"Unknown TTS engine '{name}'. Available: {available}")

    engine_class = _ENGINE_REGISTRY[name]
    return engine_class(**kwargs)


def list_available_engines() -> list[str]:
    """Return list of installed and available engine names."""
    available = []
    for name, engine_class in _ENGINE_REGISTRY.items():
        try:
            instance = engine_class()
            if instance.is_available():
                available.append(name)
        except Exception:
            pass
    return available


def get_fallback_chain() -> list[tuple[str, dict]]:
    """
    Return ordered list of (engine_name, kwargs) for fallback.

    Priority: Kitten (lightweight) -> Chatterbox (quality) -> Coqui (multilingual) -> OpenRouter (cloud, free only)
    """
    return [
        ("kitten", {"model_size": "mini"}),
        ("chatterbox", {"model_type": "turbo"}),
        ("coqui", {"model_name": "tts_models/multilingual/multi-dataset/xtts_v2"}),
        ("openrouter", {"model": "openrouter/free"}),
    ]
