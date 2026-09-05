import os
import sys
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
import asyncio

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from src.engine.forecasting_engine import ForecastingEngine
from src.engine.aether_assistant import AETHERAssistant
import api_reference

os.environ["AETHER_LLM_PROVIDER"] = "external"
os.environ["EXTERNAL_LLM_API_KEY"] = "dummy"

class MockForecastingEngine:
    def __init__(self):
        self.dataset = None
    def predict_forecast(self, valid_time, lead_time_hours, lat, lon):
        return {
            "forecast": 29.06, 
            "unit": "C", 
            "valid_time": valid_time.strftime("%Y-%m-%d %H:%M:%S"),
            "lead_time_hours": lead_time_hours,
            "location": {"latitude": lat, "longitude": lon},
            "model_weights": {"IFS": 0.4, "GFS": 0.3, "ICON": 0.3},
            "model_forecasts": {"IFS": 29.1, "GFS": 29.0, "ICON": 29.0},
            "disagreement": 0.1,
            "uncertainty": 0.5,
            "confidence": "High",
            "reference_value": None,
            "provenance": {"IFS": {}, "GFS": {}, "ICON": {}},
            "persistence_status": "disabled"
        }

engine = MockForecastingEngine()
assistant = AETHERAssistant(engine=engine)
api_reference.aether_assistant = assistant
api_reference.forecasting_engine = engine

with patch("api_reference.geolocator.geocode") as mock_geocode, \
     patch.object(assistant, "_generate_external") as mock_generate_external, \
     patch.object(assistant, "execute_tool", wraps=assistant.execute_tool) as mock_execute_tool:

    mock_loc = MagicMock()
    mock_loc.latitude = 17.44
    mock_loc.longitude = 78.34
    mock_loc.name = "Gachibowli"
    mock_geocode.return_value = mock_loc
    mock_generate_external.return_value = "Mocked Gemini Output"
    
    request = api_reference.ChatRequest(prompt="What will the temperature be in Gachibowli tomorrow at 12 PM?")
    asyncio.run(api_reference.chat_with_aether(request))
    
    print("\n=== execute_tool Arguments ===")
    action, args = mock_execute_tool.call_args[0]
    print(f"Action: {action}")
    print(f"Args: {json.dumps(args, indent=2)}")
    
    print("\n=== Gemini Payload Context ===")
    messages = mock_generate_external.call_args[0][0]
    for msg in messages:
        if msg["role"] == "user":
            print(f"Role: user\nContent:\n{msg['content']}")
