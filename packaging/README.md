# Desktop Bundling

Seneca AGI bundles into a single-file desktop launcher with PyInstaller. Builds must be created on
**each target OS** (Windows, macOS, Linux).

## Prerequisites

- Python 3.9+
- A working C compiler toolchain for your OS

## Install bundling dependencies

```bash
pip install -e ".[bundle]"
```

## Build the bundle

```bash
python packaging/build.py
```

The bundled executable appears in `dist/`:

- **Windows:** `dist/SenecaAGI.exe`
- **macOS:** `dist/SenecaAGI`
- **Linux:** `dist/SenecaAGI`

## Run

```bash
./dist/SenecaAGI
```

## Notes

- macOS distributions may require signing and notarization before sharing.
- Override the default Streamlit port with `SENECA_DESKTOP_PORT=8501`.
