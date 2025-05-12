"""
Smoke Dispersion Simulator
==========================

Reads a *single* FireMap JSON and produces:

• One **KML** per horizon (0.5 h, 1.5 h, 2.5 h)
• One **metadata JSON** bundling *all* horizons in a single object:

      {
        "guid": "...",
        "lat" : 30.30,
        "lon" : -97.73,
        "horizons": {
          "0.5h": {
              "kml": "plumes/2025-05-11_<guid>_1.kml",
              "wspd": 4,
              "wdir": 180,
              "erate": 4.77,
              ...
          },
          "1.5h": { ... },
          "2.5h": { ... }
        }
      }

The schema is future‑proof: a new key `3d` can later hold volumetric links
without touching the API layer.
"""
from __future__ import annotations
import json, subprocess, shutil
from pathlib import Path
from datetime import datetime
from backend.utils.paths import conf, PLUMES_D, META_D
from backend.ingest.weather import get_hourly_wx

# (Lookup tables from legacy script)
_dirs  = "N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW".split()
_angles = [0,25,45,65,90,115,135,155,180,205,225,245,270,295,315,335]

def _wx_block(lat: float, lon: float) -> dict:
    """
    Return integer wind speed (mph ≥ 1) and direction (deg 1‑360).
    """
    wx = get_hourly_wx(lat, lon)

    # ---------- speed ----------------------------------------------------
    raw = wx["windSpeed"].split()[0]
    wspd = int(raw) if raw.isdigit() else 0
    if wspd < 1:
        wspd = 1                         # VSmoke rejects U < 0.1 mph

    # ---------- direction -------------------------------------------------
    dir_txt = wx["windDirection"]
    if dir_txt not in _dirs:             # e.g. "Calm"
        dir_txt = "N"
    wdir = _angles[_dirs.index(dir_txt)]
    if wdir == 0:                        # clamp 0 deg to 360 deg
        wdir = 360

    return {"wspd": wspd, "wdir": wdir}




# ------------------------------------------------------------------
# helper: write one meta‑JSON with *exactly* the stem you give me
# ------------------------------------------------------------------
def _build_input(meta: dict) -> Path:
    """
    Write the per‑horizon metadata JSON.

    File name becomes  <stem>.json  — no extra horizon tag is appended.
    """
    ipt = META_D / f"{meta['stem']}.json"
    ipt.write_text(json.dumps(meta, indent=2))
    return ipt

def _run_vsmoke(ipt: Path) -> Path:
    """
    Drive the Fortran VSmoke model and the legacy KML converter.

    Steps
    -----
    1.  Run VSMKARC.EXE (directly on Windows, or via Wine on *nix) in
        `backend/vsmoke_bin/` so its data files are in scope.
        • If the solver aborts (e.g., U < 0.1 mph) we raise RuntimeError.
    2.  In the **same working directory** run the Python wrapper
        `backend.simulators.runvsmoke` which generates <name>.kml under
        PLUMES_D.
    3.  Return the absolute path to that KML.
    """
    import os, sys, json, subprocess
    vsmoke_bin = Path(conf.vsmoke["exe"]).parent

    # ── 1) Fortran solver ────────────────────────────────────────────────
    if conf.vsmoke["wine"]:                              # Linux/macOS
        cmd = [conf.vsmoke["wine"], str(conf.vsmoke["exe"])]
    else:                                                # Windows
        cmd = [str(conf.vsmoke["exe"])]

    result = subprocess.run(
        cmd,
        cwd=vsmoke_bin,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"VSmoke solver failed:\n{result.stdout.strip()}"
        )

    # ── 2) KML converter ─────────────────────────────────────────────────
    env = os.environ.copy()
    env["PYTHONPATH"] = str(conf.project_root)           # ensure backend importable

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.simulators.runvsmoke",
            "--input",
            str(ipt),
        ],
        cwd=vsmoke_bin,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"runvsmoke.py failed:\n{result.stdout.strip()}"
        )

    # ── 3) Resolve final KML path ────────────────────────────────────────
    name = json.loads(ipt.read_text())["name"]
    return PLUMES_D / f"{name}.kml"




def _single_horizon(guid: str, lat: float, lon: float,
                    tag: str, minutes_ahead: float) -> dict:
    """
    Produce a plume for one horizon and return its metadata snippet.
    """
    meta = {
        "stem": f"{datetime.now().date()}_{guid}_{tag}",
        "guid": guid,
        "lat": lat,  "lon": lon,
        "acres": conf.vsmoke["acres_default"],
        "mix":   conf.vsmoke["mix_height_ft"],
        "stclass": conf.vsmoke["stability_class"],
        "frise": conf.vsmoke["plume_rise_fraction"],
        "horizon_min": minutes_ahead,
        "erate": 4.77,  # ← kept from legacy (could be dynamic)
        "hrate": 5.18
    }
    meta["name"] = meta["stem"]
    meta.update(_wx_block(lat, lon))
    ipt = _build_input(meta)
    kml = _run_vsmoke(ipt)
    meta["kml"] = str(kml.relative_to(conf.project_root))
    return meta

def process_firemap(firemap_json: Path):
    """
    Iterate through RSS <item> nodes and generate three horizons each.
    """
    rss = json.loads(firemap_json.read_text())["rss"]["channel"]["item"]
    items = rss if isinstance(rss, list) else [rss]

    for it in items:
        guid = it["guid"]["#text"]
        lat, lon = map(float, it["link"].split("q=")[1].split(","))
        bundle = {
            "guid": guid,
            "lat": lat, "lon": lon,
            "horizons": {
                "0.5h": _single_horizon(guid, lat, lon, "1", 30),
                "1.5h": _single_horizon(guid, lat, lon, "2", 90),
                "2.5h": _single_horizon(guid, lat, lon, "3", 150),
            }
        }
        out = META_D / f"{firemap_json.stem}_{guid}.json"
        out.write_text(json.dumps(bundle, indent=2))
        print("✓ 3‑horizon plume:", out.name)

if __name__ == "__main__":
    today = PLUMES_D.parent/"ingested_fire_incident_maps"/f"FireMap_{datetime.now().date()}.json"
    process_firemap(today)
