"""
Configuration for Seneca AGI — supports free/local and cloud LLM backends.

Priority order for free accessibility:
  1. Ollama  (local, completely free — default)
  2. Groq    (free cloud tier, fastest inference)
  3. OpenAI  (paid, but widely used)
  4. Custom  (any OpenAI-compatible endpoint)
"""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Backend(str, Enum):
    """Supported LLM backends."""

    OLLAMA = "ollama"
    GROQ = "groq"
    OPENAI = "openai"
    CUSTOM = "custom"


@dataclass
class SenecaConfig:
    """Runtime configuration for Seneca AGI."""

    # ------------------------------------------------------------------ backend
    backend: Backend = field(
        default_factory=lambda: Backend(
            os.getenv("SENECA_BACKEND", Backend.OLLAMA.value)
        )
    )

    # ------------------------------------------------------------ model names
    # Text generation model
    text_model: str = field(
        default_factory=lambda: os.getenv(
            "SENECA_TEXT_MODEL", "llama3.2"
        )
    )
    # Vision / multimodal model (image + text)
    vision_model: str = field(
        default_factory=lambda: os.getenv(
            "SENECA_VISION_MODEL", "llava"
        )
    )

    # ------------------------------------------------------- connection params
    # Ollama base URL (local by default)
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
    )
    # Cloud API key (Groq / OpenAI / custom)
    api_key: Optional[str] = field(
        default_factory=lambda: (
            os.getenv("GROQ_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("SENECA_API_KEY")
        )
    )
    # Base URL for OpenAI-compatible cloud endpoints
    api_base_url: str = field(
        default_factory=lambda: os.getenv(
            "SENECA_API_BASE_URL",
            "https://api.groq.com/openai/v1",
        )
    )

    # ------------------------------------------------------ generation params
    temperature: float = float(os.getenv("SENECA_TEMPERATURE", "0.75"))
    max_tokens: int = int(os.getenv("SENECA_MAX_TOKENS", "1024"))
    # Number of past messages kept in context
    context_window: int = int(os.getenv("SENECA_CONTEXT_WINDOW", "20"))

    # ------------------------------------------------------ memory persistence
    memory_path: Optional[str] = field(
        default_factory=lambda: os.getenv("SENECA_MEMORY_PATH")
    )
    persist_messages: bool = (
        os.getenv("SENECA_PERSIST_MESSAGES", "false").lower() == "true"
    )

    # ------------------------------------------------------- consciousness
    # Whether to run the inner-monologue / self-reflection loop
    enable_consciousness: bool = (
        os.getenv("SENECA_CONSCIOUSNESS", "true").lower() == "true"
    )
    # Maximum depth of Socratic self-questioning per response
    reflection_depth: int = int(
        os.getenv("SENECA_REFLECTION_DEPTH", "2")
    )

    # ------------------------------------------------------------------ meta
    debug: bool = os.getenv("SENECA_DEBUG", "false").lower() == "true"

    # ------------------------------------------- model aliases for Groq free
    GROQ_TEXT_MODEL: str = "llama3-8b-8192"
    GROQ_VISION_MODEL: str = "llava-v1.5-7b-4096-preview"

    def resolve_text_model(self) -> str:
        """Return the correct text model name for the active backend."""
        if self.backend == Backend.GROQ and self.text_model == "llama3.2":
            return self.GROQ_TEXT_MODEL
        return self.text_model

    def resolve_vision_model(self) -> str:
        """Return the correct vision model name for the active backend."""
        if self.backend == Backend.GROQ and self.vision_model == "llava":
            return self.GROQ_VISION_MODEL
        return self.vision_model

    def supports_vision(self) -> bool:
        """Return True when the current backend can process images."""
        return self.backend in (Backend.OLLAMA, Backend.GROQ, Backend.OPENAI, Backend.CUSTOM)

    def resolve_memory_path(self) -> Optional[Path]:
        """Return the configured memory path, falling back to a default when enabled."""
        if self.memory_path:
            return Path(self.memory_path)
        if self.persist_messages:
            return Path.home() / ".seneca_agi" / "memory.json"
        return None
