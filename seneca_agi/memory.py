"""
Conversation memory and wisdom store for Seneca AGI.

Keeps a rolling window of the dialogue and accumulates a personal
wisdom ledger — aphorisms and insights the AGI has generated or
distilled, so that later replies remain coherent and self-consistent.
"""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Message:
    """A single turn in the conversation."""

    role: str          # "user" | "assistant" | "system"
    content: str
    timestamp: float = field(default_factory=time.time)
    has_image: bool = False

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "has_image": self.has_image,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Message":
        return cls(
            role=d["role"],
            content=d["content"],
            timestamp=d.get("timestamp", time.time()),
            has_image=d.get("has_image", False),
        )


@dataclass
class WisdomEntry:
    """A distilled philosophical insight."""

    text: str
    source: str = "reflection"   # "reflection" | "user" | "citation"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"text": self.text, "source": self.source, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, d: dict) -> "WisdomEntry":
        return cls(text=d["text"], source=d.get("source", "reflection"),
                   timestamp=d.get("timestamp", time.time()))


# ─────────────────────────────────────────────────────────────────────────────
# Memory store
# ─────────────────────────────────────────────────────────────────────────────

class ConversationMemory:
    """
    Rolling-window dialogue memory plus a persistent wisdom ledger.

    Parameters
    ----------
    max_messages:
        How many recent messages to keep in active context.
    persistence_path:
        Optional file path for persisting wisdom entries across sessions.
    """

    def __init__(
        self,
        max_messages: int = 20,
        persistence_path: Optional[Path] = None,
        persist_messages: bool = False,
    ) -> None:
        self._messages: Deque[Message] = deque(maxlen=max_messages)
        self._wisdom: List[WisdomEntry] = []
        self._persistence_path = persistence_path
        self._persist_messages = persist_messages
        if persistence_path and persistence_path.exists():
            self._load(persistence_path)

    # ---------------------------------------------------------------- messages

    def add_message(self, role: str, content: str, has_image: bool = False) -> None:
        self._messages.append(Message(role=role, content=content, has_image=has_image))
        if self._persist_messages and self._persistence_path:
            self._save(self._persistence_path)

    def get_messages(self) -> List[Message]:
        return list(self._messages)

    def get_messages_as_dicts(self) -> List[dict]:
        """Return messages in the format expected by chat-completion APIs."""
        return [{"role": m.role, "content": m.content} for m in self._messages]

    def clear_messages(self) -> None:
        self._messages.clear()
        if self._persist_messages and self._persistence_path:
            self._save(self._persistence_path)

    # ----------------------------------------------------------------- wisdom

    def add_wisdom(self, text: str, source: str = "reflection") -> None:
        entry = WisdomEntry(text=text, source=source)
        self._wisdom.append(entry)
        if self._persistence_path:
            self._save(self._persistence_path)

    def get_wisdom(self, limit: int = 5) -> List[WisdomEntry]:
        """Return the most recent *limit* wisdom entries."""
        return self._wisdom[-limit:]

    def wisdom_summary(self, limit: int = 3) -> str:
        """One-liner summary of recent wisdom for injection into prompts."""
        entries = self.get_wisdom(limit)
        if not entries:
            return ""
        lines = [f"• {e.text}" for e in entries]
        return "Recent reflections:\n" + "\n".join(lines)

    # ----------------------------------------------------------- serialisation

    def _save(self, path: Path) -> None:
        data = {
            "wisdom": [w.to_dict() for w in self._wisdom],
        }
        if self._persist_messages:
            data["messages"] = [m.to_dict() for m in self._messages]
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            if path.parent.name == ".seneca_agi":
                path.parent.chmod(0o700)
        except OSError:
            pass
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass

    def _load(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._wisdom = [WisdomEntry.from_dict(d) for d in data.get("wisdom", [])]
            if self._persist_messages:
                self._messages.clear()
                for message in data.get("messages", []):
                    self._messages.append(Message.from_dict(message))
        except (json.JSONDecodeError, KeyError):
            pass  # Corrupt file — start fresh

    # --------------------------------------------------------------- helpers

    def __len__(self) -> int:
        return len(self._messages)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ConversationMemory(messages={len(self._messages)}, "
            f"wisdom={len(self._wisdom)})"
        )
