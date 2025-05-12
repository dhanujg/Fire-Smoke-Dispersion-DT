from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pathlib import Path
from backend.utils.paths import conf, INGEST_D, PLUMES_D, META_D
import json

app = FastAPI(title="FireSmoke Data API")

def latest(prefix: Path, pattern: str) -> Path:
    try:
        return max(prefix.glob(pattern))
    except ValueError:
        raise HTTPException(404, "No data")

@app.get("/dates")
def available_dates():
    return sorted({p.stem.split("_")[1] for p in INGEST_D.glob("FireMap_*.json")})

@app.get("/fires/{day}")
def fires(day: str = "latest"):
    fp = latest(INGEST_D, "FireMap_*.json") if day == "latest" else INGEST_D/f"FireMap_{day}.json"
    return JSONResponse(json.loads(fp.read_text()))

@app.get("/plume/{day}/{guid}.kml")
def plume(day: str, guid: str):
    kml_candidates = list(PLUMES_D.glob(f"{day}_{guid}_*.kml"))
    if not kml_candidates:
        raise HTTPException(404, "Plume not found")
    kml = kml_candidates[0]              # default: first horizon (0.5 h)
    return PlainTextResponse(
        kml.read_text(),
        media_type="application/vnd.google-earth.kml+xml"
    )

@app.get("/meta/{day}/{guid}")
def meta(day: str, guid: str):
    js = META_D / f"FireMap_{day}_{guid}.json"
    if not js.exists():
        raise HTTPException(404, "Metadata not found")
    return JSONResponse(json.loads(js.read_text()))
