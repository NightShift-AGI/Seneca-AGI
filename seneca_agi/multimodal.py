"""
Multimodal utilities for Seneca AGI.

Handles image encoding, resizing, and format normalisation so that
any upstream vision model receives a consistent payload.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Optional, Tuple, Union

try:
    from PIL import Image, ImageOps
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Maximum dimension (width or height) before the image is down-scaled.
MAX_IMAGE_DIM = 1024
# JPEG quality used when re-encoding for transmission.
JPEG_QUALITY = 85


# ─────────────────────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────────────────────

def is_pil_available() -> bool:
    """Return True if Pillow is installed."""
    return _PIL_AVAILABLE


def load_image(source: Union[str, Path, bytes, "Image.Image"]) -> "Image.Image":
    """
    Load an image from a file path, raw bytes, or an existing PIL Image.

    Raises
    ------
    ImportError  — if Pillow is not installed.
    ValueError   — if the source type is not recognised.
    """
    if not _PIL_AVAILABLE:
        raise ImportError(
            "Pillow is required for image support: pip install Pillow"
        )

    if isinstance(source, Image.Image):
        return source
    if isinstance(source, (str, Path)):
        return Image.open(source)
    if isinstance(source, (bytes, bytearray)):
        return Image.open(io.BytesIO(source))
    raise ValueError(f"Unsupported image source type: {type(source)}")


def resize_image(
    image: "Image.Image",
    max_dim: int = MAX_IMAGE_DIM,
) -> "Image.Image":
    """
    Down-scale *image* so that neither dimension exceeds *max_dim*.
    Preserves aspect ratio.  Returns the image unchanged if already small.
    """
    w, h = image.size
    if max(w, h) <= max_dim:
        return image
    scale = max_dim / max(w, h)
    new_size = (int(w * scale), int(h * scale))
    return image.resize(new_size, Image.LANCZOS)


def image_to_base64(
    source: Union[str, Path, bytes, "Image.Image"],
    fmt: str = "JPEG",
    max_dim: int = MAX_IMAGE_DIM,
    quality: int = JPEG_QUALITY,
) -> Tuple[str, str]:
    """
    Convert an image to a base64-encoded string suitable for API payloads.

    Returns
    -------
    (base64_string, mime_type)
        *base64_string* — raw base64 data (no ``data:`` prefix).
        *mime_type*     — e.g. ``"image/jpeg"``.
    """
    img = load_image(source)
    img = resize_image(img, max_dim)

    # Ensure RGB mode for JPEG output
    if fmt.upper() == "JPEG" and img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")

    buffer = io.BytesIO()
    img.save(buffer, format=fmt, quality=quality if fmt.upper() == "JPEG" else None)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    mime = f"image/{fmt.lower()}"
    return b64, mime


def build_vision_content(
    text_prompt: str,
    image_source: Optional[Union[str, Path, bytes, "Image.Image"]] = None,
) -> list:
    """
    Build the ``content`` field for an OpenAI-style vision chat message.

    Returns a list of content parts that can be passed directly to the
    ``messages`` field of a chat-completion request.

    If *image_source* is None, returns a plain text part only.
    """
    parts: list = [{"type": "text", "text": text_prompt}]

    if image_source is not None:
        b64, mime = image_to_base64(image_source)
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            }
        )

    return parts


def get_image_description_prompt(philosophical_context: str = "") -> str:
    """
    Return a system-level instruction that primes Seneca to comment on an image
    through a Stoic philosophical lens.
    """
    base = (
        "You are viewing an image. Describe what you perceive, "
        "then reflect upon it as Seneca would — drawing on Stoic virtue, "
        "impermanence, the dichotomy of control, and the examined life."
    )
    if philosophical_context:
        return f"{base}\n\nPhilosophical context: {philosophical_context}"
    return base
