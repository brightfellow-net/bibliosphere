# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: builds two standalone executables from this project.

Run (after `pip install -e ".[build]"`): pyinstaller bibliosphere.spec

Output lands in dist/Bibliosphere/ (the app) and dist/bibliosphere-seed-admin/ (a
one-time console tool that creates the first librarian account — see
scripts/seed_admin.py's docstring for why that has to be run once, from a terminal,
before the app can log in). Both resolve to the same on-disk database once frozen —
see infrastructure/sqlite/connection.py's default_db_path().

schema.sql is loaded at runtime via importlib.resources (connection.py), not a plain
file read, so it's listed explicitly in `datas` below rather than relying on
PyInstaller's static import analysis to discover it on its own.
"""

SCHEMA_DATAS = [
    ("src/bibliosphere/infrastructure/sqlite/schema.sql", "bibliosphere/infrastructure/sqlite"),
]

app_analysis = Analysis(
    ["main.py"],
    pathex=["src"],
    datas=SCHEMA_DATAS,
)
app_pyz = PYZ(app_analysis.pure)
app_exe = EXE(
    app_pyz,
    app_analysis.scripts,
    [],
    exclude_binaries=True,
    name="Bibliosphere",
    console=False,
)

seed_admin_analysis = Analysis(
    ["scripts/seed_admin.py"],
    pathex=["src"],
    datas=SCHEMA_DATAS,
)
seed_admin_pyz = PYZ(seed_admin_analysis.pure)
seed_admin_exe = EXE(
    seed_admin_pyz,
    seed_admin_analysis.scripts,
    [],
    exclude_binaries=True,
    name="bibliosphere-seed-admin",
    console=True,
)

COLLECT(
    app_exe,
    app_analysis.binaries,
    app_analysis.zipfiles,
    app_analysis.datas,
    name="Bibliosphere",
)

COLLECT(
    seed_admin_exe,
    seed_admin_analysis.binaries,
    seed_admin_analysis.zipfiles,
    seed_admin_analysis.datas,
    name="bibliosphere-seed-admin",
)
