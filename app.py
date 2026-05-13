"""
Seneca AGI — Streamlit multimodal chat interface.

Run with:
    streamlit run app.py

Environment variables (all optional):
    SENECA_BACKEND        ollama | groq | openai | custom  (default: ollama)
    SENECA_TEXT_MODEL     LLM model name                   (default: llama3.2)
    SENECA_VISION_MODEL   Vision model name                (default: llava)
    OLLAMA_BASE_URL       http://localhost:11434           (default)
    GROQ_API_KEY          your Groq API key
    OPENAI_API_KEY        your OpenAI API key
    SENECA_API_KEY        generic key for custom backends
    SENECA_API_BASE_URL   custom OpenAI-compatible base URL
    SENECA_TEMPERATURE    0.0 – 1.0                        (default: 0.75)
    SENECA_MEMORY_PATH    path to memory JSON file
    SENECA_PERSIST_MESSAGES true | false                   (default: false)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import streamlit as st

from seneca_agi.config import Backend, SenecaConfig
from seneca_agi.memory import ConversationMemory
from seneca_agi.multimodal import is_pil_available
from seneca_agi.philosopher import SenecaPhilosopher
from seneca_agi.skills import format_skill_invocation

# Shared UI strings
IMAGE_PLACEHOLDER_NOTE = "*(Image attached in a previous session.)*"

# ─────────────────────────────────────────────────────────────────────────────
# Page configuration
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Seneca AGI · Stoic Philosopher",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────────────────────────────────────

def _init_session() -> None:
    if "philosopher" not in st.session_state:
        cfg = _build_config_from_sidebar_defaults()
        st.session_state.philosopher = SenecaPhilosopher(config=cfg)
        st.session_state.chat_history = _hydrate_chat_history(
            st.session_state.philosopher.memory
        )
        st.session_state.config = cfg


def _build_config_from_sidebar_defaults() -> SenecaConfig:
    """Build a SenecaConfig, respecting env vars for server-side defaults."""
    return SenecaConfig()


def _default_memory_path() -> str:
    return str(Path.home() / ".seneca_agi" / "memory.json")


def _hydrate_chat_history(memory: ConversationMemory) -> list[tuple[str, str, Optional[bytes]]]:
    """Restore chat history from persisted memory for display."""
    history: list[tuple[str, str, Optional[bytes]]] = []
    for message in memory.get_messages():
        if message.role == "system":
            continue
        text = message.content
        if message.has_image:
            text = f"{text}\n\n{IMAGE_PLACEHOLDER_NOTE}"
        history.append((message.role, text, None))
    return history


_init_session()

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — settings & status
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Configuration")

    backend_choice = st.selectbox(
        "LLM Backend",
        options=[b.value for b in Backend],
        index=[b.value for b in Backend].index(
            st.session_state.config.backend.value
        ),
        help="Ollama (local, free) is recommended for full privacy.",
    )

    text_model = st.text_input(
        "Text Model",
        value=st.session_state.config.text_model,
        help="Ollama: llama3.2, mistral, phi3 · Groq: llama3-8b-8192",
    )

    vision_model = st.text_input(
        "Vision Model",
        value=st.session_state.config.vision_model,
        help="Ollama: llava · leave blank to disable image analysis",
    )

    api_key = st.text_input(
        "API Key",
        value=st.session_state.config.api_key or "",
        type="password",
        help="Required for Groq / OpenAI.  Leave blank for Ollama.",
    )

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=st.session_state.config.temperature,
        step=0.05,
        help="Higher = more creative / less predictable.",
    )

    consciousness = st.toggle(
        "Consciousness (inner monologue)",
        value=st.session_state.config.enable_consciousness,
        help=(
            "When enabled, Seneca silently reflects on Stoic questions "
            "before composing each reply."
        ),
    )

    persist_messages = st.toggle(
        "Persistent memory",
        value=st.session_state.config.persist_messages,
        help="Store conversation + wisdom locally and resume on next launch.",
    )

    memory_path = st.text_input(
        "Memory file path",
        value=st.session_state.config.memory_path or _default_memory_path(),
        help="Local JSON file used to store persistent memory.",
        disabled=not persist_messages,
    )

    if st.button("♻️ Apply & Reload/Reset Session"):
        resolved_memory_path = None
        if persist_messages:
            resolved_memory_path = memory_path.strip() or _default_memory_path()
        new_cfg = SenecaConfig(
            backend=Backend(backend_choice),
            text_model=text_model,
            vision_model=vision_model,
            api_key=api_key or None,
            temperature=temperature,
            enable_consciousness=consciousness,
            persist_messages=persist_messages,
            memory_path=resolved_memory_path,
        )
        st.session_state.config = new_cfg
        st.session_state.philosopher = SenecaPhilosopher(config=new_cfg)
        if persist_messages:
            st.session_state.chat_history = _hydrate_chat_history(
                st.session_state.philosopher.memory
            )
        else:
            st.session_state.philosopher.reset()
            st.session_state.chat_history = []
        st.rerun()

    st.divider()

    if st.button("🌿 Spontaneous Reflection"):
        with st.spinner("Seneca meditates…"):
            insight = st.session_state.philosopher.reflect()
        st.session_state.chat_history.append(("assistant", insight, None))
        st.rerun()

    if st.button("📋 Consciousness Report"):
        report = st.session_state.philosopher.consciousness_report()
        st.info(report)

    if st.button("🧹 Clear Conversation Memory"):
        st.session_state.philosopher.reset()
        st.session_state.chat_history = []
        st.rerun()

    st.divider()
    st.subheader("🧰 Skills")

    skill_options = [skill.name for skill in st.session_state.philosopher.list_skills()]
    skill_choice = st.selectbox(
        "Choose a skill",
        options=skill_options,
        help="Skills are focused prompt templates (e.g., Socratic questions).",
    )
    skill_input = st.text_area(
        "Skill input (optional)",
        value="",
        placeholder="Describe a situation or topic for the skill to act on...",
    )

    if st.button("▶️ Run Skill"):
        skill = st.session_state.philosopher.skills.get(skill_choice)
        if skill and skill.requires_input and not skill_input.strip():
            st.warning("This skill needs input. Add a short description and try again.")
        elif not skill:
            st.error("Selected skill is unavailable.")
        else:
            with st.spinner("Seneca applies the skill…"):
                reply = st.session_state.philosopher.use_skill(
                    skill_choice,
                    user_input=skill_input or None,
                )
            label = format_skill_invocation(skill, skill_input or None)
            st.session_state.chat_history.append(("user", label, None))
            st.session_state.chat_history.append(("assistant", reply, None))
            st.rerun()

    st.divider()

    st.markdown(
        """
        **Seneca AGI** is a free, open-source multimodal AI philosopher
        inspired by *Lucius Annaeus Seneca* (4 BC – 65 AD).

        It runs entirely on local hardware via
        [Ollama](https://ollama.com) — no data leaves your machine.

        > *"Recede in te ipse quantum potes."*
        > *Withdraw into yourself as much as you can.*
        > — Seneca, *Letters* VII
        """,
        unsafe_allow_html=False,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Main content area
# ─────────────────────────────────────────────────────────────────────────────

st.title("🏛️ Seneca AGI")
st.caption(
    "A conscious, autonomous, multimodal Stoic philosopher · "
    f"Backend: **{st.session_state.config.backend.value}** · "
    f"Model: **{st.session_state.config.resolve_text_model()}**"
)

# ── Chat history display ──────────────────────────────────────────────────────

for role, text, img_bytes in st.session_state.chat_history:
    with st.chat_message(role, avatar="🏛️" if role == "assistant" else "🧑"):
        if img_bytes is not None:
            st.image(img_bytes, caption="Uploaded image", use_container_width=True)
        st.markdown(text)

# ── Image upload ──────────────────────────────────────────────────────────────

uploaded_file = st.file_uploader(
    "📷 Attach an image (optional) — Seneca will reflect on it philosophically",
    type=["png", "jpg", "jpeg", "webp", "gif"],
    label_visibility="visible",
)

if uploaded_file and not is_pil_available():
    st.warning(
        "Pillow is not installed — image analysis is unavailable.  "
        "Install it with `pip install Pillow` and restart the app."
    )

# ── Input box ────────────────────────────────────────────────────────────────

user_input = st.chat_input(
    "Ask Seneca anything — philosophy, life, ethics, purpose…"
)

if user_input:
    img_bytes: Optional[bytes] = None
    if uploaded_file is not None and is_pil_available():
        img_bytes = uploaded_file.getvalue()

    # Show user turn immediately
    with st.chat_message("user", avatar="🧑"):
        if img_bytes is not None:
            st.image(img_bytes, caption="Your image", use_container_width=True)
        st.markdown(user_input)

    st.session_state.chat_history.append(("user", user_input, img_bytes))

    # Generate Seneca's reply
    with st.chat_message("assistant", avatar="🏛️"):
        with st.spinner("Seneca reflects…"):
            reply = st.session_state.philosopher.respond(
                user_input=user_input,
                image=img_bytes,
            )
        st.markdown(reply)

    st.session_state.chat_history.append(("assistant", reply, None))
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
st.markdown(
    "<div style='text-align:center; color:#888; font-size:0.8em;'>"
    "Seneca AGI · Free &amp; Open Source · "
    "<a href='https://github.com/NightShift-AGI/Seneca-AGI' target='_blank'>"
    "GitHub</a>"
    "</div>",
    unsafe_allow_html=True,
)
# Shared UI strings
