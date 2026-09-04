import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, "/home/agasthya/ai models")

from src.engine.forecasting_engine import ForecastingEngine

def main():
    engine = ForecastingEngine(Path("."), Path("/home/agasthya/ai models/models/blender/mlp_gating_model"))
    
    # Try fetching a valid time way out in the future (where API will likely not have hourly data, or just mock it)
    # Actually let's just make the lat/lon completely invalid so open-meteo throws a 400 Client Error
    lat = 999.0
    lon = 999.0
    valid_time = datetime.utcnow() + timedelta(days=1)
    
    try:
        engine.predict_forecast(valid_time, 24, lat, lon)
        print("FAIL: Should have raised an error.")
        sys.exit(1)
    except ValueError as e:
        print(f"SUCCESS (Explicit Error Raised): {e}")

if __name__ == '__main__':
    main()
