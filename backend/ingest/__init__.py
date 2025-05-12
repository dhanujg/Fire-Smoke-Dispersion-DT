"""
Import‑side effect free; just surface the main entry point.
"""
from .fire_ingester import run as ingest_firemap

__all__ = ["ingest_firemap"]
