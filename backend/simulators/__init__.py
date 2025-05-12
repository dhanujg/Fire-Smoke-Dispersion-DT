"""
Simulation drivers.

• smoke_simulator.process_firemap(...)   – 2‑D VSmoke (three horizons)
• placeholder3d.generate(...)           – reserved for future volume model
"""
from .smoke_simulator import process_firemap as simulate_plumes

__all__ = ["simulate_plumes"]
