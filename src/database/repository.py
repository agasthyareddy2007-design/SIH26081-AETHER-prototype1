"""
Database repository for forecast persistence
Clean data-access layer for Supabase PostgreSQL
"""
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from decimal import Decimal

from .connection import get_db_connection

logger = logging.getLogger("aether.database.repository")

class ForecastRepository:
    """
    Repository for persisting forecasts to PostgreSQL.
    All methods gracefully handle database unavailability.
    """

    def __init__(self):
        self.db = get_db_connection()

    def _get_or_create_location(self, conn, lat: float, lon: float, name: str = None) -> Optional[int]:
        """Get or create location, returns location_id or None if DB unavailable"""
        if conn is None:
            return None

        try:
            cursor = conn.cursor()

            # Try to get existing location
            cursor.execute(
                "SELECT id FROM locations WHERE latitude = %s AND longitude = %s",
                (round(lat, 6), round(lon, 6))
            )
            result = cursor.fetchone()

            if result:
                return result[0]

            # Create new location
            if name is None:
                name = f"Location ({lat:.4f}, {lon:.4f})"

            cursor.execute(
                """INSERT INTO locations (name, latitude, longitude)
                   VALUES (%s, %s, %s) RETURNING id""",
                (name, round(lat, 6), round(lon, 6))
            )
            return cursor.fetchone()[0]

        except Exception as e:
            logger.error(f"Failed to get/create location: {type(e).__name__}")
            return None

    def _get_model_version_id(self, conn, sha256_hash: str) -> Optional[int]:
        """Get model version ID by SHA256 hash"""
        if conn is None:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM model_versions WHERE sha256_hash = %s",
                (sha256_hash,)
            )
            result = cursor.fetchone()
            return result[0] if result else None

        except Exception as e:
            logger.error(f"Failed to get model version: {type(e).__name__}")
            return None

    def save_nwp_forecasts(
        self,
        lat: float,
        lon: float,
        valid_time: datetime,
        lead_time_hours: int,
        forecasts: Dict[str, float],
        provenance: Dict[str, Dict]
    ) -> bool:
        """
        Save raw NWP forecasts (IFS, GFS, ICON) to database.
        Returns True if successful, False if database unavailable.
        """
        with self.db.get_connection() as conn:
            if conn is None:
                logger.warning("Database unavailable - NWP forecasts not persisted")
                return False

            try:
                location_id = self._get_or_create_location(conn, lat, lon)
                if location_id is None:
                    return False

                cursor = conn.cursor()

                for model_name, temperature in forecasts.items():
                    prov = provenance.get(model_name, {})

                    cursor.execute(
                        """INSERT INTO nwp_forecasts (
                            location_id, model_name, model_identifier,
                            valid_time, lead_time_hours, temperature_c,
                            api_endpoint, data_source, is_live_api, fetched_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (location_id, model_name, valid_time, lead_time_hours)
                        DO UPDATE SET
                            temperature_c = EXCLUDED.temperature_c,
                            fetched_at = EXCLUDED.fetched_at""",
                        (
                            location_id,
                            model_name,
                            prov.get('model_identifier', model_name.lower()),
                            valid_time,
                            lead_time_hours,
                            round(temperature, 2),
                            prov.get('api_endpoint', ''),
                            prov.get('data_source', 'UNKNOWN'),
                            prov.get('live_api', True),
                            datetime.fromisoformat(prov.get('fetched_at', datetime.utcnow().isoformat()))
                        )
                    )

                logger.info(f"Persisted {len(forecasts)} NWP forecasts for location_id={location_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to save NWP forecasts: {type(e).__name__}")
                return False

    def save_blended_forecast(
        self,
        lat: float,
        lon: float,
        valid_time: datetime,
        lead_time_hours: int,
        blended_temp: float,
        weights: Dict[str, float],
        model_forecasts: Dict[str, float],
        uncertainty: Dict[str, any],
        model_sha256: str
    ) -> bool:
        """
        Save blended forecast (MLPGatingNet output) to database.
        Returns True if successful, False if database unavailable.
        """
        with self.db.get_connection() as conn:
            if conn is None:
                logger.warning("Database unavailable - blended forecast not persisted")
                return False

            try:
                location_id = self._get_or_create_location(conn, lat, lon)
                model_version_id = self._get_model_version_id(conn, model_sha256)

                if location_id is None or model_version_id is None:
                    logger.error("Failed to resolve location_id or model_version_id")
                    return False

                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO blended_forecasts (
                        location_id, model_version_id, valid_time, lead_time_hours,
                        blended_temperature_c, weight_ifs, weight_gfs, weight_icon,
                        forecast_ifs_c, forecast_gfs_c, forecast_icon_c,
                        disagreement, uncertainty, confidence
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (location_id, model_version_id, valid_time, lead_time_hours)
                    DO UPDATE SET
                        blended_temperature_c = EXCLUDED.blended_temperature_c,
                        weight_ifs = EXCLUDED.weight_ifs,
                        weight_gfs = EXCLUDED.weight_gfs,
                        weight_icon = EXCLUDED.weight_icon,
                        disagreement = EXCLUDED.disagreement,
                        uncertainty = EXCLUDED.uncertainty,
                        confidence = EXCLUDED.confidence""",
                    (
                        location_id,
                        model_version_id,
                        valid_time,
                        lead_time_hours,
                        round(blended_temp, 2),
                        round(weights.get('IFS', 0), 3),
                        round(weights.get('GFS', 0), 3),
                        round(weights.get('ICON', 0), 3),
                        round(model_forecasts.get('IFS', 0), 2),
                        round(model_forecasts.get('GFS', 0), 2),
                        round(model_forecasts.get('ICON', 0), 2),
                        round(uncertainty.get('model_spread_std', 0), 2),
                        round(uncertainty.get('uncertainty_value', 0), 2),
                        uncertainty.get('confidence_level', 'Unknown')
                    )
                )

                logger.info(f"Persisted blended forecast for location_id={location_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to save blended forecast: {type(e).__name__}")
                return False

    def log_forecast_request(
        self,
        lat: float,
        lon: float,
        valid_time: datetime,
        lead_time_hours: int,
        success: bool,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Log a forecast request for monitoring"""
        with self.db.get_connection() as conn:
            if conn is None:
                return False

            try:
                location_id = self._get_or_create_location(conn, lat, lon)
                if location_id is None:
                    return False

                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO forecast_requests (
                        location_id, requested_valid_time, lead_time_hours,
                        response_time_ms, success, error_message
                    ) VALUES (%s, %s, %s, %s, %s, %s)""",
                    (location_id, valid_time, lead_time_hours, response_time_ms, success, error_message)
                )
                return True

            except Exception as e:
                logger.error(f"Failed to log request: {type(e).__name__}")
                return False

    def get_recent_forecasts(self, lat: float, lon: float, limit: int = 10) -> List[Dict]:
        """Retrieve recent blended forecasts for a location"""
        with self.db.get_connection() as conn:
            if conn is None:
                return []

            try:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT
                        bf.valid_time, bf.lead_time_hours, bf.blended_temperature_c,
                        bf.weight_ifs, bf.weight_gfs, bf.weight_icon,
                        bf.forecast_ifs_c, bf.forecast_gfs_c, bf.forecast_icon_c,
                        bf.disagreement, bf.uncertainty, bf.confidence,
                        bf.created_at, mv.sha256_hash
                    FROM blended_forecasts bf
                    JOIN locations l ON bf.location_id = l.id
                    JOIN model_versions mv ON bf.model_version_id = mv.id
                    WHERE l.latitude = %s AND l.longitude = %s
                    ORDER BY bf.created_at DESC
                    LIMIT %s""",
                    (round(lat, 6), round(lon, 6), limit)
                )

                results = []
                for row in cursor.fetchall():
                    results.append({
                        'valid_time': row[0],
                        'lead_time_hours': row[1],
                        'blended_temperature_c': float(row[2]),
                        'weights': {'IFS': float(row[3]), 'GFS': float(row[4]), 'ICON': float(row[5])},
                        'forecasts': {'IFS': float(row[6]), 'GFS': float(row[7]), 'ICON': float(row[8])},
                        'disagreement': float(row[9]) if row[9] else None,
                        'uncertainty': float(row[10]) if row[10] else None,
                        'confidence': row[11],
                        'created_at': row[12],
                        'model_sha256': row[13]
                    })

                return results

            except Exception as e:
                logger.error(f"Failed to retrieve forecasts: {type(e).__name__}")
                return []
