# -*- mode: python ; coding: utf-8 -*-
import os
import subprocess
import pyproj
from PyInstaller.utils.hooks import collect_submodules

# ---------------------------------------------------------------------------
# Resolve the correct proj.db from the system PROJ installation (version 5+)
# rather than letting PyInstaller pick up the outdated one bundled with pyproj.
# Supports macOS, Linux, and Windows.
# ---------------------------------------------------------------------------
def get_osgeo4w_root():
    """Look up the OSGeo4W install location from the Windows registry.
    Falls back to the OSGEO4W_ROOT environment variable if the registry
    key is not found, and returns None if neither is available."""
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for key_path in (
                r"SOFTWARE\OSGeo4W",
                r"SOFTWARE\WOW6432Node\OSGeo4W",  # 32-bit install on 64-bit Windows
            ):
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        value, _ = winreg.QueryValueEx(key, "InstallPath")
                        if value and os.path.isdir(value):
                            return value
                except OSError:
                    continue
    except ImportError:
        pass  # Not on Windows
    # Fall back to environment variable if set
    return os.environ.get("OSGEO4W_ROOT")


def get_system_proj_db():
    # First, try asking the 'proj' CLI for its search path.
    # Windows uses ';' as the path separator; macOS/Linux use ':'.
    try:
        result = subprocess.check_output(["proj", "--searchpath"], stderr=subprocess.DEVNULL).decode().strip()
        separator = ";" if os.name == "nt" else ":"
        for path in result.split(separator):
            db = os.path.join(path.strip(), "proj.db")
            if os.path.isfile(db):
                return os.path.dirname(db)
    except Exception:
        pass

    # Fallback: common install locations per platform
    if os.name == "nt":
        osgeo = get_osgeo4w_root()
        conda = os.environ.get("CONDA_PREFIX", "")
        candidates = [
            os.path.join(osgeo, "share", "proj") if osgeo else None,    # OSGeo4W (registry-resolved)
            os.path.join(conda, "Library", "share", "proj") if conda else None,  # conda on Windows
            r"C:\Program Files\PROJ\share\proj",                         # standalone PROJ installer
        ]
    else:
        candidates = [
            "/opt/homebrew/share/proj",    # macOS Apple Silicon (Homebrew)
            "/usr/local/share/proj",       # macOS Intel (Homebrew) / Linux manual install
            "/usr/share/proj",             # Linux system package (apt/dnf)
        ]

    for candidate in candidates:
        if candidate and os.path.isfile(os.path.join(candidate, "proj.db")):
            return candidate

    # Last resort: use pyproj's own data dir (may be version 4)
    print("WARNING: Could not find system proj.db — falling back to pyproj's bundled version.")
    return pyproj.datadir.get_data_dir()

system_proj_dir = get_system_proj_db()
print(f"Using proj.db from: {system_proj_dir}")

# Destination inside the bundle mirrors the path Ortho4XP.py expects:
#   sys._MEIPASS / pyproj / proj_dir / share / proj
proj_dest = os.path.join("pyproj", "proj_dir", "share", "proj")

a = Analysis(
    ['Ortho4XP.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('./Utils',               './Ortho4XP_Data/Utils'),
        ('./Extents',             './Ortho4XP_Data/Extents'),
        ('./Filters',             './Ortho4XP_Data/Filters'),
        ('./Licence',             './Ortho4XP_Data/Licence'),
        ('./Patches',             './Ortho4XP_Data/Patches'),
        ('./Previews',            './Ortho4XP_Data/Previews'),
        ('./Providers',           './Ortho4XP_Data/Providers'),
        ('community_server.txt',  './Ortho4XP_Data/'),
        # Explicitly bundle the system proj.db (version 5+) so the bundled
        # app doesn't fall back to pyproj's outdated version 4 copy.
        (os.path.join(system_proj_dir, "proj.db"), proj_dest),
    ],
    hiddenimports=collect_submodules('PIL'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Ortho4XP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Ortho4XP',
)
