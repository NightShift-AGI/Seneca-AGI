from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.__main__ import run as pyinstaller_run


def _data_arg(source: Path, destination: str) -> str:
    separator = ";" if sys.platform.startswith("win") else ":"
    return f"{source}{separator}{destination}"


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    entry_point = project_root / "seneca_agi" / "desktop.py"

    args = [
        str(entry_point),
        "--name=SenecaAGI",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--collect-all=streamlit",
        f"--add-data={_data_arg(project_root / 'app.py', '.')}",
    ]

    pyinstaller_run(args)


if __name__ == "__main__":
    main()
