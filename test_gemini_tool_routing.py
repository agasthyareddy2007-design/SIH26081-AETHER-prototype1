import os
import sys
import json
import requests
from unittest.mock import patch
from datetime import datetime
from src.engine.forecasting_engine import ForecastingEngine
from src.engine.aether_assistant import AETHERAssistant

def test_external_provider_tool_routing():
    # Setup dummy environment
    os.environ["AETHER_LLM_PROVIDER"] = "external"
    os.environ["EXTERNAL_LLM_API_KEY"] = "sk-dummy"
    os.environ["EXTERNAL_LLM_API_BASE"] = "https://example.com/v1beta/openai"

    class MockForecastingEngine:
        def __init__(self):
            pass
        def predict_forecast(self, valid_time, lead_time_hours, lat, lon):
            return {"forecast": 25.0, "unit": "C"}

    engine = MockForecastingEngine()
    assistant = AETHERAssistant(engine=engine)

    intercepted_payload = None

    def mock_post(url, *args, **kwargs):
        nonlocal intercepted_payload
        intercepted_payload = kwargs.get('json')

        class MockResponse:
            def raise_for_status(self): pass
            def json(self):
                # Simulate native OpenAI tool call
                return {
                    "choices": [{
                        "message": {
                            "tool_calls": [{
                                "function": {
                                    "name": "predict_forecast",
                                    "arguments": '{"lat": 17.44, "lon": 78.34, "valid_time": "2026-09-05 12:00:00", "lead_time_hours": 24}'
                                }
                            }]
                        }
                    }]
                }
        return MockResponse()

    # Apply the mock
    original_post = requests.post
    requests.post = mock_post

    try:
        # Prompt missing lat/lon, forcing AETHER to use the _generate_external loop
        # (It will not hit the fast-path because geocoding override is not provided)
        reply = assistant.run_interaction("What will the temperature be in Gachibowli tomorrow?")

        if not intercepted_payload:
            print("FATAL: Gemini API was not called.")
            sys.exit(1)

        # 1. Verify exact request payload contains `tools`
        if "tools" not in intercepted_payload:
            print("FATAL: Request payload is missing native 'tools' definition!")
            sys.exit(1)

        if len(intercepted_payload["tools"]) != 5:
            print(f"FATAL: Expected 5 tools, got {len(intercepted_payload['tools'])}")
            sys.exit(1)

        # 2. Verify strict JSON text rules are removed from the system prompt
        system_prompt_sent = intercepted_payload["messages"][0]["content"]
        if "You must interact with the environment via strict JSON action outputs." in system_prompt_sent:
            print("FATAL: Strict JSON prompt was not removed for external LLM provider.")
            sys.exit(1)

        print("✓ Gemini OpenAI-compatible native tool schema successfully replaces strict JSON prompting.")
        print("✓ System prompt correctly truncated to prevent text-based JSON generation stalls.")
    finally:
        requests.post = original_post

    print("--- REGRESSION TEST PASS ---")

if __name__ == "__main__":
    test_external_provider_tool_routing()
