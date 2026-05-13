"""
Skill system for Seneca AGI.

Skills are lightweight, named prompt templates that guide Seneca toward a
specific kind of response (e.g., Socratic questioning, daily practice).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

TOPIC_PLACEHOLDER = "{topic}"


@dataclass(frozen=True)
class Skill:
    """A named prompt template that shapes Seneca's response."""

    name: str
    description: str
    prompt: str
    requires_input: bool = False
    include_memory_summary: bool = True

    def build_prompt(self, user_input: Optional[str], memory_summary: str) -> str:
        if self.requires_input and not user_input:
            raise ValueError(f"Skill '{self.name}' requires input.")
        prompt = self.prompt
        if TOPIC_PLACEHOLDER in prompt:
            prompt = prompt.format(topic=(user_input or "").strip())
        prompt = prompt.strip()
        if self.include_memory_summary and memory_summary:
            prompt = f"{prompt}\n\n{memory_summary}".strip()
        return prompt


def format_skill_invocation(skill: Skill, user_input: Optional[str]) -> str:
    """
    Format the visible user message for a skill invocation.

    Parameters
    ----------
    skill:
        The skill being invoked.
    user_input:
        Optional user-provided context for the skill.
    """
    label = f"[Skill: {skill.name}]"
    if user_input:
        label = f"{label} {user_input.strip()}"
    return label


class SkillRegistry:
    """Registry for available skills."""

    def __init__(self, skills: Iterable[Skill]) -> None:
        self._skills = {skill.name: skill for skill in skills}

    def list(self) -> List[Skill]:
        return list(self._skills.values())

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)


def default_skills() -> List[Skill]:
    """Built-in skill set shipped with Seneca AGI."""
    return [
        Skill(
            name="socratic-questions",
            description="Ask clarifying Stoic questions about a situation.",
            prompt=(
                "Ask 3–5 concise Stoic questions that help someone reflect on:"
                f" \"{TOPIC_PLACEHOLDER}\". Keep each question brief and practical."
            ),
            requires_input=True,
        ),
        Skill(
            name="daily-practice",
            description="Suggest a Stoic exercise for today.",
            prompt=(
                "Offer a small Stoic exercise for the next 24 hours, grounded in:"
                f" \"{TOPIC_PLACEHOLDER}\". Make it concrete and doable."
            ),
            requires_input=True,
        ),
        Skill(
            name="wisdom-distill",
            description="Distill the recent conversation into crisp wisdom.",
            prompt=(
                "Distill the recent conversation into 2–3 crisp aphorisms. "
                "End with a question that invites deeper inquiry."
            ),
            include_memory_summary=True,
        ),
    ]
