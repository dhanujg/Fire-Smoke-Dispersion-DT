"""
Local end‑to‑end test
=====================

1. Ingest RSS for a user‑supplied or current date.
2. Run 3‑horizon smoke simulation for every incident.
3. Print resulting files so the developer can drag‑drop into QGIS/ArcGIS.
"""

# ---- path shim: make parent folder importable ---------------------------
import pathlib, sys, os
TEST_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
# -------------------------------------------------------------------------

import sys, webbrowser
from backend.ingest.fire_ingester import run as ingest
from backend.simulators.smoke_simulator import process_firemap
from backend.utils.paths import conf, INGEST_D, PLUMES_D, META_D
from datetime import date as datetime

day = sys.argv[1] if len(sys.argv) > 1 else None

# Step 1 – Fetch RSS
j_fp = ingest(day)

# Step 2 – Simulate plumes
process_firemap(j_fp)

# Step 3 – List artefacts
for lbl, path in [("FIRE MAPS", INGEST_D), ("PLUMES", PLUMES_D), ("META", META_D)]:
    print(f"\n── {lbl} ──")
    for f in sorted(path.glob("*")):
        print("   •", f.relative_to(conf.project_root))

# ── Build GeoJSON bundle ---------------------------------------------------
from backend.api.transform_to_geojson import build as build_gj
gj_path = build_gj(day or datetime.date.today().isoformat())
print("\nGeoJSON saved →", gj_path.relative_to(conf.project_root))
webbrowser.open(f"file:///{gj_path}")    # auto‑open in browser if supported


# Bonus – open fires GeoJSON in browser to verify API output quickly
url = f"http://localhost:{conf.api['port']}/fires/{day or 'latest'}"
print("\nOpen →", url)
try:
    webbrowser.open(url)
except RuntimeError:
    pass

