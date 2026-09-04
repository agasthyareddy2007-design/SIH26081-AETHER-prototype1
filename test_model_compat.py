import sys
import hashlib
from pathlib import Path
from src.engine.forecasting_engine import ForecastingEngine

print(f"Python Version: {sys.version}")

# 1. SHA Checks
def check_sha(path, expected):
    if not path.exists():
        print(f"FATAL: Missing {path}")
        sys.exit(1)
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    if sha != expected:
        print(f"FATAL: {path.name} SHA mismatch: {sha} != {expected}")
        sys.exit(1)
    print(f"✓ {path.name} SHA verified: {sha}")

check_sha(Path("models/blender/mlp_gating_model.pth"), "11180fb2b72d49154434ecad3276281b305277d0eeb2098df86d4485d5ad32b4")

# 2. Check the meta files exist (used by the engine internally)
if not Path("models/blender/feature_means_stds.npy").exists():
    print("FATAL: feature_means_stds.npy missing")
    sys.exit(1)
if not Path("models/blender/mlp_gating_model_meta.json").exists():
    print("FATAL: mlp_gating_model_meta.json missing")
    sys.exit(1)

print("✓ Metadata and Feature scaling artifacts present.")

# 3. Actually LOAD the model using ForecastingEngine
try:
    engine = ForecastingEngine(
        config_path=Path("config/environment.yaml"),
        model_path=Path("models/blender/mlp_gating_model"),  # The .pth is appended inside
        enable_persistence=False
    )
    print("✓ Model successfully initialized via ForecastingEngine.")
except Exception as e:
    print(f"FATAL: Model loading failed: {e}")
    sys.exit(1)

print("--- Compatibility Check PASS ---")
