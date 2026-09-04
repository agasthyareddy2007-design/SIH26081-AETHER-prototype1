#!/usr/bin/env python3
"""
Efficient bulk training data builder for AETHER.

Strategy: Fetch the entire date range per model in a SINGLE API call per location,
avoiding the N_init_times × N_models × N_grid_points explosion that causes 429s.

For each (model, location) pair, we make ONE request covering the full date range.
Then we align the data offline without any additional API calls.

Models:
  - IFS:  ecmwf_ifs025   (Historical Forecast API)
  - GFS:  gfs_seamless    (Historical Forecast API)
  - ICON: icon_seamless   (Historical Forecast API)
  - ERA5-Land: era5_land  (Archive API) — INDEPENDENT ground truth target
"""

import sys
import time
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / 'logs' / f'bulk_fetch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("aether.bulk_fetch")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
START_DATE = "2025-09-03"
END_DATE   = "2026-09-03"

# Hyderabad region — use a 3×3 grid (9 points) instead of 5×5 (25) to be gentler
LAT_RANGE = (16.8, 17.8)
LON_RANGE = (78.0, 79.0)
GRID_SIZE = 3  # 3×3 = 9 API calls per model

LEAD_TIMES = [6, 12, 24]  # hours

FORECAST_MODELS = [
    ("IFS",  "ecmwf_ifs025", "https://historical-forecast-api.open-meteo.com/v1/forecast"),
    ("GFS",  "gfs_seamless",  "https://historical-forecast-api.open-meteo.com/v1/forecast"),
    ("ICON", "icon_seamless", "https://historical-forecast-api.open-meteo.com/v1/forecast"),
]

ERA5_CONFIG = ("ERA5", "era5_land", "https://archive-api.open-meteo.com/v1/archive")

CACHE_DIR = PROJECT_ROOT / "data" / "raw" / "bulk_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# HTTP session with retry
# ---------------------------------------------------------------------------
def make_session():
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    s.mount('https://', HTTPAdapter(max_retries=retries))
    return s

SESSION = make_session()

def cached_fetch(url, params, label=""):
    """Fetch with JSON file cache and inter-request delay."""
    key = url + json.dumps(params, sort_keys=True)
    h = hashlib.md5(key.encode()).hexdigest()
    cache_path = CACHE_DIR / f"{h}.json"

    if cache_path.exists():
        logger.info(f"  [CACHE HIT] {label}")
        with open(cache_path, 'r') as f:
            return json.load(f)

    logger.info(f"  [API CALL]  {label}  →  {url}")
    resp = SESSION.get(url, params=params, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    with open(cache_path, 'w') as f:
        json.dump(data, f)

    # Polite delay to stay under rate limits
    time.sleep(1.5)
    return data

# ---------------------------------------------------------------------------
# Fetch full time series for one model at one location
# ---------------------------------------------------------------------------
def fetch_model_timeseries(model_name, model_slug, endpoint, lat, lon):
    """
    Fetch the full hourly temperature_2m for a single model at a single point,
    covering START_DATE to END_DATE in one API call.

    Returns dict: { "YYYY-MM-DDTHH:00": temp_value, ... }
    """
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": "temperature_2m",
    }
    # For forecast models, specify the model slug
    if model_slug != "era5_land":
        params["models"] = model_slug
    else:
        params["models"] = "era5_land"

    label = f"{model_name} lat={lat:.2f} lon={lon:.2f}"
    data = cached_fetch(endpoint, params, label)

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])

    ts = {}
    for t, v in zip(times, temps):
        if v is not None:
            ts[t] = v
    return ts

# ---------------------------------------------------------------------------
# Build the full aligned dataset
# ---------------------------------------------------------------------------
def build_dataset():
    lats = np.linspace(LAT_RANGE[0], LAT_RANGE[1], GRID_SIZE)
    lons = np.linspace(LON_RANGE[0], LON_RANGE[1], GRID_SIZE)

    logger.info("=" * 80)
    logger.info("AETHER BULK DATA BUILDER — REAL OPEN-METEO DATA")
    logger.info(f"Date range: {START_DATE} to {END_DATE}")
    logger.info(f"Grid: {GRID_SIZE}×{GRID_SIZE} = {GRID_SIZE**2} points")
    logger.info(f"Models: {[m[0] for m in FORECAST_MODELS]} + ERA5-Land")
    logger.info("=" * 80)

    # -----------------------------------------------------------------------
    # Step 1: Fetch all raw time series
    # -----------------------------------------------------------------------
    # Structure: raw[model_name][(lat, lon)] = { "YYYY-MM-DDTHH:00": temp, ... }
    raw = {}

    for model_name, slug, endpoint in FORECAST_MODELS + [ERA5_CONFIG]:
        logger.info(f"\n--- Fetching {model_name} ({slug}) ---")
        raw[model_name] = {}
        for lat in lats:
            for lon in lons:
                ts = fetch_model_timeseries(model_name, slug, endpoint, lat, lon)
                raw[model_name][(round(lat, 4), round(lon, 4))] = ts
                logger.info(f"    {model_name} ({lat:.2f}, {lon:.2f}): {len(ts)} hourly values")

    # -----------------------------------------------------------------------
    # Step 2: Align into training rows
    # -----------------------------------------------------------------------
    logger.info("\n--- Building aligned dataset ---")

    rows = []
    start_dt = datetime.strptime(START_DATE, "%Y-%m-%d")
    end_dt = datetime.strptime(END_DATE, "%Y-%m-%d")

    # Iterate over initialization times (every day at 00Z)
    init_time = start_dt
    while init_time <= end_dt:
        init_str = init_time.strftime("%Y-%m-%d")

        for lead_time in LEAD_TIMES:
            valid_time = init_time + timedelta(hours=lead_time)
            vt_str = valid_time.strftime("%Y-%m-%dT%H:00")

            for lat in lats:
                for lon in lons:
                    key = (round(lat, 4), round(lon, 4))

                    # Fetch each model's forecast for this valid_time
                    ifs_val  = raw["IFS"].get(key, {}).get(vt_str)
                    gfs_val  = raw["GFS"].get(key, {}).get(vt_str)
                    icon_val = raw["ICON"].get(key, {}).get(vt_str)
                    era5_val = raw["ERA5"].get(key, {}).get(vt_str)

                    # Skip rows where ANY value is missing — no fabrication
                    if any(v is None for v in [ifs_val, gfs_val, icon_val, era5_val]):
                        continue

                    rows.append({
                        'initialization_time': init_str,
                        'valid_time': vt_str,
                        'lead_time': lead_time,
                        'latitude': round(lat, 4),
                        'longitude': round(lon, 4),
                        'IFS': ifs_val,
                        'GFS': gfs_val,
                        'ICON': icon_val,
                        'reference_value': era5_val,
                    })

        init_time += timedelta(days=1)

    df = pd.DataFrame(rows)
    logger.info(f"Total aligned rows: {len(df)}")

    if len(df) == 0:
        logger.error("ZERO rows generated — all data was missing. ABORTING.")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 3: Feature engineering
    # -----------------------------------------------------------------------
    logger.info("\n--- Feature engineering ---")

    df['valid_time_dt'] = pd.to_datetime(df['valid_time'])
    df['hour'] = df['valid_time_dt'].dt.hour
    df['day_of_year'] = df['valid_time_dt'].dt.dayofyear

    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24.0)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24.0)
    df['doy_sin']  = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
    df['doy_cos']  = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
    df['lead_time_sqrt'] = np.sqrt(df['lead_time'])

    # Model disagreement features
    df['disagreement_std'] = df[['IFS', 'ICON', 'GFS']].std(axis=1)
    df['disagreement_range'] = df[['IFS', 'ICON', 'GFS']].max(axis=1) - df[['IFS', 'ICON', 'GFS']].min(axis=1)
    df['diff_ifs_icon'] = df['IFS'] - df['ICON']
    df['diff_ifs_gfs']  = df['IFS'] - df['GFS']

    df.drop(columns=['valid_time_dt', 'hour', 'day_of_year'], inplace=True)

    # -----------------------------------------------------------------------
    # Step 4: Chronological split (70/15/15)
    # -----------------------------------------------------------------------
    logger.info("\n--- Chronological split ---")
    df = df.sort_values('initialization_time').reset_index(drop=True)

    n = len(df)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)

    df_train = df.iloc[:train_end].copy()
    df_val   = df.iloc[train_end:val_end].copy()
    df_test  = df.iloc[val_end:].copy()

    logger.info(f"Train: {len(df_train)} rows  ({df_train['initialization_time'].min()} → {df_train['initialization_time'].max()})")
    logger.info(f"Val:   {len(df_val)} rows  ({df_val['initialization_time'].min()} → {df_val['initialization_time'].max()})")
    logger.info(f"Test:  {len(df_test)} rows  ({df_test['initialization_time'].min()} → {df_test['initialization_time'].max()})")

    # -----------------------------------------------------------------------
    # Step 5: Save
    # -----------------------------------------------------------------------
    out_dir = PROJECT_ROOT / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(out_dir / "training_features.csv", index=False)
    df_train.to_csv(out_dir / "train.csv", index=False)
    df_val.to_csv(out_dir / "val.csv", index=False)
    df_test.to_csv(out_dir / "test.csv", index=False)

    logger.info(f"\nSaved: training_features.csv, train.csv, val.csv, test.csv")

    # -----------------------------------------------------------------------
    # Step 6: Sanity checks
    # -----------------------------------------------------------------------
    logger.info("\n" + "=" * 80)
    logger.info("SANITY CHECKS")
    logger.info("=" * 80)

    # Check 1: No model achieves RMSE = 0.0 against ERA5-Land
    for model in ['IFS', 'GFS', 'ICON']:
        rmse = np.sqrt(np.mean((df[model] - df['reference_value'])**2))
        mae  = np.mean(np.abs(df[model] - df['reference_value']))
        logger.info(f"  {model} vs ERA5-Land:  RMSE = {rmse:.4f}°C   MAE = {mae:.4f}°C")
        if rmse < 0.01:
            logger.error(f"  CRITICAL: {model} RMSE is near zero — POSSIBLE TARGET LEAKAGE!")
            sys.exit(1)

    # Check 2: Simple average baseline
    avg = df[['IFS', 'GFS', 'ICON']].mean(axis=1)
    avg_rmse = np.sqrt(np.mean((avg - df['reference_value'])**2))
    logger.info(f"  Simple Average vs ERA5-Land:  RMSE = {avg_rmse:.4f}°C")

    # Check 3: Temperature reasonableness (Hyderabad: 10-50°C)
    for col in ['IFS', 'GFS', 'ICON', 'reference_value']:
        mn, mx = df[col].min(), df[col].max()
        logger.info(f"  {col} range: [{mn:.1f}, {mx:.1f}]°C")
        if mn < 5 or mx > 55:
            logger.warning(f"  WARNING: {col} has values outside expected Hyderabad range")

    # Check 4: No NaN in final data
    nan_count = df[['IFS', 'GFS', 'ICON', 'reference_value']].isna().sum().sum()
    logger.info(f"  NaN count in final data: {nan_count}")

    logger.info("\n" + "=" * 80)
    logger.info("BULK DATA BUILD COMPLETE")
    logger.info("=" * 80)

    return df

if __name__ == "__main__":
    build_dataset()
