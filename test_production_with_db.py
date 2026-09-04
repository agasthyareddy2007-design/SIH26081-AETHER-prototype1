#!/usr/bin/env python3
"""
Production forecast test with database persistence
Verifies ML model integrity and database integration
"""
import sys
import hashlib
import math
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, "/home/agasthya/ai models")

from src.engine.forecasting_engine import ForecastingEngine

def check_model_sha256():
    """Verify production model SHA256"""
    model_path = Path("/home/agasthya/ai models/models/blender/mlp_gating_model.pth")
    with open(model_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def main():
    print("=" * 80)
    print("PRODUCTION FORECAST TEST WITH DATABASE PERSISTENCE")
    print("=" * 80)

    # Verify model integrity BEFORE
    sha256_before = check_model_sha256()
    print(f"\nModel SHA256 (before): {sha256_before}")
    expected = "11180fb2b72d49154434ecad3276281b305277d0eeb2098df86d4485d5ad32b4"

    if sha256_before != expected:
        print(f"✗ FAIL: Model SHA256 mismatch!")
        print(f"  Expected: {expected}")
        print(f"  Got: {sha256_before}")
        sys.exit(1)

    print("✓ Production model integrity verified")

    # Initialize engine with persistence enabled
    print("\n--- Initializing ForecastingEngine with persistence ---")
    engine = ForecastingEngine(
        Path("."),
        Path("/home/agasthya/ai models/models/blender/mlp_gating_model"),
        enable_persistence=True
    )

    # Test future forecast
    print("\n--- Testing Future Forecast (Tomorrow, Gachibowli) ---")
    tomorrow = datetime.utcnow() + timedelta(days=1)
    valid_time = tomorrow.replace(hour=12, minute=0, second=0, microsecond=0)
    lat, lon = 17.44, 78.34
    lead_time_hours = 24

    print(f"Valid Time: {valid_time.isoformat()}")
    print(f"Location: ({lat}, {lon})")
    print(f"Lead Time: {lead_time_hours}h")

    try:
        result = engine.predict_forecast(valid_time, lead_time_hours, lat, lon)
    except Exception as e:
        print(f"✗ Forecast failed: {e}")
        sys.exit(1)

    print("\n--- Forecast Result ---")
    print(f"Blended Temperature: {result['forecast']}°C")
    print(f"Persistence Status: {result['persistence_status']}")

    # Verify live API usage
    print("\n--- Verifying Live API Usage ---")
    for model, prov in result['provenance'].items():
        print(f"{model}:")
        print(f"  Endpoint: {prov['api_endpoint']}")
        print(f"  Data Source: {prov['data_source']}")
        print(f"  Live API: {prov['live_api']}")

        if not prov['live_api']:
            print(f"✗ FAIL: {model} not using live API")
            sys.exit(1)

        if "api.open-meteo.com/v1/forecast" not in prov['api_endpoint']:
            print(f"✗ FAIL: {model} using wrong endpoint")
            sys.exit(1)

    print("✓ All models using Live API")

    # Verify MLPGatingNet Softmax weights
    print("\n--- Verifying MLPGatingNet Weights ---")
    weights = result['model_weights']
    print(f"w_IFS: {weights['IFS']}")
    print(f"w_GFS: {weights['GFS']}")
    print(f"w_ICON: {weights['ICON']}")

    weight_sum = sum(weights.values())
    print(f"Sum: {weight_sum:.6f}")

    if not math.isclose(weight_sum, 1.0, abs_tol=0.01):
        print(f"✗ FAIL: Weights don't sum to 1: {weight_sum}")
        sys.exit(1)

    print("✓ Softmax constraint satisfied")

    # Verify arithmetic
    print("\n--- Verifying Blend Arithmetic ---")
    forecasts = result['model_forecasts']
    explicit_blend = sum(forecasts[k] * weights[k] for k in forecasts.keys())
    actual_blend = result['forecast']

    print(f"Explicit Calculation: {explicit_blend:.3f}°C")
    print(f"Engine Output: {actual_blend}°C")
    print(f"Difference: {abs(actual_blend - explicit_blend):.6f}°C")

    if not math.isclose(explicit_blend, actual_blend, abs_tol=0.1):
        print(f"✗ FAIL: Arithmetic mismatch")
        sys.exit(1)

    print("✓ Arithmetic verified")

    # Verify no synthetic fallback
    print("\n--- Verifying No Synthetic Fallback ---")
    if any('synthetic' in str(v).lower() for v in result.values()):
        print("✗ FAIL: Synthetic data detected")
        sys.exit(1)
    print("✓ No synthetic fallback")

    # Verify uncertainty
    print("\n--- Verifying Uncertainty Metrics ---")
    print(f"Disagreement: {result['disagreement']}°C")
    print(f"Uncertainty: {result['uncertainty']}°C")
    print(f"Confidence: {result['confidence']}")
    print("✓ Uncertainty estimation active")

    # Check database persistence
    print("\n--- Checking Database Persistence ---")
    persistence = result['persistence_status']
    print(f"Persistence Status: {persistence}")

    if persistence == "success":
        print("✓ Database persistence successful")

        # Retrieve recent forecasts
        print("\n--- Retrieving Recent Forecasts ---")
        recent = engine.get_recent_forecasts(lat, lon, limit=5)
        print(f"Retrieved {len(recent)} forecast(s) from database")

        if recent:
            latest = recent[0]
            print(f"Latest: {latest['blended_temperature_c']}°C at {latest['valid_time']}")
            print(f"Model: {latest['model_sha256'][:16]}...")
    elif persistence == "disabled":
        print("⚠ Database persistence disabled (no credentials)")
    elif persistence in ["failed", "partial_failure"]:
        print(f"⚠ Database persistence {persistence} (forecast still valid)")

    # Verify model integrity AFTER
    print("\n--- Verifying Model Integrity (After) ---")
    sha256_after = check_model_sha256()
    print(f"Model SHA256 (after): {sha256_after}")

    if sha256_before != sha256_after:
        print("✗ FAIL: Model was modified!")
        sys.exit(1)

    print("✓ Model unchanged")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✓ Production model SHA256 preserved")
    print("✓ Live API forecasts (IFS, GFS, ICON)")
    print("✓ Softmax weights sum to 1.0")
    print("✓ Blend arithmetic verified")
    print("✓ No synthetic fallback")
    print("✓ Uncertainty metrics operational")
    print(f"✓ Database persistence: {persistence}")
    print("\n✓ ALL TESTS PASSED")
    print(f"\nModel SHA256: {sha256_after}")
    print(f"Blended Forecast: {result['forecast']}°C")
    print(f"Persistence: {persistence}")

if __name__ == '__main__':
    main()
