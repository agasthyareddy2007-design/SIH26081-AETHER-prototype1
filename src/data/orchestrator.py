"""
Data Ingestion Orchestrator
Coordinates multi-source forecast data collection
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

import pandas as pd
import xarray as xr

from src.data import IFSAdapter, ICONAdapter, GFSAdapter, ERA5Adapter


class DataOrchestrator:
    """
    Orchestrates data ingestion from multiple forecast sources.

    Manages:
    - Parallel data fetching from IFS, ICON, GFS
    - ERA5 reference data retrieval
    - Temporal alignment
    - Data validation
    - Metadata preservation
    """

    def __init__(self, config: Dict, cache_dir: Path):
        self.config = config
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize adapters
        self.ifs = IFSAdapter(cache_dir / "ifs")
        self.icon = ICONAdapter(cache_dir / "icon")
        self.gfs = GFSAdapter(cache_dir / "gfs")
        self.era5 = ERA5Adapter(cache_dir / "era5")

        self.logger = logging.getLogger("aether.data.orchestrator")

    def fetch_multi_model_forecast(
        self,
        init_time: datetime,
        variables: List[str],
        lat_range: tuple,
        lon_range: tuple,
        lead_times_hours: List[int],
    ) -> Dict[str, xr.Dataset]:
        """
        Fetch forecasts from all enabled sources.

        Returns:
            Dict mapping source name to forecast dataset
        """
        forecasts = {}

        if self.config.get("sources", {}).get("ifs", {}).get("enabled", True):
            self.logger.info("Fetching IFS forecast...")
            forecasts["IFS"] = self.ifs.fetch_forecast(
                init_time, variables, lat_range, lon_range, lead_times_hours
            )

        if self.config.get("sources", {}).get("icon", {}).get("enabled", True):
            self.logger.info("Fetching ICON forecast...")
            forecasts["ICON"] = self.icon.fetch_forecast(
                init_time, variables, lat_range, lon_range, lead_times_hours
            )

        if self.config.get("sources", {}).get("gfs", {}).get("enabled", True):
            self.logger.info("Fetching GFS forecast...")
            forecasts["GFS"] = self.gfs.fetch_forecast(
                init_time, variables, lat_range, lon_range, lead_times_hours
            )

        return forecasts

    def fetch_references_for_forecasts(
        self,
        init_time: datetime,
        variables: List[str],
        lat_range: tuple,
        lon_range: tuple,
        lead_times_hours: List[int],
    ) -> Dict[int, xr.Dataset]:
        """
        Fetch ERA5 reference data for all valid times.

        Returns:
            Dict mapping lead_time to ERA5 reference dataset
        """
        references = {}

        for lead_time in lead_times_hours:
            valid_time = init_time + timedelta(hours=lead_time)
            self.logger.info(f"Fetching ERA5 reference for +{lead_time}h (valid: {valid_time})")

            references[lead_time] = self.era5.fetch_reference(
                valid_time, variables, lat_range, lon_range
            )

        return references

    def create_aligned_dataset(
        self,
        init_time: datetime,
        variables: List[str],
        lat_range: tuple,
        lon_range: tuple,
        lead_times_hours: List[int],
    ) -> pd.DataFrame:
        """
        Create fully aligned dataset with forecasts and references.

        Returns:
            DataFrame with columns:
            - source
            - variable
            - initialization_time
            - valid_time
            - lead_time
            - latitude
            - longitude
            - forecast_value
            - reference_value
        """
        forecasts = self.fetch_multi_model_forecast(
            init_time, variables, lat_range, lon_range, lead_times_hours
        )

        references = self.fetch_references_for_forecasts(
            init_time, variables, lat_range, lon_range, lead_times_hours
        )

        records = []

        for source_name, forecast_ds in forecasts.items():
            for lead_time in lead_times_hours:
                valid_time = init_time + timedelta(hours=lead_time)

                # Extract forecast values
                forecast_values = forecast_ds['t2m'].sel(
                    time=valid_time, method='nearest'
                ).values

                # Extract reference values (squeeze time dimension)
                ref_ds = references[lead_time]
                ref_values = ref_ds['t2m'].squeeze().values

                # Create records for each grid point
                lats = forecast_ds.latitude.values
                lons = forecast_ds.longitude.values

                for i, lat in enumerate(lats):
                    for j, lon in enumerate(lons):
                        records.append({
                            'source': source_name,
                            'variable': '2m_temperature',
                            'initialization_time': init_time,
                            'valid_time': valid_time,
                            'lead_time': lead_time,
                            'latitude': lat,
                            'longitude': lon,
                            'forecast_value': forecast_values[i, j],
                            'reference_value': ref_values[i, j],
                        })

        df = pd.DataFrame(records)
        return df
