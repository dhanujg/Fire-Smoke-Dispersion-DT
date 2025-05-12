"""
Fire Incident Ingester
----------------------

Pulls the Austin Fire Department RSS feed, converts XML ➜ JSON
and stores *one* file per calendar day:

    data/ingested_fire_incident_maps/FireMap_<YYYY-MM-DD>.json

Behaviour
~~~~~~~~~
• If the target date is **today**, the file is overwritten (fresh snapshot).  
• If the date is **in the past** and a file already exists, nothing is re‑fetched
  (keeps bandwidth low and preserves any manual edits).

The JSON schema exactly matches the original legacy code so downstream
parsers remain unchanged.
"""
from __future__ import annotations
from datetime import datetime
import json, requests, xmltodict
from pathlib import Path
from backend.utils.paths import conf, INGEST_D

def _fetch_rss() -> dict:
    resp = requests.get(conf.ingest["rss_url"], timeout=30)
    resp.raise_for_status()
    return xmltodict.parse(resp.text)

def _target(day: datetime) -> Path:
    return INGEST_D / f"FireMap_{day.date()}.json"

def run(day_str: str | None = None) -> Path:
    """
    Parameters
    ----------
    day_str : str | None
        • "2025-05-11" ➜ archive fetch  
        • None        ➜ today

    Returns
    -------
    Path to the JSON file written/used.
    """
    day  = datetime.strptime(day_str, "%Y-%m-%d") if day_str else datetime.now()
    out  = _target(day)

    # Skip fetch if archive already on disk
    if out.exists() and day.date() != datetime.now().date():
        return out

    rss_json = _fetch_rss()
    out.write_text(json.dumps(rss_json, indent=2))
    return out

if __name__ == "__main__":
    run()  # python fire_ingester.py ➜ today
