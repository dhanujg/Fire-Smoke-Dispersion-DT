"""
Utility that

1. Loads `config.yaml`
2. Expands environment variables like  ${HOME}
3. Converts any node tagged with !!path (absolute only) into `pathlib.Path`
4. Exposes a frozen `FSConfig` dataclass + four convenience Path objects.

All other modules import *only* from this file, never from `yaml` directly
→ a single point of maintenance when new parameters are added.
"""
from __future__ import annotations
import os, yaml
from dataclasses import dataclass
from pathlib import Path

@dataclass(slots=True, frozen=True)
class FSConfig:
    project_root: Path
    data_dir:     Path
    ingest:       dict
    vsmoke:       dict
    api:          dict
    arcgis:       dict
    geojson:      dict

def _expand(val: str) -> str:
    "Expand ${VAR} and ~ consistently on every platform."
    return os.path.expanduser(os.path.expandvars(val))

# ------------------------------------------------------------------
# Better path detection: also catch "C:/..." and "C:\..." on Windows
# ------------------------------------------------------------------
import re
from pathlib import Path
import os, yaml

ABS_WIN = re.compile(r"^[A-Za-z]:[\\/].*")   # e.g. C:\ or D:/

def _looks_like_path(val: str) -> bool:
    return val.startswith("/") or ABS_WIN.match(val)

def load_config(cfg_path: str | Path = None) -> FSConfig:
    """
    Parse YAML then cast any top‑level value that *looks* like an absolute
    path (Unix or Windows drive letter) into pathlib.Path.
    Environment variables are expanded beforehand.
    """
    cfg_path = Path(cfg_path or __file__).parents[2] / "config.yaml"
    text = os.path.expandvars(Path(cfg_path).read_text())
    cfg  = yaml.safe_load(text)

    for k, v in cfg.items():
        if isinstance(v, str) and _looks_like_path(v):
            cfg[k] = Path(v)

    # also promote nested vsmoke.exe to Path for consistency
    if _looks_like_path(cfg["vsmoke"]["exe"]):
        cfg["vsmoke"]["exe"] = str(Path(cfg["vsmoke"]["exe"]))

    return FSConfig(**cfg)

# ── Instantiate and materialise the folders once at import time ────────────
conf    = load_config()
DATA_D  = conf.data_dir
INGEST_D = DATA_D/conf.ingest["output_subdir"]
PLUMES_D = DATA_D/conf.vsmoke["output_subdir"]
META_D   = DATA_D/conf.vsmoke["meta_subdir"]
GEOJSON_D = DATA_D / conf.geojson["output_subdir"]

for d in (DATA_D, INGEST_D, PLUMES_D, META_D, GEOJSON_D):
    d.mkdir(parents=True, exist_ok=True)
