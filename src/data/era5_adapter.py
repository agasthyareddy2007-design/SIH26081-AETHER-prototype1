import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import numpy as np
import pandas as pd
import xarray as xr

from .base_adapter import BaseDataAdapter
from .openmeteo_client import get_open_meteo_client

class ERA5Adapter(BaseDataAdapter):
    """
    Adapter for ERA5-Land Reanalysis Data via Open-Meteo Archive API.
    """
    def __init__(self, cache_dir: Path, **kwargs):
        super().__init__(source_name="ERA5", cache_dir=cache_dir, **kwargs)
        self.om_client = get_open_meteo_client(self.cache_dir / "om_cache")

    def fetch_forecast(self, init_time, variables, lat_range, lon_range, lead_times_hours):
        raise NotImplementedError("Use fetch_reference for ERA5 data.")

    def fetch_reference(
        self,
        valid_time: datetime,
        variables: List[str],
        lat_range: tuple,
        lon_range: tuple,
    ) -> xr.Dataset:
        """
        Fetch ERA5-Land reference data from Open-Meteo Archive.
        """
        identifier = f"ERA5Land_REAL_{valid_time.isoformat()}_{variables}_{lat_range}_{lon_range}"
        cached = self._load_from_cache(identifier)
        if cached is not None:
            return cached

        self.logger.info(f"Fetching real ERA5-Land reference for {valid_time}")
        
        date_str = valid_time.strftime('%Y-%m-%d')
        
        # Grid
        lats = np.linspace(lat_range[0], lat_range[1], 5)
        lons = np.linspace(lon_range[0], lon_range[1], 5)
        
        lat_list = []
        lon_list = []
        for lat in lats:
            for lon in lons:
                lat_list.append(round(lat, 4))
                lon_list.append(round(lon, 4))
                
        # Parameters
        params = {
            "latitude": ",".join(map(str, lat_list)),
            "longitude": ",".join(map(str, lon_list)),
            "start_date": date_str,
            "end_date": date_str,
            "hourly": "temperature_2m",
            "models": "era5_land"
        }
        
        url = "https://archive-api.open-meteo.com/v1/archive"
        
        results = self.om_client.fetch(url, params)
        if not isinstance(results, list):
            results = [results]
            
        shape = (1, len(lats), len(lons))
        temp_data = np.zeros(shape)
        
        vt_str = valid_time.strftime('%Y-%m-%dT%H:00')
        
        for idx in range(25):
            r = results[idx]
            lat_idx = idx // 5
            lon_idx = idx % 5
            
            hourly = r.get("hourly", {})
            times_str = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            
            try:
                time_index = times_str.index(vt_str)
                val = temps[time_index]
                temp_data[0, lat_idx, lon_idx] = val if val is not None else np.nan
            except ValueError:
                temp_data[0, lat_idx, lon_idx] = np.nan
                    
        data_vars = {'t2m': (['time', 'latitude', 'longitude'], temp_data)}
        
        ds = xr.Dataset(
            data_vars=data_vars,
            coords={
                'time': [valid_time],
                'latitude': lats,
                'longitude': lons,
            },
            attrs={
                'description': 'Real ERA5-Land Data from Open-Meteo',
                'valid_time': valid_time.isoformat(),
            }
        )

        if not self._validate_dataset(ds):
            # Try to print for debugging
            logger = logging.getLogger("aether.openmeteo")
            logger.warning(f"ERA5 dataset validation failed for {valid_time}")
            raise ValueError("Dataset validation failed (NaNs in array?)")

        ds = self._add_source_metadata(ds)
        self._save_to_cache(ds, identifier)
        return ds
