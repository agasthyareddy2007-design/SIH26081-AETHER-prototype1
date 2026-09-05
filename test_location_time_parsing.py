import os
import sys
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from src.engine.forecasting_engine import ForecastingEngine
from src.engine.aether_assistant import AETHERAssistant
import api_reference

# Set mock env variables for provider
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
    def get_model_weights(self, *args, **kwargs): return {}
    def get_model_comparison(self, *args, **kwargs): return {}
    def get_forecast_explanation(self, *args, **kwargs): return {}
    def get_uncertainty(self, *args, **kwargs): return {}

def test_integration_pipeline_gachibowli():
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
        
        import asyncio
        request = api_reference.ChatRequest(prompt="What will the temperature be in Gachibowli tomorrow at 12 PM?")
        response = asyncio.run(api_reference.chat_with_aether(request))
        
        # Assert
        assert mock_execute_tool.called
        action, args = mock_execute_tool.call_args[0]
        
        assert action == "predict_forecast"
        assert args["lat"] == 17.44
        assert args["lon"] == 78.34
        assert args["valid_time"] == "2026-09-05 12:00:00"
        assert args["lead_time_hours"] == 24
        
        # Ensure Numerical Forecast Engine Result went to Gemini
        messages_sent_to_gemini = mock_generate_external.call_args[0][0]
        user_message = messages_sent_to_gemini[-1]["content"]
        assert "Numerical Forecast Engine Result" in user_message
        assert "29.06" in user_message

def test_integration_pipeline_secunderabad():
    engine = MockForecastingEngine()
    assistant = AETHERAssistant(engine=engine)
    api_reference.aether_assistant = assistant
    api_reference.forecasting_engine = engine

    with patch("api_reference.geolocator.geocode") as mock_geocode, \
         patch.object(assistant, "_generate_external") as mock_generate_external, \
         patch.object(assistant, "execute_tool", wraps=assistant.execute_tool) as mock_execute_tool:

        mock_loc = MagicMock()
        mock_loc.latitude = 17.43
        mock_loc.longitude = 78.49
        mock_loc.name = "Secunderabad"
        mock_geocode.return_value = mock_loc
        mock_generate_external.return_value = "Mocked Gemini Output"
        
        import asyncio
        request = api_reference.ChatRequest(prompt="what's the weather in secunderabad tomorrow?")
        response = asyncio.run(api_reference.chat_with_aether(request))
        
        assert mock_execute_tool.called
        action, args = mock_execute_tool.call_args[0]
        
        assert args["lat"] == 17.43
        assert args["lon"] == 78.49
        assert args["valid_time"] == "2026-09-05 12:00:00"

def test_integration_pipeline_explicit_date():
    engine = MockForecastingEngine()
    assistant = AETHERAssistant(engine=engine)
    api_reference.aether_assistant = assistant
    api_reference.forecasting_engine = engine

    with patch("api_reference.geolocator.geocode") as mock_geocode, \
         patch.object(assistant, "_generate_external") as mock_generate_external, \
         patch.object(assistant, "execute_tool", wraps=assistant.execute_tool) as mock_execute_tool:

        mock_loc = MagicMock()
        mock_loc.latitude = 17.48
        mock_loc.longitude = 78.40
        mock_loc.name = "Kukatpally"
        mock_geocode.return_value = mock_loc
        mock_generate_external.return_value = "Mocked Gemini Output"
        
        import asyncio
        request = api_reference.ChatRequest(prompt="Give me the forecast for Kukatpally on September 10 at 3 PM.")
        response = asyncio.run(api_reference.chat_with_aether(request))
        
        assert mock_execute_tool.called
        action, args = mock_execute_tool.call_args[0]
        assert args["lat"] == 17.48
        assert args["lon"] == 78.40
        assert args["valid_time"] == "2026-09-10 15:00:00"
        assert args["lead_time_hours"] == 147

def test_integration_pipeline_non_weather():
    engine = MockForecastingEngine()
    assistant = AETHERAssistant(engine=engine)
    api_reference.aether_assistant = assistant
    api_reference.forecasting_engine = engine

    with patch("api_reference.geolocator.geocode") as mock_geocode, \
         patch.object(assistant, "_generate_external") as mock_generate_external, \
         patch.object(assistant, "execute_tool", wraps=assistant.execute_tool) as mock_execute_tool:

        mock_generate_external.return_value = "Hello! I am AETHER."
        
        import asyncio
        request = api_reference.ChatRequest(prompt="Hello AETHER")
        response = asyncio.run(api_reference.chat_with_aether(request))
        
        # Should NOT call tool
        assert not mock_execute_tool.called
        
        # Ensure it just passed text through
        messages = mock_generate_external.call_args[0][0]
        # No Numerical Forecast Result should be attached
        assert "Numerical Forecast Engine Result" not in messages[-1]["content"]

