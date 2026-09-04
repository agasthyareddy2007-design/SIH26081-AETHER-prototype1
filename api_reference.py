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
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

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
    explainability: Dict[str, Any] | None = None
    provenance: Dict[str, Any] | None = None
    persistence_status: str | None = None

class ChatResponse(BaseModel):
    reply: str

# Global instances (initialized at startup)
forecasting_engine: ForecastingEngine = None
aether_assistant: AETHERAssistant = None



# Global geocoder instance
geolocator = Nominatim(user_agent="sih_aether_app")

from datetime import timedelta
# BASE TIME FOR DATE MATH
CURRENT_SIMULATED_TIME = datetime(2026, 9, 4, 12, 0, 0)

def extract_area_name(prompt_lower):
    # Use word boundaries so 'at' inside 'what' is skipped
    match = re.search(r'\b(?:in|at|for)\b\s+([a-zA-Z\s]+?)(?:\s+(?:what|time|now|forecast|weather|temperature|tomorrow|today|next|on|at|\d)|\!|\?|\.|&|$)', prompt_lower)
    if match:
        return match.group(1).strip()
    return None

def resolve_temporal_parameters(prompt_lower):
    target_date = None
    
    if "day after tomorrow" in prompt_lower or "in 2 days" in prompt_lower:
        target_date = CURRENT_SIMULATED_TIME + timedelta(days=2)
    elif "tomorrow" in prompt_lower:
        target_date = CURRENT_SIMULATED_TIME + timedelta(days=1)
    elif "today" in prompt_lower:
        target_date = CURRENT_SIMULATED_TIME
    elif re.search(r"\b(september|sep|october|oct|november|nov)\s+(\d+)\b", prompt_lower):
        m_match = re.search(r"\b(september|sep|october|oct|november|nov)\s+(\d+)\b", prompt_lower)
        month_str = m_match.group(1)[:3]
        day = int(m_match.group(2))
        month_map = {'sep': 9, 'oct': 10, 'nov': 11}
        target_date = datetime(2026, month_map[month_str], day)
        
    hour = 12 # Default to noon if no time specified, as in original baseline
    
    time_match = re.search(r"\b(?:at\s+)(\d+)(?:\:00)?\s*(am|pm)?\b", prompt_lower)
    if not time_match:
        time_match = re.search(r"\b(\d+)(?:\:00)?\s*(am|pm)\b", prompt_lower)
        
    if time_match:
        h = int(time_match.group(1))
        meridiem = time_match.group(2)
        if meridiem == 'pm' and h < 12:
            h += 12
        elif meridiem == 'am' and h == 12:
            h = 0
        hour = h

    if target_date is None:
        target_date = CURRENT_SIMULATED_TIME
        
    target_time = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    lead_time = int((target_time - CURRENT_SIMULATED_TIME).total_seconds() / 3600)
    
    if lead_time < 0:
        lead_time = 0
        
    return target_time.strftime("%Y-%m-%d %H:%M:%S"), lead_time

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
    global forecasting_engine, aether_assistant
    logger.info("Initializing SIH26081 Forecasting System...")
    try:
        model_path = PROJECT_ROOT / "models" / "blender" / "mlp_gating_model"
        logger.info("Loading PyTorch forecasting engine...")
        forecasting_engine = ForecastingEngine(
            config_path=None,
            model_path=model_path
        )
        logger.info("✓ Forecasting engine loaded")

        logger.info("Loading AETHER conversational assistant (this may take 30-60 seconds)...")
        aether_assistant = AETHERAssistant(
            engine=forecasting_engine,
            model_id="Qwen/Qwen2.5-3B-Instruct"
        )
        logger.info("✓ AETHER assistant loaded and ready")

    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        raise

@app.get("/")
async def root():
    index_path = PROJECT_ROOT / "frontend" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "API is operational. Frontend not found."}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "forecasting_engine": "ready" if forecasting_engine else "not initialized",
        "aether_assistant": "ready" if aether_assistant else "not initialized"
    }

@app.post("/api/forecast", response_model=ForecastResponse)
async def get_forecast(request: ForecastRequest):
    if not forecasting_engine:
        raise HTTPException(status_code=503, detail="Forecasting engine not initialized")
    try:
        valid_time = datetime.fromisoformat(request.valid_time.replace(' ', 'T'))
        logger.info(f"Forecast request: lat={request.lat}, lon={request.lon}, valid_time={valid_time}, lead_time={request.lead_time_hours}h")

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
    if not aether_assistant:
        raise HTTPException(status_code=503, detail="AETHER assistant not initialized")

    try:
        prompt_lower = request.prompt.lower()
        logger.info(f"1. AETHER parsed intent/location/time from: '{request.prompt}'")

        # 1. Location Extraction & Geographic Resolution via Geopy
        extracted_area_name = extract_area_name(prompt_lower)
        
        injections = []
        if extracted_area_name:
            mapped_lat, mapped_lon, loc_name = geocode_location(extracted_area_name)
            
            if mapped_lat is not None and mapped_lon is not None:
                # 2. Date/Lead Time Dynamic Resolution
                vt_str, lead_hours = resolve_temporal_parameters(prompt_lower)
                
                area_display = loc_name.split(',')[0] if loc_name else extracted_area_name.title()
                
                injections.append(f"[System override: The user is asking about {area_display}. Use lat {mapped_lat:.4f}, lon {mapped_lon:.4f} for your tool calls. CRITICAL: In your final response, refer to the location ONLY by its name \"{area_display}\". Do not mention the latitude and longitude.]")
                injections.append(f"[System override: The user requested a specific time. Translating to valid_time '{vt_str}' with lead_time_hours {lead_hours}]")
        
        enriched_prompt = request.prompt
        if injections:
            enriched_prompt += " " + " ".join(injections)

        logger.info(f"2. ForecastingEngine execution prepared via AETHER override.")
        
        # Process the query through AETHER (which will then natively invoke ForecastingEngine)
        logger.info(f"3. ForecastingEngine execution started")
        reply = aether_assistant.run_interaction(enriched_prompt)
        logger.info(f"4. External Gemini synthesis started")

        logger.info(f"5. External Gemini response obtained.")

        return ChatResponse(reply=reply)

    except Exception as e:
        logger.error(f"AETHER query failed: {e}")
        raise HTTPException(status_code=500, detail=f"AETHER query failed: {str(e)}")

@app.get("/api/available-times")
async def get_available_times():
    if not forecasting_engine or forecasting_engine.dataset is None:
        raise HTTPException(status_code=503, detail="Forecasting engine not initialized")
    try:
        df = forecasting_engine.dataset
        valid_times = sorted(df['valid_time'].dt.strftime('%Y-%m-%d %H:%M:%S').unique())
        lead_times = sorted(df['lead_time'].unique().tolist())
        lat_min, lat_max = df['latitude'].min(), df['latitude'].max()
        lon_min, lon_max = df['longitude'].min(), df['longitude'].max()
        return {
            "valid_times": valid_times[:50],  
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)