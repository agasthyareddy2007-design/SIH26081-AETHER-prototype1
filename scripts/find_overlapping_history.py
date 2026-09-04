#!/usr/bin/env python3
import sys
from datetime import datetime, timedelta
from pathlib import Path
import logging

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from src.data.openmeteo_client import get_open_meteo_client

logging.basicConfig(level=logging.INFO)

def check_date_available(client, lat, lon, check_date, model_slug, endpoint):
    d_str = check_date.strftime('%Y-%m-%d')
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": d_str,
        "end_date": d_str,
        "hourly": "temperature_2m",
        "models": model_slug
    }
    try:
        res = client.fetch(endpoint, params)
        if isinstance(res, list):
            res = res[0]
        temps = res.get("hourly", {}).get("temperature_2m", [])
        return any(t is not None for t in temps)
    except Exception as e:
        return False

def main():
    client = get_open_meteo_client("/tmp/find_history_cache")
    lat, lon = 17.385, 78.4867
    
    # We want to find the earliest contiguous timeline up to today where all 4 work.
    today = datetime(2026, 9, 3) # Use 3rd to ensure data completeness across all TZs
    
    models = [
        ("IFS", "https://historical-forecast-api.open-meteo.com/v1/forecast", "ecmwf_ifs025"),
        ("GFS", "https://historical-forecast-api.open-meteo.com/v1/forecast", "gfs_seamless"),
        ("ICON", "https://historical-forecast-api.open-meteo.com/v1/forecast", "icon_seamless"),
        ("ERA5-Land", "https://archive-api.open-meteo.com/v1/archive", "era5_land")
    ]
    
    # Let's binary search or just step back in 30-day chunks
    # Actually, we know IFS 0.25 goes back pretty far. Let's check 365 days ago directly.
    target_start = today - timedelta(days=365)
    
    all_good = True
    for name, endpoint, slug in models:
        if not check_date_available(client, lat, lon, target_start, slug, endpoint):
            print(f"Model {name} missing data on {target_start.strftime('%Y-%m-%d')}")
            all_good = False
            
    if all_good:
        print(f"SUCCESS: All models have data for the full 365 days starting {target_start.strftime('%Y-%m-%d')}.")
        d = target_start
    else:
        # Step forward until we find good data
        print("Finding earliest valid common date...")
        good_date = None
        for i in range(365, -1, -1):
            check_d = today - timedelta(days=i)
            day_good = True
            for name, endpoint, slug in models:
                if not check_date_available(client, lat, lon, check_d, slug, endpoint):
                    day_good = False
                    break
            if day_good:
                good_date = check_d
                break
        if good_date:
            print(f"SUCCESS: Earliest overlapping date is {good_date.strftime('%Y-%m-%d')}")
            d = good_date
        else:
            print("FAILED: No overlapping data found at all.")
            sys.exit(1)
            
    # Output recommended splits based on available data
    total_days = (today - d).days
    print(f"Total contiguous days available: {total_days}")
    
if __name__ == "__main__":
    main()
