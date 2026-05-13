from __future__ import annotations

import os
import sys
from pathlib import Path

from streamlit.web import bootstrap

DEFAULT_PORT = 8501


def _resolve_app_path() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "app.py"
    return Path(__file__).resolve().parents[1] / "app.py"


def main() -> None:
    app_path = _resolve_app_path()
    if not app_path.exists():
        raise FileNotFoundError(f"Streamlit app not found at {app_path}")

    port = int(os.environ.get("SENECA_DESKTOP_PORT", DEFAULT_PORT))

    flag_options = {
        "server.address": "127.0.0.1",
        "server.port": port,
        "server.headless": False,
        "browser.gatherUsageStats": False,
        "server.fileWatcherType": "none",
    }

    bootstrap.run(str(app_path), False, [], flag_options)


if __name__ == "__main__":
    main()
