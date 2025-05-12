"""
Combine incidents + plumes + dispersion metadata into ONE ArcGIS‑ready
GeoJSON FeatureCollection.

The output is flat but has a `layer` attribute so ArcGIS can filter /
symbolise each logical layer separately.

Layers
------
incidents : point  – title, description, pubDate
plumes    : polygon – title, horizon_type, geometry (ring from KML)
meta      : point  – horizon_type, acres … wdir

The helper honours conf.geojson.save_to_disk; when True the file is saved
to  <data_dir>/<output_subdir>/FireSmokeMap_<day>.geojson
"""
from __future__ import annotations
import json, datetime
from pathlib import Path, PurePosixPath
from typing import List, Dict, Any
import fastkml
from backend.utils.paths import (
    conf, INGEST_D, PLUMES_D, META_D,
    GEOJSON_D  # added in utils.paths, see §3
)

def _read_incidents(day: str) -> List[Dict[str, Any]]:
    fp = INGEST_D / f"FireMap_{day}.json"
    data = json.loads(fp.read_text())["rss"]["channel"]["item"]
    items = data if isinstance(data, list) else [data]

    feats = []
    for it in items:
        lat, lon = map(float, it["link"].split("q=")[1].split(","))
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "layer": "incidents",
                "guid":   it["guid"]["#text"],
                "title":  it["title"],
                "description": it.get("description", ""),
                "pubDate": it.get("pubDate", "")
            }
        })
    return feats


def _kml_ring(kml_path: Path) -> list | None:
    """
    Return an (lon,lat) outer ring list or None when the KML has *no*
    polygon geometry.

    • Works with fastkml 0.x (features() callable) and 1.x+ (features list)
    • Handles Polygon, MultiPolygon, and GeometryCollection.
    """
    import shapely.geometry as SG
    doc = fastkml.KML()
    doc.from_string(kml_path.read_bytes())

    def _children(o):
        feats = o.features if hasattr(o, "features") else ()
        return feats() if callable(feats) else list(feats)

    def _extract_ring(geom):
        """Return first polygon exterior coords from any geometry type."""
        if geom.geom_type == "Polygon":
            return list(geom.exterior.coords)
        if geom.geom_type == "MultiPolygon":
            return list(geom.geoms[0].exterior.coords)
        if geom.geom_type == "GeometryCollection":
            for g in geom.geoms:
                ring = _extract_ring(g)
                if ring:
                    return ring
        return None

    # breadth‑first search over the feature tree
    queue = _children(doc)
    while queue:
        feat = queue.pop(0)
        geom = getattr(feat, "geometry", None)
        if geom:
            ring = _extract_ring(geom)
            if ring:
                return ring
        queue.extend(_children(feat))

    # fallback: parse first <coordinates> manually
    import xml.etree.ElementTree as ET
    ns = {"k": "http://earth.google.com/kml/2.0"}
    root = ET.fromstring(kml_path.read_text())
    coord_el = root.find(".//k:LinearRing/k:coordinates", ns)
    if coord_el is None or not coord_el.text:
        return None
    pairs = [tuple(map(float, p.split(",")[:2]))
             for p in coord_el.text.strip().split()]
    return pairs if pairs else None




def _read_plumes_and_meta(day: str) -> (List[Dict[str, Any]], List[Dict[str, Any]]):
    plume_feats, meta_feats = [], []
    for mfp in META_D.glob(f"FireMap_{day}_*.json"):
        bundle = json.loads(mfp.read_text())
        lat, lon = bundle["lat"], bundle["lon"]
        title    = bundle["guid"]

        for label, hdict in bundle["horizons"].items():
            guid   = bundle["guid"]
            horizon = label        # "0.5h", "1.5h", "2.5h"
            # hdict["kml"] is stored as "data/plumes/<file>.kml"
            kml_rel = PurePosixPath(hdict["kml"])          # posix → Path‑like
            kml_abs = (conf.project_root / kml_rel).resolve()

            if not kml_abs.exists():                       # safety guard
                print("⚠︎  KML missing →", kml_abs)
                continue


            # plume polygon
            plume_feats.append({
                "type": "Feature",
                "geometry": {"type": "Polygon",
                             "coordinates": [_kml_ring(kml_abs)]},
                "properties": {
                    "layer": "plumes",
                    "guid": guid,
                    "title": title,
                    "horizon_type": horizon
                }
            })

            # meta point
            meta_props = {
                "layer": "meta",
                "guid": guid,
                "title": title,
                "horizon_type": horizon,
                **{k: hdict[k] for k in
                   ("acres", "mix", "stclass", "frise",
                    "horizon_min", "erate", "hrate", "wspd", "wdir")}
            }
            meta_feats.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": meta_props
            })
    return plume_feats, meta_feats


def build(day: str,
          save: bool | None = None) -> Dict[str, Any] | Path:
    """
    Parameters
    ----------
    day  : 'YYYY-MM-DD'
    save : override conf.geojson.save_to_disk if set

    Returns
    -------
    dict (GeoJSON) or Path to written file
    """
    if save is None:
        save = conf.geojson["save_to_disk"]

    features  = _read_incidents(day)
    plumes, meta = _read_plumes_and_meta(day)
    features.extend(plumes)
    features.extend(meta)

    gj = {
        "type": "FeatureCollection",
        "title": f"FireSmokeMap_{day}",
        "features": features
    }

    if save:
        GEOJSON_D.mkdir(parents=True, exist_ok=True)
        out = GEOJSON_D / f"FireSmokeMap_{day}.geojson"
        out.write_text(json.dumps(gj))
        return out
    return gj
