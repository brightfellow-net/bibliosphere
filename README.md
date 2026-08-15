# Biblio Sphere

Desktop library management system (Python + PySide6, local SQLite storage, no
server/network component). See `docs/requirements.md` and `docs/architecture.md` for
scope and design.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

python scripts/seed_admin.py   # one-time: create the first librarian account
python main.py                 # run the app (uses data/bibliosphere.db, created on first run)
```

Run the test suite and type checker:

```bash
pytest
mypy
```

## Building a standalone binary

```bash
pip install -e ".[build]"
pyinstaller bibliosphere.spec
```

This builds two executables into `dist/`:

- `dist/Bibliosphere/Bibliosphere` — the app itself.
- `dist/bibliosphere-seed-admin/bibliosphere-seed-admin` — a one-time console tool
  that creates the first librarian account (there's no in-app way to create the very
  first one, same as `scripts/seed_admin.py` above). Run this once, from a terminal,
  before launching `Bibliosphere` for the first time.

The built app stores its database in the OS's standard per-user data directory —
`~/.local/share/Bibliosphere/` on Linux, `%APPDATA%\Bibliosphere\` on Windows,
`~/Library/Application Support/Bibliosphere/` on macOS — not next to the executable.

PyInstaller does not cross-compile: build on (or for) each OS you want to ship a
binary for.
