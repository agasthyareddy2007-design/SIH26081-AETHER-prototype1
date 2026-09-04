import sys
from pathlib import Path
from datetime import datetime, timedelta
import math
import hashlib

sys.path.insert(0, "/home/agasthya/ai models")

from src.engine.forecasting_engine import ForecastingEngine

def check_model_sha256():
    model_path = Path("/home/agasthya/ai models/models/blender/mlp_gating_model.pth")
    with open(model_path, 'rb') as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    return digest

def main():
    print("Testing Future Forecast Data Source...\n")

    # A. Run a future forecast for Gachibowli for tomorrow
    tomorrow = datetime.utcnow() + timedelta(days=1)
    
    # Force noon for a solid hour
    valid_time = tomorrow.replace(hour=12, minute=0, second=0, microsecond=0)
    lead_time_hours = 24
    
    lat = 17.44
    lon = 78.34
    
    print(f"Target Valid Time: {valid_time.isoformat()} (Lead: {lead_time_hours}h, Lat: {lat}, Lon: {lon})")

    engine = ForecastingEngine(Path("."), Path("/home/agasthya/ai models/models/blender/mlp_gating_model"))
    
    try:
        res = engine.predict_forecast(valid_time, lead_time_hours, lat, lon)
    except Exception as e:
        print(f"FETCH FAILED: {e}")
        sys.exit(1)

    print("\n--- FORECAST RESULT ---")
    print(res)
    print("\n--- PROVENANCE ---")
    for k, v in res.get('provenance', {}).items():
        print(f"{k}: {v}")

    # C. Verify returned
    models_returned = set(res['model_forecasts'].keys())
    assert models_returned == {'IFS', 'ICON', 'GFS'}, f"Missing models: {models_returned}"

    # Verify B, D, E
    for model, prov in res.get('provenance', {}).items():
        assert prov['live_api'] is True, f"{model} did not use live API"
        assert prov['data_source'] == "LIVE FUTURE FORECAST DATA"
        assert "api.open-meteo.com/v1/forecast" in prov['api_endpoint']
        assert "historical" not in prov['api_endpoint']
    
    # G. Verify Softmax sum to 1
    weights = list(res['model_weights'].values())
    sum_w = sum(weights)
    assert math.isclose(sum_w, 1.0, abs_tol=1e-2), f"Weights do not sum to 1: {sum_w} ({weights})"
    
    # H. Explicit Blend
    exp_blend = sum([res['model_forecasts'][k] * res['model_weights'][k] for k in models_returned])
    actual = res['forecast']
    assert math.isclose(exp_blend, actual, abs_tol=0.1), f"Blend arithmetic fails: exp {exp_blend} != act {actual}"
    
    # L. Model SHA256 Check
    sha256 = check_model_sha256()
    assert sha256 == "11180fb2b72d49154434ecad3276281b305277d0eeb2098df86d4485d5ad32b4", f"SHA256 mismatch: {sha256}"
    
    print("\nSUCCESS! All checks passed.")
    print(f"Model SHA256: {sha256}")
    print(f"Blended Result: {actual} (Explicit: {exp_blend:.3f})")
    
if __name__ == '__main__':
    main()
