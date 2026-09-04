import os
import sys
from pathlib import Path
from datetime import datetime

# We will patch requests.post and our om_client.fetch to intercept URLs and params
import requests

# Test 1 & 2: Gemini URLs
from src.engine.aether_assistant import AETHERAssistant
from src.engine.forecasting_engine import ForecastingEngine

# Dummy engine
try:
    engine = ForecastingEngine(
        config_path=Path("config/environment.yaml"),
        model_path=Path("models/blender/mlp_gating_model"),
        enable_persistence=False
    )
except Exception as e:
    print(f"FATAL: Engine load failed - {e}")
    sys.exit(1)

intercepted_url = ""

def mock_post(url, *args, **kwargs):
    global intercepted_url
    intercepted_url = url
    class MockResponse:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": "mocked"}}]}
    return MockResponse()

original_post = requests.post
requests.post = mock_post

# Test trailing slash
os.environ["AETHER_LLM_PROVIDER"] = "external"
os.environ["EXTERNAL_LLM_API_KEY"] = "sk-dummy"
os.environ["EXTERNAL_LLM_API_BASE"] = "https://example.com/v1beta/openai/"

assistant = AETHERAssistant(engine=engine)
assistant.run_interaction("Hello")
if intercepted_url != "https://example.com/v1beta/openai/chat/completions":
    print(f"FATAL: Gemini URL with trailing slash failed: {intercepted_url}")
    sys.exit(1)
print("✓ Gemini base URL with trailing slash is correctly sanitized.")

# Test without trailing slash
os.environ["EXTERNAL_LLM_API_BASE"] = "https://example.com/v1beta/openai"
assistant = AETHERAssistant(engine=engine)
assistant.run_interaction("Hello")
if intercepted_url != "https://example.com/v1beta/openai/chat/completions":
    print(f"FATAL: Gemini URL without trailing slash failed: {intercepted_url}")
    sys.exit(1)
print("✓ Gemini base URL without trailing slash remains correct.")

requests.post = original_post

# Test 3: Open-Meteo API Key
intercepted_om_args = []

def mock_fetch(endpoint, params):
    global intercepted_om_args
    intercepted_om_args.append((endpoint, params))
    # mock a valid response
    vt_str = "2026-09-05T12:00"
    return [{"hourly": {"time": [vt_str], "temperature_2m": [25.0]}}]

engine.om_client.fetch = mock_fetch

os.environ["OPENMETEO_API_KEY"] = "om-sk-test-12345"

# Request future forecast
vt = datetime(2026, 9, 5, 12, 0, 0)
engine.predict_forecast(vt, lead_time_hours=24, lat=17.4, lon=78.3)

for endpoint, params in intercepted_om_args:
    if not endpoint.startswith("https://customer-api"):
        print(f"FATAL: Endpoint did not use customer prefix: {endpoint}")
        sys.exit(1)
    if params.get("apikey") != "om-sk-test-12345":
        print(f"FATAL: API key missing or incorrect in params: {params}")
        sys.exit(1)

print("✓ Open-Meteo authenticated configuration routes correctly to customer API.")

# Ensure keys are not in logs/errors
import logging
from io import StringIO
log_stream = StringIO()
handler = logging.StreamHandler(log_stream)
engine.logger.addHandler(handler)

# trigger an error by patching fetch to simulate a crash
def mock_fetch_error(endpoint, params):
    raise Exception("Simulated OM crash")

engine.om_client.fetch = mock_fetch_error
try:
    engine.predict_forecast(vt, lead_time_hours=24, lat=17.4, lon=78.3)
except Exception:
    pass

logs = log_stream.getvalue()
if "om-sk-test-12345" in logs:
    print("FATAL: Open-Meteo API key leaked in engine logs!")
    sys.exit(1)

print("✓ Open-Meteo API key never appears in engine logs/errors.")

print("--- ALL REGRESSION TESTS PASS ---")

# Test 4: Gemini model resolves to gemini-2.5-flash
assistant = AETHERAssistant(engine=engine)
if assistant.model_name != "gemini-2.5-flash":
    print(f"FATAL: Expected model 'gemini-2.5-flash', got '{assistant.model_name}'")
    sys.exit(1)
print("✓ Gemini model resolves to gemini-2.5-flash.")

print("--- ALL UPDATED REGRESSION TESTS PASS ---")
