import os
import sys

# Ensure we're testing the 'external' profile so it doesn't trigger gigabytes of HuggingFace downloads
os.environ["AETHER_LLM_PROVIDER"] = "external"
os.environ["EXTERNAL_LLM_API_KEY"] = "sk-dummy-key"
os.environ["DB_HOST"] = "test.supabase.co"

try:
    from api_reference import app
    print("✓ FastAPI Application structure successfully imported.")
except ImportError as e:
    print(f"FATAL: Application import failed - {e}")
    sys.exit(1)

# Check if Qwen got mysteriously imported/allocated in aether assistant
from src.engine.aether_assistant import AETHERAssistant
import gc

objs = [str(type(obj)) for obj in gc.get_objects()]
if any('transformers' in obj for obj in objs):
    print("FATAL: transformers loaded into memory despite AETHER_LLM_PROVIDER=external")
    sys.exit(1)
print("✓ No transformers model footprints detected in memory.")

print("--- Clean Startup Testing PASS ---")
