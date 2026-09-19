"""Inventory and copy only the owner-supplied Glass templates, unchanged."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine/src/hermes_video"))
from glass_pack import import_library

if __name__ == "__main__":
    library = import_library(ROOT / "config/glass-pack-sources.json", ROOT)
    print(json.dumps({"assets": len(library["assets"]), "packages": library["packages"],
                      "fontLockedAssets": sum(bool(a["fontLocked"]) for a in library["assets"]),
                      "nativeApproved": 0}, ensure_ascii=False))
