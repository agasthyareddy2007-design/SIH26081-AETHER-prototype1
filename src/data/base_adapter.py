"""
Base Data Adapter
Abstract interface for all forecast data sources
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import time
import hashlib
import json

import xarray as xr
import pandas as pd


class BaseDataAdapter(ABC):
    """
    Abstract base class for forecast data source adapters.

    All adapters (IFS, ICON, GFS, ERA5) must implement this interface.
    Provides common functionality for:
    - Download retry logic
    - File validation
    - Caching
    - Metadata preservation
    - Source identity tracking
    """

    def __init__(
        self,
        source_name: str,
        cache_dir: Path,
        max_retries: int = 15,
        retry_delay: float = 10.0,
        timeout: int = 300,
    ):
        self.source_name = source_name
        self.cache_dir = Path(cache_dir)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(f"aether.data.{source_name.lower()}")

    @abstractmethod
    def fetch_forecast(
        self,
        init_time: datetime,
        variables: List[str],
        lat_range: tuple,
        lon_range: tuple,
        lead_times_hours: List[int],
    ) -> xr.Dataset:
        """
        Fetch forecast data from the source.

        Args:
            init_time: Forecast initialization time (UTC)
            variables: List of variables to fetch (e.g., ['2m_temperature'])
            lat_range: (min_lat, max_lat)
            lon_range: (min_lon, max_lon)
            lead_times_hours: List of forecast lead times in hours

        Returns:
            xarray.Dataset with forecast data and metadata
        """
        pass

    @abstractmethod
    def fetch_reference(
        self,
        valid_time: datetime,
        variables: List[str],
        lat_range: tuple,
        lon_range: tuple,
    ) -> xr.Dataset:
        """
        Fetch verification/reference data (for ERA5).

        Args:
            valid_time: Valid time for verification (UTC)
            variables: List of variables
            lat_range: (min_lat, max_lat)
            lon_range: (min_lon, max_lon)

        Returns:
            xarray.Dataset with reference data
        """
        pass

    def _get_cache_path(self, identifier: str) -> Path:
        """Generate cache file path from identifier"""
        hash_key = hashlib.md5(identifier.encode()).hexdigest()
        return self.cache_dir / f"{self.source_name}_{hash_key}.nc"

    def _is_cached(self, identifier: str) -> bool:
        """Check if data is already cached"""
        cache_path = self._get_cache_path(identifier)
        return cache_path.exists()

    def _load_from_cache(self, identifier: str) -> Optional[xr.Dataset]:
        """Load data from cache if available"""
        if not self._is_cached(identifier):
            return None

        cache_path = self._get_cache_path(identifier)
        try:
            self.logger.info(f"Loading from cache: {cache_path.name}")
            ds = xr.open_dataset(cache_path)
            return ds
        except Exception as e:
            self.logger.warning(f"Cache read failed: {e}")
            return None

    def _save_to_cache(self, data: xr.Dataset, identifier: str) -> None:
        """Save data to cache"""
        cache_path = self._get_cache_path(identifier)
        try:
            data.to_netcdf(cache_path)
            self.logger.info(f"Saved to cache: {cache_path.name}")
        except Exception as e:
            self.logger.error(f"Cache write failed: {e}")

    def _retry_download(self, download_func, *args, **kwargs) -> Any:
        """Execute download function with retry logic"""
        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(f"Download attempt {attempt}/{self.max_retries}")
                result = download_func(*args, **kwargs)
                return result
            except Exception as e:
                self.logger.warning(f"Attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error(f"All {self.max_retries} attempts failed")
                    raise

    def _validate_dataset(self, ds: xr.Dataset) -> bool:
        """
        Validate downloaded dataset.

        Checks:
        - Required dimensions exist
        - No entirely NaN variables
        - Reasonable coordinate ranges
        """
        required_dims = {'latitude', 'longitude', 'time'}

        if not required_dims.issubset(set(ds.dims)):
            self.logger.error(f"Missing required dimensions: {required_dims - set(ds.dims)}")
            return False

        # Check for completely NaN variables
        for var in ds.data_vars:
            if ds[var].isnull().all():
                self.logger.warning(f"Variable {var} is entirely NaN")
                return False

        # Check coordinate ranges
        if 'latitude' in ds.coords:
            lat_range = (float(ds.latitude.min()), float(ds.latitude.max()))
            if not (-90 <= lat_range[0] <= 90 and -90 <= lat_range[1] <= 90):
                self.logger.error(f"Invalid latitude range: {lat_range}")
                return False

        if 'longitude' in ds.coords:
            lon_range = (float(ds.longitude.min()), float(ds.longitude.max()))
            if not (-180 <= lon_range[0] <= 360 and -180 <= lon_range[1] <= 360):
                self.logger.error(f"Invalid longitude range: {lon_range}")
                return False

        self.logger.info("Dataset validation passed")
        return True

    def _add_source_metadata(self, ds: xr.Dataset) -> xr.Dataset:
        """Add source identification metadata to dataset"""
        ds.attrs['source'] = self.source_name
        ds.attrs['ingestion_time'] = datetime.utcnow().isoformat()
        return ds

    def get_metadata(self, identifier: str) -> Optional[Dict]:
        """Retrieve metadata for a cached dataset"""
        cache_path = self._get_cache_path(identifier)
        metadata_path = cache_path.with_suffix('.json')

        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                return json.load(f)
        return None

    def save_metadata(self, identifier: str, metadata: Dict) -> None:
        """Save metadata alongside cached dataset"""
        cache_path = self._get_cache_path(identifier)
        metadata_path = cache_path.with_suffix('.json')

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
