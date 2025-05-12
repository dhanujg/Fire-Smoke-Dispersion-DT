"""
Expose the resolved config and folders so downstream code can do:

    from backend.utils import conf, PLUMES_D
"""
from .paths import conf, DATA_D, INGEST_D, PLUMES_D, META_D

__all__ = ["conf", "DATA_D", "INGEST_D", "PLUMES_D", "META_D", "GEOJSON_D"]
