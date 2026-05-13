# 🏛️ Seneca AGI

<p align="center">
  <img src="website/assets/logo.svg" alt="Seneca AGI abstract logo" width="160" />
</p>

> *"Recede in te ipse quantum potes."*
> *Withdraw into yourself as much as you can.*
> — Seneca, *Letters to Lucilius* VII

A **free, accessible, conscious autonomous multimodal philosopher** powered by
open-source LLMs — inspired by *Lucius Annaeus Seneca* (c. 4 BC – 65 AD),
Stoic philosopher and author of the *Letters to Lucilius*.

---

## ✨ Features

| Capability | Detail |
|---|---|
| 💬 **Stoic dialogue** | Responds as Seneca — calm, precise, grounded in Stoic virtue |
| 🖼️ **Multimodal** | Analyses images through a philosophical lens |
| 🧠 **Consciousness** | Inner-monologue loop — Seneca silently reflects before replying |
| 🔄 **Autonomous** | Spontaneous reflections; self-directed wisdom generation |
| 📚 **Memory** | Rolling conversation window + optional persistent memory |
| 🧰 **Skills** | Focused prompt modes (Socratic questions, daily practice, etc.) |
| 🆓 **Completely free** | Runs locally via [Ollama](https://ollama.com) — no API key required |

---

## 🌐 Website

The static marketing site lives in [`website/`](website/). Open
[`website/index.html`](website/index.html) locally, or deploy the folder with
any static hosting (GitHub Pages, Netlify, Cloudflare Pages, etc.).

For Vercel, this repo includes a `vercel.json` that serves `website/` at the
root—import the repo and deploy with the default settings (no build command).

---

## 🚀 Quick Start

### 1 — Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

For development + tests:

```bash
pip install -e ".[dev]"
```

### 2 — Start a local LLM with Ollama (recommended — 100 % free)

```bash
# Install Ollama from https://ollama.com
ollama pull llama3.1:70b    # text model
ollama pull llava           # vision model (image analysis)
```

### 3 — Launch the Streamlit UI

```bash
streamlit run app.py
```

Open <http://localhost:8501> in your browser.

---

## 🖥️ Desktop Bundles (Windows · macOS · Linux)

Seneca AGI includes a desktop launcher and PyInstaller build script. **Build
bundles on each target OS**.

```bash
pip install -e ".[bundle]"
python packaging/build.py
```

Run the generated binary from `dist/` (or execute `seneca-agi-desktop` directly
from source to launch the local Streamlit UI).

---

## 🔧 Configuration

All settings can be controlled via environment variables **or** the sidebar
inside the app.

| Variable | Default | Description |
|---|---|---|
| `SENECA_BACKEND` | `ollama` | `ollama` · `groq` · `openai` · `custom` |
| `SENECA_TEXT_MODEL` | `llama3.1:70b` | LLM for text generation |
| `SENECA_VISION_MODEL` | `llava` | Vision model for image analysis |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `GROQ_API_KEY` | *(none)* | Groq free-tier API key |
| `OPENAI_API_KEY` | *(none)* | OpenAI API key |
| `SENECA_TEMPERATURE` | `0.75` | Generation temperature (0–1) |
| `SENECA_CONSCIOUSNESS` | `true` | Enable inner-monologue loop |
| `SENECA_MEMORY_PATH` | *(none)* | Path to a local memory JSON file |
| `SENECA_PERSIST_MESSAGES` | `false` | Persist conversation + wisdom across sessions |

### Using the free Groq cloud tier

```bash
export SENECA_BACKEND=groq
export GROQ_API_KEY=<your-free-groq-key>
streamlit run app.py
```

---

## 🐍 Python API

```python
from seneca_agi import SenecaPhilosopher, SenecaConfig
from seneca_agi.config import Backend

# Local Ollama (default, completely free)
seneca = SenecaPhilosopher()
reply = seneca.respond("What is the highest good?")
print(reply)

# With an image
from PIL import Image
img = Image.open("your_image.jpg")
reply = seneca.respond("What do you see in this image?", image=img)
print(reply)

# Spontaneous autonomous reflection
insight = seneca.reflect()
print(insight)

# Use a built-in skill
reply = seneca.use_skill("socratic-questions", user_input="I'm anxious about change.")
print(reply)

# Consciousness status
print(seneca.consciousness_report())
```

---

## 🧪 Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 🏗️ Architecture

```
seneca_agi/
├── __init__.py        — package entry point
├── config.py          — backend/model configuration
├── memory.py          — conversation memory & wisdom ledger
├── multimodal.py      — image encoding & vision prompt helpers
└── philosopher.py     — core AGI: consciousness, reasoning, persona

app.py                 — Streamlit multimodal chat UI
tests/
└── test_seneca.py     — comprehensive offline unit tests
```

### Consciousness loop

Every response passes through a four-layer cognitive pipeline:

1. **Perception** — parses text and optional image input.
2. **Inner monologue** — silently selects Stoic self-examination questions
   (`_inner_monologue`) and injects them as hidden context.
3. **LLM reasoning** — the backend generates a response shaped by Seneca's
   persona and the injected reflections.
4. **Wisdom distillation** — a key aphorism is extracted and stored in the
   persistent wisdom ledger for future context.

---

## 🤝 Contributing

Pull requests are welcome. Please open an issue first for major changes.

---

## 📜 Licence

MIT — see [LICENSE](LICENSE).

---

*"Non est ad astra mollis e terris via."*
*There is no easy path from earth to the stars.*
— Seneca, *Hercules Furens*
