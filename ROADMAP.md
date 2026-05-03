# 🗺️ Seneca AGI Roadmap

This roadmap is a living document that translates the project’s vision into
clear, staged milestones. It is intentionally detailed so contributors can see
what matters now, what depends on what, and how decisions are made.

**Legend**
- **Now**: foundational or urgent work for the next release
- **Next**: planned once “Now” items land
- **Later**: longer-horizon research or expansion goals

---

## 🌟 Vision

Build a **free, local-first, multimodal philosopher** that helps people reason
clearly, live virtuously, and reflect deeply — while remaining transparent,
inspectable, and usable on everyday hardware.

---

## 🧭 Guiding Principles

1. **Local-first by default** — no API keys required.
2. **Privacy-respecting** — minimal telemetry; user data stays local.
3. **Transparent cognition** — the inner-monologue pipeline is explicit and
   configurable.
4. **Graceful degradation** — when models or vision aren’t available, the system
   should still be helpful and honest.
5. **Minimal dependencies** — prefer stdlib + small libraries to keep setup
   simple and stable.
6. **Testable, offline-friendly** — core logic should be testable without any
   network calls.

---

## ✅ Current Capabilities (Baseline)

- **Multimodal dialogue** with optional image analysis.
- **Consciousness loop** with deterministic inner-monologue questions.
- **Rolling memory window** plus a persistent wisdom ledger.
- **Multiple backends**: Ollama (local), Groq (free-tier), OpenAI, custom.
- **Streamlit UI** for chat, settings, and quick reflections.

---

## 🚧 Roadmap by Stage

### 1) **Now — Stability & Core Foundations** (Short Term)

**Core Engine**
- [ ] Validate configuration at startup (clear errors for invalid models, base
  URLs, or API key mismatch).
- [ ] Add a single source of truth for runtime diagnostics (backend status,
  model selected, vision availability).
- [ ] Harden error messaging for backend failures (actionable steps + fallback).
- [ ] Expand wisdom distillation with consistent formatting and length caps.

**Memory & Persistence**
- [ ] Make memory persistence configurable from the UI and env vars.
- [ ] Add conversation export to JSON/Markdown.
- [ ] Optional “session resume” from recent local history.

**Multimodal**
- [ ] Normalize uploaded images (EXIF rotation, size bounds).
- [ ] Improve descriptive prompting for vision to reduce hallucinations.
- [ ] Add clear UI warnings when vision is disabled or unsupported.

**UI/UX**
- [ ] Improve onboarding: quick tips, first-run guidance.
- [ ] Add “reset wisdom ledger” control (with confirmation).
- [ ] Consistent UI status indicators (backend, model, vision).

**Quality**
- [ ] Expand unit tests for edge cases in message assembly and error handling.
- [ ] Add lightweight linting or formatting guidance (no heavy tooling).

---

### 2) **Next — Autonomy, Memory Depth & Insight** (Mid Term)

**Autonomous Reflection**
- [ ] Scheduled reflection mode (e.g., daily or per N turns).
- [ ] Optional “self-critique” pass for longer responses.
- [ ] Track reflection themes over time.

**Memory Evolution**
- [ ] Wisdom tags (themes like courage, temperance, impermanence).
- [ ] Search/filter wisdom entries.
- [ ] Summarize long conversations into short philosophical notes.

**Multimodal Expansion**
- [ ] Image + text co-reasoning templates (e.g., “describe then interpret”).
- [ ] Add support for multiple images per turn.

**Developer Experience**
- [ ] Publish a lightweight Python package to PyPI.
- [ ] Provide a minimal CLI for scripted reflection and batch prompts.
- [ ] Document configuration with a dedicated reference page.

---

### 3) **Later — Knowledge, Tools & Community** (Long Term)

**Local Knowledge Integration**
- [ ] Optional local document ingestion (notes, journals, books).
- [ ] Retrieval-augmented reflection, fully local.

**Tool Use (Optional)**
- [ ] Add a minimal, permissioned tool layer (e.g., search local notes).
- [ ] Explicit “tool reasoning” mode for transparency.

**Community & Ecosystem**
- [ ] Contribution guide for adding new philosophical personas.
- [ ] Public library of reflection prompts and Stoic exercises.
- [ ] Benchmarks for reflection quality and coherence.

---

## 🧱 Cross-Cutting Milestones

These span multiple stages and should be revisited each cycle.

- **Accessibility**: keyboard-first navigation and readable color contrast.
- **Performance**: keep response times reasonable on modest hardware.
- **Security**: no automatic uploads; explicit user consent for any network calls.
- **Observability**: simple, local logs for debugging (opt-in).

---

## ⚠️ Dependencies & Risks

- **Model availability**: local models may be large; users need disk space and
  compute. Roadmap assumes Ollama remains stable and accessible.
- **API shifts**: Groq/OpenAI compatibility may change; version pinning and
  robust error handling required.
- **UX complexity**: too many controls can overwhelm; defaults should stay
  simple and safe.

---

## 🤝 How to Contribute to the Roadmap

1. Open an issue with a clear proposal and intended user impact.
2. Reference the stage (Now / Next / Later) and any dependencies.
3. Provide a short implementation sketch and testing notes.

If you’re unsure where a proposal fits, open a discussion thread first.

---

## 📍 Update Cadence

The roadmap will be reviewed at least once per release and adjusted based on:

- User feedback and community requests
- Changes in open-source model availability
- Practical constraints on local hardware performance

