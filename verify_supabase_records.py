#!/usr/bin/env python3
"""Verify actual Supabase database records"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.repository import ForecastRepository

repo = ForecastRepository()

if not repo.db.is_available():
    print("✗ Database unavailable")
    sys.exit(1)

print("=" * 80)
print("SUPABASE DATABASE VERIFICATION")
print("=" * 80)

# Query actual records
with repo.db.get_connection() as conn:
    if conn is None:
        print("✗ Connection failed")
        sys.exit(1)
    
    cursor = conn.cursor()
    
    # Check locations
    cursor.execute("SELECT id, name, latitude, longitude FROM locations ORDER BY id DESC LIMIT 5")
    locations = cursor.fetchall()
    print(f"\n--- Locations Table ({len(locations)} recent) ---")
    for loc in locations:
        print(f"ID {loc[0]}: {loc[1]} ({loc[2]}, {loc[3]})")
    
    # Check NWP forecasts
    cursor.execute("""
        SELECT id, model_name, temperature_c, is_live_api, fetched_at 
        FROM nwp_forecasts 
        ORDER BY id DESC LIMIT 5
    """)
    nwp = cursor.fetchall()
    print(f"\n--- NWP Forecasts Table ({len(nwp)} recent) ---")
    for row in nwp:
        print(f"ID {row[0]}: {row[1]} = {row[2]}°C (live: {row[3]}, fetched: {row[4]})")
    
    # Check blended forecasts
    cursor.execute("""
        SELECT id, blended_temperature_c, weight_ifs, weight_gfs, weight_icon, created_at 
        FROM blended_forecasts 
        ORDER BY id DESC LIMIT 5
    """)
    blended = cursor.fetchall()
    print(f"\n--- Blended Forecasts Table ({len(blended)} recent) ---")
    for row in blended:
        weight_sum = float(row[2]) + float(row[3]) + float(row[4])
        print(f"ID {row[0]}: {row[1]}°C | w_IFS={row[2]}, w_GFS={row[3]}, w_ICON={row[4]}")
        print(f"         Weight sum: {weight_sum:.6f} | Created: {row[5]}")
    
    # Check model versions
    cursor.execute("SELECT id, model_name, version, sha256_hash FROM model_versions")
    models = cursor.fetchall()
    print(f"\n--- Model Versions Table ({len(models)} total) ---")
    for m in models:
        print(f"ID {m[0]}: {m[1]} v{m[2]}")
        print(f"         SHA256: {m[3]}")
    
    # Check forecast requests
    cursor.execute("SELECT COUNT(*) FROM forecast_requests WHERE success = true")
    success_count = cursor.fetchone()[0]
    print(f"\n--- Forecast Requests Table ---")
    print(f"Successful requests: {success_count}")

print("\n" + "=" * 80)
print("✓ DATABASE VERIFICATION COMPLETE")
print("=" * 80)
