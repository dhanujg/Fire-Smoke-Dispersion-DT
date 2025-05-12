"""
firesmoke – Austin fire‑and‑smoke digital‑twin toolkit
------------------------------------------------------

Public re‑exports
-----------------
>>> from firesmoke import conf, ingest_firemap, simulate_plumes
"""
from importlib import import_module

# Central config adapter (one object, shared everywhere)
conf = import_module("backend.utils.paths").conf

# Convenience call‑throughs so users can write::
#     from firesmoke import ingest_firemap
ingest_firemap = import_module("backend.ingest.fire_ingester").run
simulate_plumes = import_module("backend.simulators.smoke_simulator").process_firemap

__all__ = ["conf", "ingest_firemap", "simulate_plumes"]
__version__ = "0.1.0"
