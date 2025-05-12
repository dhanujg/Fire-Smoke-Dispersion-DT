"""
backend/ingest/weather.py
=========================

NOAA National Weather Service (NWS) “Points” API helper
-------------------------------------------------------

• Resolve a lat/lon into the nearest forecast grid (`/points/{lat},{lon}`)
• Download the *hourly* forecast JSON for that grid
• Return the first forecast entry whose `startTime` ≥ **now** (local)
  as a **flat dict** with *only* the two keys the simulator needs::

      {
          "windSpeed": "4 mph",
          "windDirection": "S"
      }

All parameters such as timeouts and User‑Agent are defined at the top for
easy tweaking.
"""
from __future__ import annotations
import datetime as _dt
import logging
import requests

#: REST endpoints -----------------------------------------------------------
ROOT_POINTS = "https://api.weather.gov/points/{lat},{lon}"

#: Requests setup -----------------------------------------------------------
TIMEOUT = 10        # seconds for every HTTP request
HEADERS = {
    "User-Agent": (
        "firesmoke-digital-twin (your.email@example.com)"
    ),
    "Accept": "application/ld+json"
}

_log = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)


# ────────────────────────────────────────────────────────────────────────────
def _ensure_ok(resp: requests.Response):
    """Raise for non‑2xx with a readable message."""
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        # NOAA often returns extra detail in JSON → include it
        try:
            detail = resp.json().get("detail", "")
        except Exception:       # noqa: BLE001
            detail = ""
        raise RuntimeError(f"NWS Points API error {resp.status_code}: {detail}") from exc


def _get_json(url: str) -> dict:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    _ensure_ok(resp)
    return resp.json()


# ────────────────────────────────────────────────────────────────────────────
def get_hourly_wx(lat: float, lon: float) -> dict:
    """
    Parameters
    ----------
    lat, lon : float
        Decimal degrees (WGS‑84) – e.g. 30.27, ‑97.73 for Austin.

    Returns
    -------
    dict with two keys:
        • windSpeed     – text, e.g. "4 mph"
        • windDirection – compass string "S", "SW" etc.

    Raises
    ------
    RuntimeError on network / API errors.
    """
    # 1) Resolve the forecast office + gridpoint
    meta = _get_json(ROOT_POINTS.format(lat=lat, lon=lon))

    if "properties" not in meta or "forecastHourly" not in meta["properties"]:
        _log.warning(
            "NWS Points API returned error payload for %.4f,%.4f – using calm wind.",
            lat, lon
        )
        return {"windSpeed": "0 mph", "windDirection": "N"}
    
    hourly_url = meta["properties"]["forecastHourly"]

    # 2) Pull the hourly forecast
    hourly = _get_json(hourly_url)
    periods = hourly["properties"]["periods"]
    if not periods:
        raise RuntimeError("Empty hourly forecast from NWS")

    # 3) Find the first forecast *not in the past*
    now = _dt.datetime.utcnow().replace(tzinfo=_dt.timezone.utc)
    for p in periods:
        start = _dt.datetime.fromisoformat(p["startTime"])
        if start >= now:
            return {
                "windSpeed":     p["windSpeed"],
                "windDirection": p["windDirection"],
            }

    # Fallback – return the last item if everything else was in the past
    _log.warning("All forecast periods appear to be in the past; using last entry.")
        # ── NORMALISE VALUES ────────────────────────────────────────────────
    speed_txt = p["windSpeed"].split()[0]          # "4", "Calm", "10"
    wind_speed = f"{speed_txt} mph" if speed_txt.isdigit() else "0 mph"

    wind_dir = p["windDirection"]
    if wind_dir not in (
        "N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW".split()
    ):
        wind_dir = "N"
    # -------------------------------------------------------------------

    return {
        "windSpeed":     wind_speed,
        "windDirection": wind_dir,
    }
    # return {
    #     "windSpeed":     periods[-1]["windSpeed"],
    #     "windDirection": periods[-1]["windDirection"],
    # }


if __name__ == "__main__":           # quick CLI check
    import sys, json
    lat, lon = (float(x) for x in sys.argv[1:3])
    print(json.dumps(get_hourly_wx(lat, lon), indent=2))
