# Austin Fire & Smoke Dispersion & Digital‑Twin APIs 
##### Author(s): Dhanuj M. Gandikota, Ryan Lewis

## Description
The project is developed and maintained by the TexUS Extreme Weather & Urban Climate Modeling Lab, Jackson School of Geosciences, The University of Texas at Austin. 

This application ingests daily fire‑incident reports from the Austin Fire Department, simulates near‑real‑time smoke‑plume dispersion with the VSmoke model, and serves the results—together with meteorology and emissions metadata—through public‑facing APIs that drop directly into ArcGIS Online or ArcGIS Pro


> End‑to‑end toolkit for **ingesting Austin Fire Department RSS feeds,
> simulating 2‑D VSmoke plumes**, and exposing the results via
> **FastAPI** (+ an ArcGIS‑friendly façade).  
> Includes a one‑click *local smoke‑test* that downloads incidents,
> runs three forecast horizons, builds a multi‑layer GeoJSON bundle, and
> opens both APIs in your browser.

---

## 1  Repository layout


Fire-Smoke-Dispersion-DT/
├─ backend/                    ← src package (importable as `firesmoke`)
│  ├─ ingest/                  ← data acquisition
│  ├─ simulators/              ← VSmoke driver + legacy converter
│  ├─ api/                     ← FastAPI apps (data + ArcGIS)
│  ├─ utils/                   ← config & path helpers
│  └─ vsmoke_bin/              ← VSMKARC.EXE + tables (Windows binary)
├─ data/                       ← auto‑created; all outputs land here
│  ├─ ingested_fire_incident_maps/
│  ├─ plumes/                  ← *.kml
│  ├─ dispersion_sim_data/     ← per‑incident JSON bundles
│  └─ geojson/                 ← FireSmokeMap_YYYY‑MM‑DD.geojson
├─ tests/
│  └─ local_smoke_test.py      ← quick pipeline smoke‑test
├─ config.yaml                 ← all paths + model / API parameters
├─ requirements.txt
└─ README.md                   ← (you are here)



---

## 2  Data outputs

| folder / file | what it holds | notes |
|---------------|---------------|-------|
| **`ingested_fire_incident_maps/FireMap_<date>.json`** | raw RSS → JSON snapshot | overwritten when `<date>` == today |
| **`plumes/<date>_<guid>_<tag>.kml`** | VSmoke concentration isopleths per horizon | `_1 = 0.5 h`, `_2 = 1.5 h`, `_3 = 2.5 h` |
| **`dispersion_sim_data/FireMap_<date>_<guid>.json`** | one JSON *bundle* per incident containing all three horizon blocks + meteorology | consumed by the ArcGIS API |
| **`geojson/FireSmokeMap_<date>.geojson`** | single FeatureCollection with three logical layers (`incidents`, `plumes`, `meta`) | ready for drag‑and‑drop into ArcGIS |

---

## 3  Installation

### Windows 10/11 (PowerShell)

```powershell
# 1 – clone
git clone https://github.com/your‑org/Fire_Smoke_Dispersion_DT.git
cd Fire_Smoke_Dispersion_DT

# 2 – Python 3.11 env
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3 – deps (includes Shapely, fastkml, FastAPI …)
pip install -r requirements.txt
```

The repo ships with **`backend/vsmoke_bin/VSMKARC.EXE`** (32‑bit
Fortran); no extra installs needed on Windows.

### Linux / macOS

```bash
git clone https://github.com/your‑org/Fire_Smoke_Dispersion_DT.git
cd Fire_Smoke_Dispersion_DT
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> **VSmoke is Windows‑only.**
> On Linux/macOS the simulator automatically calls the EXE through
> **Wine**. Install a recent Wine (≥ 7.0) and ensure the binary is on
> `$PATH`, then set `vsmoke.wine: "wine"` in `config.yaml`.

---

## 4  Quick pipeline test

### Windows

```powershell
(.venv) PS> python -m tests.local_smoke_test           # today
(.venv) PS> python -m tests.local_smoke_test 2025-05-11
```

### Linux / macOS

```bash
(.venv) $ python -m tests.local_smoke_test             # today
(.venv) $ python -m tests.local_smoke_test 2025-05-11
```

The script will:

1. Fetch / refresh the daily Fire Map.
2. Run VSmoke for 0.5 h, 1.5 h, 2.5 h horizons.
3. Build `FireSmokeMap_<date>.geojson`.
4. Launch **Data API** (`localhost:8080`) and **ArcGIS API**
(`localhost:8081`) in the background and open them in your browser.
Press **Ctrl +C** to stop.

---

## 5  Running the APIs permanently

### Local machine (Windows / Linux / macOS)

```bash
# Data API  (fires, plumes, meta)
uvicorn backend.api.data_api:app --host 0.0.0.0 --port 8080 --reload

# ArcGIS API (layer‑friendly + GeoJSON bundle)
uvicorn backend.api.arcgis_api:app --host 0.0.0.0 --port 8081 --reload
```

Add `--workers 4` to scale on multi‑core boxes.
Use **pm2**, **systemd**, or **nssm** to keep them alive between reboots.

### Cloud / public URLs

| target                                 | steps                                                                                                                                                                                    |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Docker Compose**                     | `docker build -t firesmoke .`<br>`docker run -d -p 8080:8080 -p 8081:8081 firesmoke`                                                                                                     |
| **Fly.io / Render / Railway**          | 1. Add `requirements.txt` and `start` cmd (`uvicorn backend.api.data_api:app … && uvicorn backend.api.arcgis_api:app …`).<br>2. Provision two services or a Procfile with two processes. |
| **AWS EC2**                            | same as local; front with an ALB or Nginx                                                                                                                                                |
| **Azure App Service / Container Apps** | push the image or zip‑deploy; expose ports 8080/8081                                                                                                                                     |

Set `api.host` / `arcgis.host` in `config.yaml` to `"0.0.0.0"` (already
default) so FastAPI binds to all interfaces.

---

## 6  API usage

### 6.1 Data API (`:8080`)

| verb | endpoint                  | description                     |
| ---- | ------------------------- | ------------------------------- |
| GET  | `/dates`                  | list all Fire Map days on disk  |
| GET  | `/fires/<day>`            | full Fire Map JSON (RSS schema) |
| GET  | `/plume/<day>/<guid>.kml` | KML for *first* horizon (0.5 h) |
| GET  | `/meta/<day>/<guid>`      | dispersion + meteorology JSON   |

Example:

```bash
curl http://localhost:8080/fires/2025-05-11
```

### 6.2 ArcGIS API (`:8081`)

| endpoint | query params                   | what it returns                                                 |
| -------- | ------------------------------ | --------------------------------------------------------------- |
| `/layer` | `layer=fires` `day=YYYY‑MM‑DD` | point GeoJSON of fires                                          |
|          | `layer=plume` `day=YYYY‑MM‑DD` | list of KML URLs *(default)* or ESRI‑JSON ring (`fmt=esrijson`) |
|          | `layer=meta`  `day=YYYY‑MM‑DD` | array of attribute JSONs                                        |
|          | `layer=map`   `day=YYYY‑MM‑DD` | **FireSmokeMap\_\*.geojson** (3‑layer FeatureCollection)        |

#### Adding to ArcGIS Online / Pro

1. **Drag & drop**
   `data/geojson/FireSmokeMap_<date>.geojson` into your map
   *or* “Add Layer from URL” → type: **GeoJSON** →
   `http://<server>:8081/layer?layer=map&day=<date>`

2. Style by the **`layer`** attribute to toggle *incidents*, *plumes*,
   *meta* separately.

3. For older ArcGIS versions (≤10.4) that require EsriJSON, call:

```
http://<server>:8081/layer?layer=plume&day=<date>&fmt=esrijson
```

ArcGIS recognises the `esriGeometryPolygon` block automatically.

---

## 7  Customising & extending

### Edit parameters

*All tweaks live in `config.yaml`*:

```yaml
vsmoke:
  mix_height_ft: 2500   # change mixing height
  acres_default: 2      # default acreage
geojson:
  save_to_disk: false   # build on‑the‑fly only
```

### Add a new forecast horizon

1. Open `backend/simulators/smoke_simulator.py`.
2. Duplicate one `_single_horizon` call inside `process_firemap()`:

```python
"3.5h": _single_horizon(guid, lat, lon, "4", 210),
```

### 3‑D plumes

The metadata schema already reserves a sibling key (`"3d"`) next to each
horizon block—drop your volumetric model output there and surface it in
the APIs as a new `layer=volume`.

---

## 8  Troubleshooting

| symptom                                              | fix                                                                               |
| ---------------------------------------------------- | --------------------------------------------------------------------------------- |
| `ValueError: No polygon found …`                     | KML had only headers (tiny plume). Message is safe to ignore; horizon is skipped. |
| `VSmoke solver failed: … U < 0.1`                    | wind too calm – simulator clamps to **1 mph**; check `_wx_block()`.               |
| `ModuleNotFoundError: backend` inside `runvsmoke.py` | `PYTHONPATH` injection already handled; ensure you didn’t move the script.        |
| KML pretty‑print warning                             | install `lxml` (already in `requirements.txt`).                                   |

---


