import os
import sys
from pathlib import Path
from src.engine.forecasting_engine import ForecastingEngine
from api_reference import app

def check():
    # 1. Inspect PORT configuration
    if "PORT" not in os.environ:
        os.environ["PORT"] = "8080"

    # 2. Check model SHA remains unchanged
    import hashlib
    model_path = Path("models/blender/mlp_gating_model.pth")
    if not model_path.exists():
        print("FATAL: mlp_gating_model.pth missing!")
        sys.exit(1)

    with open(model_path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    if sha != "11180fb2b72d49154434ecad3276281b305277d0eeb2098df86d4485d5ad32b4":
        print(f"FATAL: Production model SHA mismatch: {sha}")
        sys.exit(1)

    print("✓ Cloud Run Readiness: Model SHA verified.")

    # 3. Application exists
    if not app:
        print("FATAL: FastAPI app did not load.")
        sys.exit(1)

    print(f"✓ Cloud Run Readiness: FastAPI App loaded. Preparing to bind to 0.0.0.0:{os.environ['PORT']}")
    print("--- Cloud Run Readiness PASS ---")

if __name__ == "__main__":
    check()
