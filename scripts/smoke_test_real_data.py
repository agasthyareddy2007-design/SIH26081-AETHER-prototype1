#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.openmeteo_client import get_open_meteo_client

def run_smoke_test():
    client = get_open_meteo_client("/tmp/smoke_test_om_cache")
    lat, lon = 17.385, 78.4867
    end_date = datetime(2025, 8, 7)
    start_date = end_date - timedelta(days=6)
    
    print("=== SIH26081 REAL DATA SMOKE TEST ===")
    print(f"Location: {lat}, {lon}")
    print(f"Dates: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    tests = [
        {"name": "IFS", "url": "https://historical-forecast-api.open-meteo.com/v1/forecast", "models": "ecmwf_ifs025"},
        {"name": "GFS", "url": "https://historical-forecast-api.open-meteo.com/v1/forecast", "models": "gfs_seamless"},
        {"name": "ICON", "url": "https://historical-forecast-api.open-meteo.com/v1/forecast", "models": "icon_seamless"},
        {"name": "ERA5-Land", "url": "https://archive-api.open-meteo.com/v1/archive", "models": "era5_land"}
    ]
    
    failures = 0
    for t in tests:
        print(f"\nTesting {t['name']}...")
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "hourly": "temperature_2m",
            "models": t["models"]
        }
        try:
            res = client.fetch(t["url"], params)
            if not isinstance(res, dict) or "hourly" not in res:
                print(f"FAILED: Invalid response structure.")
                failures += 1
                continue
            temps = [x for x in res["hourly"]["temperature_2m"] if x is not None]
            if not temps:
                print(f"FAILED: No temperature data returned.")
                failures += 1
                continue
            
            avg_temp = sum(temps) / len(temps)
            min_temp, max_temp = min(temps), max(temps)
            
            # Bounds check for Hyderabad (~15C to ~45C historically)
            if 15 <= avg_temp <= 45:
                print(f"SUCCESS: Data fetched successfully. Total points: {len(temps)}")
                print(f"Metrics -> Min: {min_temp:.1f}°C, Max: {max_temp:.1f}°C, Avg: {avg_temp:.1f}°C")
            else:
                print(f"WARNING: Temperature out of typical bounds (Avg: {avg_temp:.1f}°C)")
                
            # Print sample corresponding to noon UTC
            idx = 12 # 12:00 on first day
            print(f"Sample at {res['hourly']['time'][idx]}: {res['hourly']['temperature_2m'][idx]}°C")
            
        except Exception as e:
            print(f"FAILED: Exception occurred: {e}")
            failures += 1
            
    if failures == 0:
        print("\nSMOKE TEST: PASS - All live Open-Meteo systems online.")
        sys.exit(0)
    else:
        print(f"\nSMOKE TEST: FAIL - {failures} integrations failing.")
        sys.exit(1)

if __name__ == "__main__":
    run_smoke_test()
