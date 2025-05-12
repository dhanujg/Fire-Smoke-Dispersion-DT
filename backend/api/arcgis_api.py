"""
ArcGIS Layer API
================

Serves layers that ArcGIS Online / Pro can consume directly.

New feature: `to_esrijson()` converts any GeoJSON Polygon/MultiPolygon
into the ESRI JSON dialect (ArcGIS ≤10.4 requires it).

Query parameters
----------------
day   : YYYY-MM-DD | latest
layer : fires | plume | meta
fmt   : geojson (default) | esrijson    ← only affects polygon layer
"""
from __future__ import annotations
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from backend.utils.paths import INGEST_D, PLUMES_D, META_D, conf
from pathlib import Path, PurePosixPath
from backend.api.transform_to_geojson import build as build_gj


app = FastAPI(title="ArcGIS Layer API")

# ── Helper to pick latest file if "latest" requested ───────────────────────
def _pick_latest(folder: Path, suffix: str, day: str) -> Path:
    """
    For suffix '.json' this expects files like 'FireMap_<date>.json'.
    For other suffixes (e.g. '_*.kml') it simply forwards the pattern.
    """
    if day == "latest":
        try:
            return max(folder.glob(f"*{suffix}"))
        except ValueError:
            raise HTTPException(404, "No data")

    if suffix == ".json":
        return folder / f"FireMap_{day}{suffix}"

    return folder / f"{day}{suffix}"


# ── GeoJSON → ESRI JSON converter (simple, polygon‑only) ───────────────────
def to_esrijson(geo: dict) -> dict:
    """
    ArcGIS *EsriJSON* spec uses:
      • 'rings' instead of 'coordinates'
      • Y‑first order (lat,lon)
      • spatialReference.wkid (4326 = WGS84)

    Only Polygon & MultiPolygon are needed for plume rings.
    """
    if geo["type"] == "Polygon":
        rings = [[[y, x] for x, y in ring] for ring in geo["coordinates"]]
    elif geo["type"] == "MultiPolygon":
        rings = [[[y, x] for x, y in pt] for poly in geo["coordinates"] for pt in poly]
    else:
        raise ValueError("Only polygons supported")

    return {
        "geometryType": "esriGeometryPolygon",
        "spatialReference": {"wkid": 4326},
        "features": [{"geometry": {"rings": rings}, "attributes": {}}]
    }

# ── Endpoints ──────────────────────────────────────────────────────────────
@app.get("/layer")
def layer(
    day:   str = Query("latest"),
    layer: str = Query(...),
    fmt:   str = Query("geojson")
):

    if layer == "fires":
        fp   = _pick_latest(INGEST_D, ".json", day)
        data = json.loads(fp.read_text())["rss"]["channel"]["item"]
        items = data if isinstance(data, list) else [data]

        features = [{
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    float(it["link"].split(",")[1]),   # lon
                    float(it["link"].split(",")[0].split("q=")[1])  # lat
                ]},
            "properties": {
                "title": it["title"],
                "guid":  it["guid"]["#text"]
            }
        } for it in items]

        return JSONResponse({"type": "FeatureCollection", "features": features})

    elif layer == "plume":
        # Build *virtual* FeatureCollection of KML URLs (ArcGIS < 10.7
        # authenticates KML as geo service on the fly)
        kmls = sorted(PLUMES_D.glob(f"{day}_*.kml"))
        if not kmls:
            raise HTTPException(404, "No plumes for that day")

        if fmt.lower() == "geojson":
            # Serve list of URLs; client picks
            urls = [str(PurePosixPath(p.relative_to(conf.project_root))) for p in kmls]
            return JSONResponse({"kml_layers": urls})
        
        # NOTE: only the *first* placemark of the first KML is converted.
        # Extend this loop if you need every ring.
        if fmt.lower() == "esrijson":
            # Read one KML ➜ convert rings ➜ return (demo purposes)
            # For prod you might parse every KML and merge; omitted for brevity
            import fastkml
            doc = fastkml.KML()
            doc.from_string(kmls[0].read_bytes())
            geom = list(doc.features())[0].geometry  # first placemark
            gj = geom.__geo_interface__
            return JSONResponse(to_esrijson(gj))

        raise HTTPException(400, "fmt must be geojson or esrijson")

    elif layer == "meta":
        metas = [json.loads(p.read_text()) for p in META_D.glob(f"FireMap_{day}_*.json")]
        if not metas:
            raise HTTPException(404, "No metadata for that day")
        return JSONResponse(metas)
    # ------------------------------------------------------------------
    # Fire‑Smoke map (all layers in one FeatureCollection)
    # ------------------------------------------------------------------
    elif layer == "map":
        gj = build_gj(day, save=False)   # always build on‑the‑fly here
        return JSONResponse(gj)

    raise HTTPException(400, "Unknown layer type")
