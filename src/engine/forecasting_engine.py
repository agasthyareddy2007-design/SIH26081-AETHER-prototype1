import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import math
import time

from src.blending.dynamic_blender import DynamicBlender
from src.uncertainty.estimator import UncertaintyEstimator
from src.data.openmeteo_client import get_open_meteo_client
from src.database.repository import ForecastRepository

# Production model SHA256 - MUST remain unchanged
PRODUCTION_MODEL_SHA256 = "11180fb2b72d49154434ecad3276281b305277d0eeb2098df86d4485d5ad32b4"

class ForecastingEngine:
    def __init__(self, config_path: Path, model_path: Path, enable_persistence: bool = True):
        self.logger = logging.getLogger("aether.engine")
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.blender = DynamicBlender()
        self.blender.load(model_path)
        self.uncertainty_estimator = UncertaintyEstimator()
        self.om_client = get_open_meteo_client(self.project_root / "data" / "raw" / "om_cache")
        self.dataset = None

        # Database persistence (optional, gracefully degrades if unavailable)
        self.enable_persistence = enable_persistence
        self.repository = ForecastRepository() if enable_persistence else None

        self.logger.info("Real Forecasting Engine initialized")
        if enable_persistence:
            if self.repository and self.repository.db.is_available():
                self.logger.info("Database persistence enabled")
            else:
                self.logger.warning("Database unavailable - forecasting will continue without persistence")

    def _fetch_live_api(self, valid_time: datetime, lat: float, lon: float, lead_time_hours: int) -> Tuple[Dict[str, float], Dict]:
        date_str = valid_time.strftime('%Y-%m-%d')
        vt_str = valid_time.strftime('%Y-%m-%dT%H:00')
        out = {}
        provenance = {}

        # Important audit fix: Distinguish future from past dynamically
        is_future = valid_time > datetime.utcnow()

        if is_future:
            base_url = "https://api.open-meteo.com/v1/forecast"
            api_type = "LIVE FUTURE FORECAST DATA"
        else:
            base_url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
            api_type = "HISTORICAL FORECAST DATA"

        models = [
            ("IFS", "ecmwf_ifs025", base_url),
            ("GFS", "gfs_seamless", base_url),
            ("ICON", "icon_seamless", base_url)
        ]

        for name, slug, endpoint in models:
            params = {
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "start_date": date_str,
                "end_date": date_str,
                "hourly": "temperature_2m",
                "models": slug
            }
            try:
                res = self.om_client.fetch(endpoint, params)
                if isinstance(res, list):
                    res = res[0]
                hourly = res.get("hourly", {})
                times = hourly.get("time", [])
                temps = hourly.get("temperature_2m", [])

                if vt_str not in times:
                    raise ValueError(f"Time {vt_str} not found in API response for {name}")
                idx = times.index(vt_str)
                val = temps[idx]

                if val is None or math.isnan(val):
                    raise ValueError(f"API returned null/NaN for {name} at {vt_str}")

                out[name] = val
                provenance[name] = {
                    "data_source": api_type,
                    "api_endpoint": endpoint,
                    "model_identifier": slug,
                    "fetched_at": datetime.utcnow().isoformat(),
                    "forecast_valid_time": vt_str,
                    "lead_hours": lead_time_hours,
                    "live_api": True if is_future else False
                }
            except Exception as e:
                self.logger.error(f"Live fetch failed for {name}: {e}")
                # No synthetic fallback anymore. Explicit error.
                raise ValueError(f"NWP API Failure: {name} failed to return valid data. Error: {str(e)}")

        return out, provenance

    def predict_forecast(
        self,
        valid_time: datetime,
        lead_time_hours: int,
        lat: float,
        lon: float
    ) -> Dict:
        start_time = time.time()
        self.logger.info(f"Pinging Live Open-Meteo APIs for lat={lat} lon={lon} valid_time={valid_time}")

        # 1. Fetch live models
        model_forecasts, provenance_info = self._fetch_live_api(valid_time, lat, lon, lead_time_hours)

        # 2. Build temporal features
        hour = valid_time.hour
        doy = valid_time.timetuple().tm_yday
        lead_time = lead_time_hours

        row = {
            'valid_time': valid_time,
            'lead_time': lead_time,
            'latitude': lat,
            'longitude': lon,
            'IFS': model_forecasts['IFS'],
            'ICON': model_forecasts['ICON'],
            'GFS': model_forecasts['GFS'],
            'hour_sin': np.sin(2 * np.pi * hour / 24.0),
            'hour_cos': np.cos(2 * np.pi * hour / 24.0),
            'doy_sin': np.sin(2 * np.pi * doy / 365.25),
            'doy_cos': np.cos(2 * np.pi * doy / 365.25),
            'lead_time_sqrt': np.sqrt(lead_time)
        }

        features = ['IFS', 'ICON', 'GFS', 'hour_sin', 'hour_cos', 'doy_sin', 'doy_cos', 'lead_time', 'lead_time_sqrt', 'latitude', 'longitude']
        df_input = pd.DataFrame([[row[f] for f in features]], columns=features)

        weights_dict = self.blender.predict_weights(df_input)
        weights = {k: float(v[0]) for k, v in weights_dict.items()}
        blended_forecast = float(self.blender.predict(df_input)[0])

        uncertainty = self.uncertainty_estimator.estimate(
            model_forecasts,
            {'lead_time': int(row['lead_time'])}
        )

        response_time_ms = int((time.time() - start_time) * 1000)

        # 3. Persist to database (optional, non-blocking)
        persistence_status = "disabled"
        if self.enable_persistence and self.repository:
            try:
                # Save NWP forecasts
                nwp_persisted = self.repository.save_nwp_forecasts(
                    lat=lat, lon=lon,
                    valid_time=valid_time,
                    lead_time_hours=lead_time_hours,
                    forecasts=model_forecasts,
                    provenance=provenance_info
                )

                # Save blended forecast
                blend_persisted = self.repository.save_blended_forecast(
                    lat=lat, lon=lon,
                    valid_time=valid_time,
                    lead_time_hours=lead_time_hours,
                    blended_temp=blended_forecast,
                    weights=weights,
                    model_forecasts=model_forecasts,
                    uncertainty=uncertainty,
                    model_sha256=PRODUCTION_MODEL_SHA256
                )

                # Log request
                self.repository.log_forecast_request(
                    lat=lat, lon=lon,
                    valid_time=valid_time,
                    lead_time_hours=lead_time_hours,
                    success=True,
                    response_time_ms=response_time_ms
                )

                if nwp_persisted and blend_persisted:
                    persistence_status = "success"
                else:
                    persistence_status = "partial_failure"

            except Exception as e:
                self.logger.warning(f"Database persistence failed (non-critical): {type(e).__name__}")
                persistence_status = "failed"

        # Return forecast result with persistence metadata
        result = {
            'forecast': round(blended_forecast, 2),
            'unit': 'C',
            'valid_time': valid_time.isoformat(),
            'lead_time_hours': int(row['lead_time']),
            'location': {'latitude': lat, 'longitude': lon, 'requested_lat': lat, 'requested_lon': lon},
            'model_weights': {k: round(v, 3) for k, v in weights.items()},
            'model_forecasts': {k: round(v, 2) for k, v in model_forecasts.items()},
            'disagreement': round(uncertainty['model_spread_std'], 2),
            'uncertainty': round(uncertainty['uncertainty_value'], 2),
            'confidence': uncertainty['confidence_level'],
            'reference_value': None,
            'provenance': provenance_info,
            'persistence_status': persistence_status
        }

        return result

    def get_model_weights(self, valid_time: datetime, lead_time_hours: int, lat: float, lon: float) -> Dict:
        res = self.predict_forecast(valid_time, lead_time_hours, lat, lon)
        return {
            'model_weights': res['model_weights'],
            'model_forecasts': res['model_forecasts'],
            'explanation': "The PyTorch Dynamic MLP uses a Softmax Gating Network to allocate explicit weights based on historical real data error minimization."
        }

    def get_model_comparison(self, valid_time: datetime, lead_time_hours: int, lat: float, lon: float) -> Dict:
        res = self.predict_forecast(valid_time, lead_time_hours, lat, lon)
        return {
            'forecasts': res['model_forecasts'],
            'weights': res['model_weights'],
            'disagreement': res['disagreement']
        }

    def get_forecast_explanation(self, valid_time: datetime, lead_time_hours: int, lat: float, lon: float) -> Dict:
        forecast_result = self.predict_forecast(valid_time, lead_time_hours, lat, lon)
        weights = forecast_result['model_weights']
        primary = max(weights.items(), key=lambda x: x[1])

        return {
            'blended_temperature': forecast_result['forecast'],
            'primary_model': primary[0],
            'primary_weight': primary[1],
            'reasoning': f"The neural network assigned the highest weight ({primary[1]:.1%}) to {primary[0]} for this forecasting context based on historical real data optimization.",
            'confidence': forecast_result['confidence'],
            'disagreement': forecast_result['disagreement'],
            'provenance': forecast_result['provenance']
        }

    def get_uncertainty(self, valid_time: datetime, lead_time_hours: int, lat: float, lon: float) -> Dict:
        res = self.predict_forecast(valid_time, lead_time_hours, lat, lon)
        return {
            'uncertainty_value': res['uncertainty'],
            'confidence_level': res['confidence'],
            'disagreement_std': res['disagreement']
        }

    def get_recent_forecasts(self, lat: float, lon: float, limit: int = 10) -> List[Dict]:
        """Retrieve recent persisted forecasts for a location"""
        if not self.enable_persistence or not self.repository:
            return []

        return self.repository.get_recent_forecasts(lat, lon, limit)
