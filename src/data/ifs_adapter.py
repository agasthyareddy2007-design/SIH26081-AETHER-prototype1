import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import numpy as np
import pandas as pd
import xarray as xr

from .base_adapter import BaseDataAdapter
from .openmeteo_client import get_open_meteo_client

class IFSAdapter(BaseDataAdapter):
    """
    Adapter for ECMWF IFS Forecasts via Open-Meteo API.
    """
    def __init__(self, cache_dir: Path, **kwargs):
        super().__init__(source_name="IFS", cache_dir=cache_dir, **kwargs)
        self.om_client = get_open_meteo_client(self.cache_dir / "om_cache")

    def fetch_forecast(
        self,
        init_time: datetime,
        variables: List[str],
        lat_range: tuple,
        lon_range: tuple,
        lead_times_hours: List[int],
    ) -> xr.Dataset:
        """
        Fetch IFS forecast data from Open-Meteo.
        """
        identifier = f"IFS_REAL_{init_time.isoformat()}_{variables}_{lat_range}_{lon_range}_{lead_times_hours}"
        cached = self._load_from_cache(identifier)
        if cached is not None:
            return cached

        self.logger.info(f"Fetching real IFS forecast for {init_time}")
        
        # Calculate validity times
        valid_times = [init_time + timedelta(hours=lt) for lt in lead_times_hours]
        start_date = min(valid_times).strftime('%Y-%m-%d')
        end_date = max(valid_times).strftime('%Y-%m-%d')
        
        # We query the center of the lat/lon range for simplicity, or 5x5 grid
        lats = np.linspace(lat_range[0], lat_range[1], 5)
        lons = np.linspace(lon_range[0], lon_range[1], 5)
        
        # The Open-Meteo API accepts comma-separated lats and lons (up to 100 locations)
        # We will flatten the 5x5 grid into a 25-element list
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
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "temperature_2m",  # Only temperature for now based on V1
            "models": "ecmwf_ifs025"
        }
        
        url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
        
        # The _retry_download logic in BaseDataAdapter uses a callable. 
        # We'll just call our fetch method here as it handles its own retries natively.
        results = self.om_client.fetch(url, params)
        
        # Results is a list of 25 dicts because we passed 25 locations
        if not isinstance(results, list):
            results = [results] # fallback in case of single result
            
        # Parse into xarray
        shape = (len(valid_times), len(lats), len(lons))
        temp_data = np.zeros(shape)
        
        for idx in range(25):
            r = results[idx]
            lat_idx = idx // 5
            lon_idx = idx % 5
            
            # Extract hourly data
            hourly = r.get("hourly", {})
            times_str = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            
            # Map values to valid_times
            for t_idx, vt in enumerate(valid_times):
                vt_str = vt.strftime('%Y-%m-%dT%H:00')
                try:
                    time_index = times_str.index(vt_str)
                    val = temps[time_index]
                    temp_data[t_idx, lat_idx, lon_idx] = val if val is not None else np.nan
                except ValueError:
                    temp_data[t_idx, lat_idx, lon_idx] = np.nan
                    
        data_vars = {'t2m': (['time', 'latitude', 'longitude'], temp_data)}
        
        ds = xr.Dataset(
            data_vars=data_vars,
            coords={
                'time': valid_times,
                'latitude': lats,
                'longitude': lons,
                'initialization_time': init_time,
            },
            attrs={
                'description': 'Real IFS Forecast from Open-Meteo',
                'lead_times_hours': lead_times_hours,
            }
        )

        if not self._validate_dataset(ds):
            raise ValueError("Dataset validation failed (NaNs in array?)")

        ds = self._add_source_metadata(ds)
        self._save_to_cache(ds, identifier)
        return ds

    def fetch_reference(self, valid_time, variables, lat_range, lon_range):
        raise NotImplementedError("Use ERA5Adapter for reference data.")
