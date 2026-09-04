"""
AETHER Data Ingestion Module
Phase 1 — Multi-source weather forecast data ingestion
"""

from .base_adapter import BaseDataAdapter
from .ifs_adapter import IFSAdapter
from .icon_adapter import ICONAdapter
from .gfs_adapter import GFSAdapter
from .era5_adapter import ERA5Adapter

__all__ = [
    "BaseDataAdapter",
    "IFSAdapter",
    "ICONAdapter",
    "GFSAdapter",
    "ERA5Adapter",
]
