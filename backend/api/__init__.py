"""
Expose the FastAPI apps so uvicorn can import quickly:

    uvicorn backend.api.data_api:app
    uvicorn backend.api.arcgis_api:app
"""
from .data_api import app as data_app
from .arcgis_api import app as arcgis_app

__all__ = ["data_app", "arcgis_app"]
