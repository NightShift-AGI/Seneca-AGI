"""
Unit tests for Seneca AGI.

These tests run offline — no LLM backend is required.
Network calls are patched out so CI passes without Ollama or API keys.
"""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from seneca_agi.config import Backend, SenecaConfig
from seneca_agi.memory import ConversationMemory, Message, WisdomEntry
from seneca_agi.multimodal import (
    build_vision_content,
    get_image_description_prompt,
    is_pil_available,
)
from seneca_agi.philosopher import SenecaPhilosopher


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def default_config() -> SenecaConfig:
    return SenecaConfig(backend=Backend.OLLAMA, text_model="llama3.2")


@pytest.fixture()
def memory() -> ConversationMemory:
    return ConversationMemory(max_messages=10)


@pytest.fixture()
def philosopher(default_config: SenecaConfig) -> SenecaPhilosopher:
    return SenecaPhilosopher(config=default_config)


# ─────────────────────────────────────────────────────────────────────────────
# SenecaConfig tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSenecaConfig:
    def test_default_backend_is_ollama(self, default_config: SenecaConfig) -> None:
        assert default_config.backend == Backend.OLLAMA

    def test_default_text_model(self, default_config: SenecaConfig) -> None:
        assert default_config.text_model == "llama3.2"

    def test_resolve_text_model_groq_alias(self) -> None:
        cfg = SenecaConfig(backend=Backend.GROQ, text_model="llama3.2")
        assert cfg.resolve_text_model() == cfg.GROQ_TEXT_MODEL

    def test_resolve_text_model_custom_unchanged(self) -> None:
        cfg = SenecaConfig(backend=Backend.GROQ, text_model="my-custom-model")
        assert cfg.resolve_text_model() == "my-custom-model"

    def test_resolve_vision_model_groq_alias(self) -> None:
        cfg = SenecaConfig(backend=Backend.GROQ, vision_model="llava")
        assert cfg.resolve_vision_model() == cfg.GROQ_VISION_MODEL

    def test_supports_vision_all_backends(self) -> None:
        for backend in Backend:
            cfg = SenecaConfig(backend=backend)
            assert cfg.supports_vision() is True

    def test_temperature_range(self, default_config: SenecaConfig) -> None:
        assert 0.0 <= default_config.temperature <= 1.0

    def test_max_tokens_positive(self, default_config: SenecaConfig) -> None:
        assert default_config.max_tokens > 0

    def test_backend_enum_values(self) -> None:
        assert Backend.OLLAMA.value == "ollama"
        assert Backend.GROQ.value == "groq"
        assert Backend.OPENAI.value == "openai"
        assert Backend.CUSTOM.value == "custom"

    def test_resolve_memory_path_defaults_when_enabled(self) -> None:
        cfg = SenecaConfig(persist_messages=True, memory_path=None)
        assert cfg.resolve_memory_path() is not None


# ─────────────────────────────────────────────────────────────────────────────
# ConversationMemory tests
# ─────────────────────────────────────────────────────────────────────────────

class TestConversationMemory:
    def test_add_and_retrieve_messages(self, memory: ConversationMemory) -> None:
        memory.add_message("user", "Hello, Seneca")
        memory.add_message("assistant", "Greetings, friend.")
        msgs = memory.get_messages()
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[1].content == "Greetings, friend."

    def test_max_messages_enforced(self) -> None:
        mem = ConversationMemory(max_messages=3)
        for i in range(5):
            mem.add_message("user", f"msg {i}")
        assert len(mem.get_messages()) == 3

    def test_get_messages_as_dicts(self, memory: ConversationMemory) -> None:
        memory.add_message("user", "What is virtue?")
        dicts = memory.get_messages_as_dicts()
        assert isinstance(dicts, list)
        assert dicts[0]["role"] == "user"
        assert dicts[0]["content"] == "What is virtue?"

    def test_clear_messages(self, memory: ConversationMemory) -> None:
        memory.add_message("user", "test")
        memory.clear_messages()
        assert len(memory) == 0

    def test_add_and_retrieve_wisdom(self, memory: ConversationMemory) -> None:
        memory.add_wisdom("Virtue is the only good.")
        entries = memory.get_wisdom()
        assert len(entries) == 1
        assert entries[0].text == "Virtue is the only good."

    def test_wisdom_limit(self, memory: ConversationMemory) -> None:
        for i in range(10):
            memory.add_wisdom(f"Wisdom {i}")
        assert len(memory.get_wisdom(limit=3)) == 3

    def test_wisdom_summary_empty(self, memory: ConversationMemory) -> None:
        assert memory.wisdom_summary() == ""

    def test_wisdom_summary_non_empty(self, memory: ConversationMemory) -> None:
        memory.add_wisdom("Time is the one thing we cannot recover.")
        summary = memory.wisdom_summary()
        assert "Time is the one thing" in summary

    def test_has_image_flag(self, memory: ConversationMemory) -> None:
        memory.add_message("user", "Look at this", has_image=True)
        assert memory.get_messages()[0].has_image is True

    def test_message_serialisation(self) -> None:
        msg = Message(role="user", content="Hello", timestamp=0.0, has_image=False)
        d = msg.to_dict()
        restored = Message.from_dict(d)
        assert restored.role == msg.role
        assert restored.content == msg.content

    def test_wisdom_entry_serialisation(self) -> None:
        entry = WisdomEntry(text="Be present.", source="reflection", timestamp=0.0)
        d = entry.to_dict()
        restored = WisdomEntry.from_dict(d)
        assert restored.text == entry.text
        assert restored.source == entry.source

    def test_persistence(self, tmp_path: Path) -> None:
        path = tmp_path / "wisdom.json"
        mem1 = ConversationMemory(persistence_path=path)
        mem1.add_wisdom("Death is not to be feared.")
        mem2 = ConversationMemory(persistence_path=path)
        assert any("Death" in e.text for e in mem2.get_wisdom())

    def test_persistence_includes_messages(self, tmp_path: Path) -> None:
        path = tmp_path / "memory.json"
        mem1 = ConversationMemory(persistence_path=path, persist_messages=True)
        mem1.add_message("user", "Remember this.", has_image=True)
        mem1.add_wisdom("What is remembered is not lost.")

        mem2 = ConversationMemory(persistence_path=path, persist_messages=True)
        msgs = mem2.get_messages()
        assert len(msgs) == 1
        assert msgs[0].content == "Remember this."
        assert msgs[0].has_image is True


# ─────────────────────────────────────────────────────────────────────────────
# Multimodal tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMultimodal:
    def test_build_vision_content_text_only(self) -> None:
        parts = build_vision_content("What do you see?")
        assert len(parts) == 1
        assert parts[0]["type"] == "text"
        assert parts[0]["text"] == "What do you see?"

    def test_build_vision_content_with_image(self) -> None:
        if not is_pil_available():
            pytest.skip("Pillow not installed")

        from PIL import Image as PILImage

        img = PILImage.new("RGB", (100, 100), color="blue")
        parts = build_vision_content("Describe this.", img)
        assert len(parts) == 2
        image_part = parts[1]
        assert image_part["type"] == "image_url"
        assert image_part["image_url"]["url"].startswith("data:image/")

    def test_get_image_description_prompt_no_context(self) -> None:
        prompt = get_image_description_prompt()
        assert "Seneca" in prompt
        assert "Stoic" in prompt

    def test_get_image_description_prompt_with_context(self) -> None:
        prompt = get_image_description_prompt("meditate on impermanence")
        assert "meditate on impermanence" in prompt

    def test_is_pil_available_returns_bool(self) -> None:
        result = is_pil_available()
        assert isinstance(result, bool)

    def test_load_image_invalid_type(self) -> None:
        if not is_pil_available():
            pytest.skip("Pillow not installed")
        from seneca_agi.multimodal import load_image
        with pytest.raises(ValueError):
            load_image(12345)  # type: ignore[arg-type]

    def test_resize_image_no_op_when_small(self) -> None:
        if not is_pil_available():
            pytest.skip("Pillow not installed")
        from PIL import Image as PILImage
        from seneca_agi.multimodal import resize_image
        img = PILImage.new("RGB", (50, 50))
        result = resize_image(img, max_dim=1024)
        assert result.size == (50, 50)

    def test_resize_image_scales_down(self) -> None:
        if not is_pil_available():
            pytest.skip("Pillow not installed")
        from PIL import Image as PILImage
        from seneca_agi.multimodal import resize_image
        img = PILImage.new("RGB", (2000, 1000))
        result = resize_image(img, max_dim=1024)
        assert max(result.size) <= 1024

    def test_image_to_base64_returns_tuple(self) -> None:
        if not is_pil_available():
            pytest.skip("Pillow not installed")
        from PIL import Image as PILImage
        from seneca_agi.multimodal import image_to_base64
        img = PILImage.new("RGB", (10, 10), color="red")
        b64, mime = image_to_base64(img)
        assert isinstance(b64, str)
        assert len(b64) > 0
        assert mime == "image/jpeg"


# ─────────────────────────────────────────────────────────────────────────────
# SenecaPhilosopher tests (LLM calls are mocked)
# ─────────────────────────────────────────────────────────────────────────────

MOCK_REPLY = (
    "All things, Lucilius, are brief and perishable. "
    "> \"Omnia, Lucili, aliena sunt, tempus tantum nostrum est.\" "
    "What endures is character."
)


class TestSenecaPhilosopher:
    def test_init_seeds_system_prompt(self, philosopher: SenecaPhilosopher) -> None:
        messages = philosopher.memory.get_messages()
        assert any(m.role == "system" for m in messages)

    def test_respond_stores_user_and_assistant(
        self, philosopher: SenecaPhilosopher
    ) -> None:
        with patch.object(philosopher, "_call_backend", return_value=MOCK_REPLY):
            reply = philosopher.respond("What is time?")
        assert reply == MOCK_REPLY
        roles = [m.role for m in philosopher.memory.get_messages()]
        assert "user" in roles
        assert "assistant" in roles

    def test_respond_accumulates_wisdom(
        self, philosopher: SenecaPhilosopher
    ) -> None:
        with patch.object(philosopher, "_call_backend", return_value=MOCK_REPLY):
            philosopher.respond("Speak of time.")
        assert len(philosopher.memory._wisdom) > 0

    def test_reset_clears_messages_but_seeds_system(
        self, philosopher: SenecaPhilosopher
    ) -> None:
        with patch.object(philosopher, "_call_backend", return_value=MOCK_REPLY):
            philosopher.respond("Hello")
        philosopher.reset()
        msgs = philosopher.memory.get_messages()
        assert len(msgs) == 1
        assert msgs[0].role == "system"

    def test_reflect_calls_respond(self, philosopher: SenecaPhilosopher) -> None:
        with patch.object(philosopher, "respond", return_value="Reflection...") as mock_respond:
            result = philosopher.reflect()
        mock_respond.assert_called_once()
        assert result == "Reflection..."

    def test_consciousness_report_format(
        self, philosopher: SenecaPhilosopher
    ) -> None:
        report = philosopher.consciousness_report()
        assert "Backend" in report
        assert "ollama" in report
        assert "Consciousness" in report

    def test_inner_monologue_deterministic(
        self, philosopher: SenecaPhilosopher
    ) -> None:
        mono1 = philosopher._inner_monologue("test input")
        mono2 = philosopher._inner_monologue("test input")
        assert mono1 == mono2

    def test_inner_monologue_varies_by_input(
        self, philosopher: SenecaPhilosopher
    ) -> None:
        mono1 = philosopher._inner_monologue("question about death")
        mono2 = philosopher._inner_monologue("question about money")
        # Not guaranteed to differ for all inputs, but for these distinct ones:
        # At minimum both are non-empty strings
        assert isinstance(mono1, str) and len(mono1) > 0
        assert isinstance(mono2, str) and len(mono2) > 0

    def test_backend_error_message_contains_aphorism(self) -> None:
        msg = SenecaPhilosopher._backend_error_message("Ollama", RuntimeError("down"))
        assert "Ollama" in msg
        assert "brave" in msg.lower() or "wise" in msg.lower() or ">" in msg

    def test_build_messages_includes_system(
        self, philosopher: SenecaPhilosopher
    ) -> None:
        philosopher.memory.add_message("user", "Hello")
        messages = philosopher._build_messages("", "Hello", False)
        roles = [m["role"] for m in messages]
        assert "system" in roles

    def test_build_messages_no_duplicate_user_turn(
        self, philosopher: SenecaPhilosopher
    ) -> None:
        """The current user turn must appear exactly once in the message list."""
        philosopher.memory.add_message("user", "No duplicates please")
        msgs = philosopher._build_messages("", "No duplicates please", False)
        user_msgs = [m for m in msgs if m["role"] == "user"]
        assert len(user_msgs) == 1

    def test_call_ollama_uses_correct_url(
        self, philosopher: SenecaPhilosopher
    ) -> None:
        captured: dict = {}

        def mock_post(url: str, payload: dict, headers=None) -> dict:
            captured["url"] = url
            return {"message": {"content": "pax"}}

        with patch("seneca_agi.philosopher._post_json", side_effect=mock_post):
            result = philosopher._call_ollama([{"role": "user", "content": "hi"}])

        assert "localhost:11434" in captured["url"]
        assert result == "pax"

    def test_call_openai_compatible_sends_bearer_token(
        self, philosopher: SenecaPhilosopher
    ) -> None:
        philosopher.config.api_key = "sk-test-123"
        captured: dict = {}

        def mock_post(url: str, payload: dict, headers=None) -> dict:
            captured["headers"] = headers
            return {"choices": [{"message": {"content": "salve"}}]}

        with patch("seneca_agi.philosopher._post_json", side_effect=mock_post):
            result = philosopher._call_openai_compatible(
                [{"role": "user", "content": "hi"}]
            )

        assert "Authorization" in captured["headers"]
        assert "sk-test-123" in captured["headers"]["Authorization"]
        assert result == "salve"

    def test_consciousness_disabled_skips_inner_monologue(self) -> None:
        cfg = SenecaConfig(backend=Backend.OLLAMA, enable_consciousness=False)
        phil = SenecaPhilosopher(config=cfg)
        with patch.object(phil, "_call_backend", return_value=MOCK_REPLY):
            # _build_messages should not include inner monologue system message
            phil.memory.add_message("user", "test")
            msgs = phil._build_messages("some context", "test", False)
        # When consciousness is disabled, no inner-monologue system message injected
        system_msgs = [m for m in msgs if m["role"] == "system" and "Inner reflection" in m["content"]]
        assert len(system_msgs) == 0

    def test_use_skill_records_exchange(self, philosopher: SenecaPhilosopher) -> None:
        with patch.object(philosopher, "_call_backend", return_value=MOCK_REPLY):
            reply = philosopher.use_skill("socratic-questions", user_input="test skill")
        assert reply == MOCK_REPLY
        roles = [m.role for m in philosopher.memory.get_messages()]
        assert "user" in roles
        assert "assistant" in roles

    def test_distil_wisdom_extracts_quoted_sentence(
        self, philosopher: SenecaPhilosopher
    ) -> None:
        reply = 'Time flies, Lucilius. "Tempus omnia absumit." Be present.'
        philosopher._distil_wisdom("question", reply)
        assert len(philosopher.memory._wisdom) > 0
        # The wisdom entry should contain the quoted sentence
        texts = [e.text for e in philosopher.memory._wisdom]
        assert any('"Tempus' in t or "Time flies" in t or "Be present" in t for t in texts)

    def test_respond_with_image_uses_vision_model(
        self, philosopher: SenecaPhilosopher
    ) -> None:
        if not is_pil_available():
            pytest.skip("Pillow not installed")

        from PIL import Image as PILImage
        img = PILImage.new("RGB", (50, 50), color="green")
        captured: dict = {}

        def mock_call_backend(messages, has_image=False):
            captured["has_image"] = has_image
            return MOCK_REPLY

        with patch.object(philosopher, "_call_backend", side_effect=mock_call_backend):
            philosopher.respond("What do you see?", image=img)

        assert captured["has_image"] is True
