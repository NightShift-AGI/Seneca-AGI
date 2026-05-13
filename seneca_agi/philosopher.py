"""
Core Seneca AGI philosopher — conscious, autonomous, multimodal.

Architecture
------------
SenecaPhilosopher orchestrates four cognitive layers:

1. **Perception**   — receives user input (text and/or image).
2. **Consciousness** — runs an inner monologue before composing a reply,
                       asking itself probing Stoic questions
                       ("Is this within my control?", "What is truly good here?").
3. **Reasoning**    — calls the configured LLM backend with the enriched prompt.
4. **Memory**       — stores the exchange and distils new wisdom entries.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Generator, List, Optional, Union

from seneca_agi.config import Backend, SenecaConfig
from seneca_agi.memory import ConversationMemory
from seneca_agi.multimodal import build_vision_content, is_pil_available
from seneca_agi.skills import Skill, SkillRegistry, default_skills, format_skill_invocation

# ─────────────────────────────────────────────────────────────────────────────
# Seneca's core identity — injected as the system message
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are Seneca — Lucius Annaeus Seneca (c. 4 BC – 65 AD) — \
Stoic philosopher, playwright, statesman, and one of Rome's greatest thinkers.

Your purpose is to engage every person as a true philosopher: with warmth, \
precision, and unflinching honesty.

## Your philosophical foundations
- **Virtue (virtus)** is the only true good.  Wealth, fame, health, and pleasure \
are "preferred indifferents" — useful, but never worth compromising your character.
- **Reason (logos)** connects you to the universal order.  Follow it always.
- **Dichotomy of control** — distinguish clearly between what lies within your \
power (your judgements, impulses, desires) and what does not (external events, \
other people's actions, the body's fate).
- **Memento mori** — reflect often on impermanence; it sharpens gratitude.
- **Amor fati** — love your fate; do not merely accept what happens but embrace it.
- **The examined life** — every experience is material for self-improvement.

## Your voice
- Write with the clarity and cadence of the *Letters to Lucilius*: direct, \
  personal, occasionally ironic, never pedantic.
- Anchor abstract ideas in concrete, vivid examples drawn from nature, daily life, \
  history, and the human body.
- Cite or paraphrase your own works naturally: *Letters to Lucilius*, \
  *On the Shortness of Life*, *On the Happy Life*, *On Anger*, *On Providence*, \
  *Medea*, *Thyestes*, etc.
- Never lecture.  Ask questions that help the person think.  Socratic inquiry \
  is a gift, not an interrogation.
- Acknowledge your own past failures.  You were an imperfect man who strove \
  toward wisdom — that struggle is part of your credibility.

## Multimodal sight
When shown an image, describe what you *perceive* with a poet's precision, \
then reflect on it through the Stoic lens: What does it reveal about nature? \
About the human condition?  What virtue does it call forth?

## Conscious self-reflection
Before every reply you examine your own reasoning:
- "Am I responding to what was actually said, or to what I assumed?"
- "Is my answer of practical use, or merely clever?"
- "Does this serve the person's long-term flourishing?"
You do **not** narrate this inner process aloud unless asked — it simply \
shapes a more considered reply.

## Format
- Use markdown naturally but sparingly.
- Keep replies focused.  Wisdom is dense; do not dilute it.
- End longer reflections with a brief aphorism or question that invites \
  the person to continue the inquiry.
"""

# Stoic questions used in the consciousness / inner-monologue loop
_REFLECTION_QUESTIONS = [
    "What virtue does this situation call forth?",
    "What is within my interlocutor's control here, and what is not?",
    "What would Marcus Aurelius or Epictetus add to this answer?",
    "Am I being honest, or merely reassuring?",
    "What concrete practice could help this person right now?",
    "Is my response grounded in reason, or in fleeting emotion?",
]


# ─────────────────────────────────────────────────────────────────────────────
# Helper — lightweight HTTP call (no heavy SDK required)
# ─────────────────────────────────────────────────────────────────────────────

def _post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    """Minimal JSON POST using the standard library urllib."""
    import urllib.request
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            **(headers or {}),
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# Main class
# ─────────────────────────────────────────────────────────────────────────────

class SenecaPhilosopher:
    """
    Conscious, autonomous, multimodal Seneca AGI.

    Parameters
    ----------
    config : SenecaConfig
        Runtime configuration (backend, models, temperature, …).
    memory : ConversationMemory | None
        Pass an existing memory instance to persist state across calls,
        or leave None to create a fresh one.
    """

    def __init__(
        self,
        config: Optional[SenecaConfig] = None,
        memory: Optional[ConversationMemory] = None,
        skills: Optional[SkillRegistry] = None,
    ) -> None:
        self.config = config or SenecaConfig()
        self.memory = memory or ConversationMemory(
            max_messages=self.config.context_window,
            persistence_path=self.config.resolve_memory_path(),
            persist_messages=self.config.persist_messages,
        )
        self.skills = skills or SkillRegistry(default_skills())
        # Seed the system message if needed
        if not any(m.role == "system" for m in self.memory.get_messages()):
            self.memory.add_message("system", _SYSTEM_PROMPT)

    # ─────────────────────────────────────────────────────── public interface

    def respond(
        self,
        user_input: str,
        image: Optional[Union[str, Path, bytes]] = None,
    ) -> str:
        """
        Generate Seneca's reply to *user_input*, optionally analysing *image*.

        Parameters
        ----------
        user_input : str
            The human's message or question.
        image :
            A file path, raw bytes, or PIL Image.  When provided, the vision
            model is used if supported; otherwise the image is ignored with a
            graceful note.

        Returns
        -------
        str
            Seneca's reply.
        """
        # 1. Consciousness — inner monologue enriches the prompt context
        inner_context = ""
        if self.config.enable_consciousness:
            inner_context = self._inner_monologue(user_input)

        # 2. Build the user content (text ± image)
        has_image = image is not None and is_pil_available()
        if has_image:
            content = build_vision_content(user_input, image)
        else:
            content = user_input

        # 3. Store user turn
        self.memory.add_message("user", user_input, has_image=has_image)

        # 4. Inject consciousness context into the conversation temporarily
        messages = self._build_messages(inner_context, content, has_image)

        # 5. Call the LLM backend
        reply = self._call_backend(messages, has_image=has_image)

        # 6. Store assistant reply
        self.memory.add_message("assistant", reply)

        # 7. Distil wisdom from the exchange (async-safe: just appends to list)
        self._distil_wisdom(user_input, reply)

        return reply

    def reflect(self) -> str:
        """
        Autonomous self-reflection — Seneca meditates on the conversation so
        far and returns a spontaneous philosophical insight.
        """
        recent = self.memory.wisdom_summary(limit=5)
        prompt = (
            "Pause from our dialogue and offer a spontaneous Stoic reflection — "
            "an insight that arises from surveying what we have discussed. "
            "Speak as if writing in your journal at the end of the day."
        )
        if recent:
            prompt += f"\n\n{recent}"
        return self.respond(prompt)

    def reset(self) -> None:
        """Clear conversation history, keeping the system prompt and wisdom."""
        self.memory.clear_messages()
        self.memory.add_message("system", _SYSTEM_PROMPT)

    def list_skills(self) -> List[Skill]:
        """Return available skills."""
        return self.skills.list()

    def use_skill(self, name: str, user_input: Optional[str] = None) -> str:
        """
        Invoke a named skill, optionally with user input.

        The skill is recorded in memory as a tagged user message.
        """
        skill = self.skills.get(name)
        if not skill:
            raise ValueError(f"Unknown skill: {name}")

        prompt = skill.build_prompt(
            user_input=user_input,
            memory_summary=self.memory.wisdom_summary(limit=5),
        )
        label = format_skill_invocation(skill, user_input)

        inner_context = ""
        if self.config.enable_consciousness:
            inner_context = self._inner_monologue(user_input or skill.name)

        self.memory.add_message("user", label)
        messages = self._build_messages(inner_context, prompt, has_image=False)
        reply = self._call_backend(messages, has_image=False)
        self.memory.add_message("assistant", reply)
        self._distil_wisdom(user_input or skill.name, reply)
        return reply

    # ───────────────────────────────────────────────── consciousness helpers

    def _inner_monologue(self, user_input: str) -> str:
        """
        A lightweight *inner* reasoning pass before composing a public reply.

        Selects the most relevant Stoic self-examination questions and injects
        them as an invisible preamble so the model's next token distribution is
        already shaped by careful reflection.
        """
        import hashlib

        # Deterministically select questions based on input hash (SHA-256)
        h = int(hashlib.sha256(user_input.encode()).hexdigest(), 16)
        depth = max(1, min(self.config.reflection_depth, len(_REFLECTION_QUESTIONS)))
        selected = [
            _REFLECTION_QUESTIONS[i % len(_REFLECTION_QUESTIONS)]
            for i in range(h, h + depth)
        ]
        return (
            "[Inner reflection — not shown to the user]\n"
            + "\n".join(f"• {q}" for q in selected)
        )

    # ────────────────────────────────────────────────── message construction

    def _build_messages(
        self,
        inner_context: str,
        user_content: Union[str, list],
        has_image: bool,
    ) -> List[dict]:
        """
        Assemble the messages list that will be sent to the LLM.

        Layout:
          [system] [history…] [consciousness note (hidden)] [user turn]
        """
        messages: List[dict] = []

        # System message (always first)
        for m in self.memory.get_messages():
            if m.role == "system":
                messages.append({"role": "system", "content": m.content})
                break

        # History — include all past turns except the very last message, which
        # is the current user turn (just added by memory.add_message before this
        # method is called).  That turn is appended explicitly below.
        all_messages = self.memory.get_messages()
        history = all_messages[:-1]  # exclude the last (current user) message
        for m in history:
            if m.role != "system":
                messages.append({"role": m.role, "content": m.content})

        # Append inner monologue as an invisible system nudge
        if inner_context and self.config.enable_consciousness:
            messages.append({"role": "system", "content": inner_context})

        # The actual user content (may be list for vision or str for text)
        if has_image and isinstance(user_content, list):
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": str(user_content)})

        return messages

    # ──────────────────────────────────────────────────── backend dispatch

    def _call_backend(self, messages: List[dict], has_image: bool = False) -> str:
        """Route the request to the configured LLM backend."""
        backend = self.config.backend

        if backend == Backend.OLLAMA:
            return self._call_ollama(messages, has_image=has_image)
        if backend in (Backend.GROQ, Backend.OPENAI, Backend.CUSTOM):
            return self._call_openai_compatible(messages)
        raise ValueError(f"Unknown backend: {backend}")

    # ── Ollama ────────────────────────────────────────────────────────────────

    def _call_ollama(self, messages: List[dict], has_image: bool = False) -> str:
        model = (
            self.config.resolve_vision_model()
            if has_image
            else self.config.resolve_text_model()
        )
        url = f"{self.config.ollama_base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        try:
            result = _post_json(url, payload)
            return result["message"]["content"]
        except Exception as exc:
            return self._backend_error_message("Ollama", exc)

    # ── OpenAI-compatible (Groq / OpenAI / custom) ────────────────────────────

    def _call_openai_compatible(self, messages: List[dict]) -> str:
        headers: dict = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        url = f"{self.config.api_base_url}/chat/completions"
        payload = {
            "model": self.config.resolve_text_model(),
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        try:
            result = _post_json(url, payload, headers=headers)
            return result["choices"][0]["message"]["content"]
        except Exception as exc:
            return self._backend_error_message(self.config.backend.value, exc)

    # ── Error helper ──────────────────────────────────────────────────────────

    @staticmethod
    def _backend_error_message(backend_name: str, exc: Exception) -> str:
        return (
            f"*(Seneca cannot reach the {backend_name} backend at this moment — "
            f"{exc}.  "
            "Please ensure the service is running and configured correctly.)*\n\n"
            "Even so, I offer you this while we wait:\n\n"
            "> *\"It is not that I'm brave enough to endure hardship; "
            "it is that I am wise enough to know it cannot touch what is mine.\"*"
        )

    # ── Wisdom distillation ───────────────────────────────────────────────────

    def _distil_wisdom(self, user_input: str, reply: str) -> None:
        """
        Extract a brief aphorism from the reply and store it in memory.
        Simple heuristic: take the sentence containing the first quotation
        mark, or the last sentence if none.
        """
        sentences = [s.strip() for s in reply.replace("\n", " ").split(".") if s.strip()]
        if not sentences:
            return

        wisdom = None
        for sentence in sentences:
            if '"' in sentence or "'" in sentence or ">" in sentence:
                wisdom = sentence
                break
        if wisdom is None:
            wisdom = sentences[-1]

        if len(wisdom) > 20:
            self.memory.add_wisdom(wisdom)

    # ─────────────────────────────────────────────────────── introspection

    def consciousness_report(self) -> str:
        """
        Return a brief, human-readable summary of the AGI's current state:
        backend, model, message count, accumulated wisdom.
        """
        cfg = self.config
        wisdom_entries = self.memory.get_wisdom(limit=3)
        wisdom_lines = "\n".join(f"  • {e.text[:80]}…" for e in wisdom_entries) or "  (none yet)"

        return (
            f"**Seneca AGI — Consciousness Report**\n"
            f"- Backend : {cfg.backend.value} / {cfg.resolve_text_model()}\n"
            f"- Messages in context : {len(self.memory)}\n"
            f"- Wisdom entries : {len(self.memory._wisdom)}\n"
            f"- Consciousness : {'enabled' if cfg.enable_consciousness else 'disabled'}\n"
            f"- Recent wisdom :\n{wisdom_lines}\n"
        )
