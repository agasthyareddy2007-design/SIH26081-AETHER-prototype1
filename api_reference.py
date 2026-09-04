"""
SIH26081 Multi-Model Ensemble Forecasting API
FastAPI backend connecting to existing PyTorch forecasting engine and AETHER assistant
"""

import sys
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import time

# Add the AI models project to Python path
sys.path.insert(0, "/home/agasthya/ai models")

from src.engine.forecasting_engine import ForecastingEngine
from src.engine.aether_assistant import AETHERAssistant

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("forecast-api")

# Initialize FastAPI app
app = FastAPI(
    title="SIH26081 Forecasting API",
    description="Multi-model ensemble weather forecasting with AETHER conversational assistant",
    version="1.0.0"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ForecastRequest(BaseModel):
    lat: float = Field(..., description="Latitude in decimal degrees", ge=-90, le=90)
    lon: float = Field(..., description="Longitude in decimal degrees", ge=-180, le=180)
    valid_time: str = Field(..., description="Valid time in ISO format (YYYY-MM-DD HH:MM:SS)")
    lead_time_hours: int = Field(..., description="Lead time in hours", ge=0)

class ChatRequest(BaseModel):
    prompt: str = Field(..., description="User message to AETHER assistant")

class ForecastResponse(BaseModel):
    forecast: float
    unit: str
    valid_time: str
    lead_time_hours: int
    location: Dict[str, Any]
    model_weights: Dict[str, float]
    model_forecasts: Dict[str, float]
    disagreement: float
    uncertainty: float
    confidence: str
    reference_value: float | None

class ChatResponse(BaseModel):
    reply: str

# Global instances (initialized at startup)
forecasting_engine: ForecastingEngine = None
aether_assistant: AETHERAssistant = None



# Global geocoder instance
geolocator = Nominatim(user_agent="sih_aether_app")

def extract_area_name(prompt_lower):
    # Try to heuristically extract location name, else fallback or use full prompt
    # A simple but practical implementation for this prototype
    # If it sees keywords like 'in', 'at', 'for'
    match = re.search(r'(?:in|at|for)\s+([a-zA-Z\s]+?)(?:\s+(?:what|time|forecast|weather|temperature)|\!|\?|$)', prompt_lower)
    if match:
        return match.group(1).strip()
    return prompt_lower[:50].strip() # fallback

def geocode_location(location_name):
    # Append 'Hyderabad, India' for restricted search
    search_query = f"{location_name}, Hyderabad, India"
    try:
        location = geolocator.geocode(search_query, timeout=5)
        if location:
            # Bound check 
            lat, lon = location.latitude, location.longitude
            if 16.5 <= lat <= 18.0 and 77.5 <= lon <= 79.5:
                return lat, lon, location.name
        return None, None, None
    except (GeocoderTimedOut, GeocoderUnavailable):
        return None, None, None

@app.on_event("startup")
async def startup_event():
    """Initialize forecasting engine and AETHER assistant on startup"""
    global forecasting_engine, aether_assistant

    logger.info("Initializing SIH26081 Forecasting System...")

    try:
        # Initialize Forecasting Engine
        model_path = Path("/home/agasthya/ai models/models/blender/mlp_gating_model")
        logger.info("Loading PyTorch forecasting engine...")
        forecasting_engine = ForecastingEngine(
            config_path=None,
            model_path=model_path
        )
        logger.info("✓ Forecasting engine loaded")

        # Initialize AETHER Assistant
        logger.info("Loading AETHER conversational assistant (this may take 30-60 seconds)...")
        aether_assistant = AETHERAssistant(
            engine=forecasting_engine,
            model_id="Qwen/Qwen2.5-3B-Instruct"
        )
        logger.info("✓ AETHER assistant loaded and ready")

        logger.info("="*80)
        logger.info("SIH26081 API Server Ready")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        raise

@app.get("/")
async def root():
    """Serve the main dashboard interface"""
    return {"message": "API is operational. Frontend has been removed."}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "forecasting_engine": "ready" if forecasting_engine else "not initialized",
        "aether_assistant": "ready" if aether_assistant else "not initialized"
    }

@app.post("/api/forecast", response_model=ForecastResponse)
async def get_forecast(request: ForecastRequest):
    """
    Get forecast from the multi-model ensemble system

    Returns candidate forecasts (IFS, GFS, ICON), learned dynamic weights,
    blended prediction, uncertainty estimates, and confidence metrics.
    """
    if not forecasting_engine:
        raise HTTPException(status_code=503, detail="Forecasting engine not initialized")

    try:
        # Parse the datetime string
        valid_time = datetime.fromisoformat(request.valid_time.replace(' ', 'T'))

        # Get prediction from forecasting engine
        logger.info(f"Forecast request: lat={request.lat}, lon={request.lon}, "
                   f"valid_time={valid_time}, lead_time={request.lead_time_hours}h")

        result = forecasting_engine.predict_forecast(
            valid_time=valid_time,
            lead_time_hours=request.lead_time_hours,
            lat=request.lat,
            lon=request.lon
        )

        logger.info(f"Forecast generated: {result['forecast']}°C "
                   f"(IFS: {result['model_weights']['IFS']:.1%}, "
                   f"GFS: {result['model_weights']['GFS']:.1%}, "
                   f"ICON: {result['model_weights']['ICON']:.1%})")

        return ForecastResponse(**result)

    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Forecast generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {str(e)}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_aether(request: ChatRequest):
    """
    Chat with AETHER conversational assistant

    Intercepts the prompt to inject context-aware coordinates and date boundaries
    before passing to the LLM agent.
    """
    if not aether_assistant:
        raise HTTPException(status_code=503, detail="AETHER assistant not initialized")

    try:
        prompt_lower = request.prompt.lower()

        # 1. Location Extraction & Geographic Resolution via Geopy
        extracted_area_name = extract_area_name(prompt_lower)
        mapped_lat, mapped_lon, loc_name = geocode_location(extracted_area_name)
        
        # 2. Date/Lead Time Boundary Injection
        valid_time_override = None
        if 'tomorrow' in prompt_lower:
            valid_time_override = '2026-09-05 12:00:00'
            lead_time = 24
        elif 'next monday' in prompt_lower:
            valid_time_override = '2026-09-07 12:00:00'
            lead_time = 72
        elif 'day after tomorrow' in prompt_lower:
            valid_time_override = '2026-09-06 12:00:00'
            lead_time = 48
        elif 'in 2 days' in prompt_lower:
            valid_time_override = '2026-09-06 12:00:00'
            lead_time = 48

        has_time_info = bool(re.search(r'\b(2026|aug|august|time|hour|h|hr|-08-|26th|today)\b', prompt_lower))

        injections = []
        if mapped_lat is not None and mapped_lon is not None:
            area_display = loc_name.split(',')[0] if loc_name else extracted_area_name.title()
            injections.append(f"[System override: The user is asking about {area_display}. Use lat {mapped_lat:.4f}, lon {mapped_lon:.4f} for your tool calls. CRITICAL: In your final response, refer to the location ONLY by its name \"{area_display}\". Do not mention the latitude and longitude.]")

        if valid_time_override:
            injections.append(f"[System override: The user requested a relative future date. Translating to valid_time '{valid_time_override}' with lead_time_hours {lead_time} based on the current date 2026-09-04.]")
        elif not has_time_info and 'tomorrow' not in prompt_lower and 'next' not in prompt_lower:
            injections.append("[System override: Default to valid_time '2026-09-04 12:00:00' with lead_time_hours 12]")

        enriched_prompt = request.prompt
        if injections:
            enriched_prompt += " " + " ".join(injections)

        logger.info(f"AETHER query (Enriched): {enriched_prompt}")

        # Process the query through AETHER
        reply = aether_assistant.run_interaction(enriched_prompt)

        logger.info(f"AETHER response: {reply[:100]}...")

        return ChatResponse(reply=reply)

    except Exception as e:
        logger.error(f"AETHER query failed: {e}")
        raise HTTPException(status_code=500, detail=f"AETHER query failed: {str(e)}")

@app.get("/api/available-times")
async def get_available_times():
    """Get available test dates and lead times"""
    if not forecasting_engine or forecasting_engine.dataset is None:
        raise HTTPException(status_code=503, detail="Forecasting engine not initialized")

    try:
        df = forecasting_engine.dataset

        # Get unique values
        valid_times = sorted(df['valid_time'].dt.strftime('%Y-%m-%d %H:%M:%S').unique())
        lead_times = sorted(df['lead_time'].unique().tolist())

        # Get spatial bounds
        lat_min, lat_max = df['latitude'].min(), df['latitude'].max()
        lon_min, lon_max = df['longitude'].min(), df['longitude'].max()

        return {
            "valid_times": valid_times[:50],  # Return first 50 times
            "lead_times": [int(x) for x in lead_times],
            "spatial_bounds": {
                "lat_min": float(lat_min),
                "lat_max": float(lat_max),
                "lon_min": float(lon_min),
                "lon_max": float(lon_max)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get available times: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files placeholder (frontend removed)
# app.mount("/static", ...)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
