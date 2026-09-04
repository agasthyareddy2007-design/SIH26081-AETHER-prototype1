# AIFS Viability Test Report

**Date:** 2026-09-04
**Location:** Hyderabad (Lat: 17.385, Lon: 78.4867)
**Evaluation Period:** August 2026

## Objective
Determine whether genuine historical ECMWF AIFS (0.25°) forecast data—with explicitly accessible initialization times and valid forecast horizons (6h, 12h, 24h)—is legitimately available on Open-Meteo for the SIH26081 project evaluation period, without resorting to fallbacks or synthetic values.

## Testing Methodology
All viable Open-Meteo API endpoints were probed for historical AIFS information (`ecmwf_aifs025`):
1. **Historical Forecast API** (`historical-forecast-api.open-meteo.com`)
2. **Forecast API with `past_days`** (`api.open-meteo.com`)
3. **Historical Weather Archive API** (`archive-api.open-meteo.com`)
4. **Ensemble API** (`ensemble-api.open-meteo.com`)

In parallel, we tested reference viability and independence for ECMWF IFS (`ecmwf_ifs025`), NOAA GFS (`gfs_seamless`), and the independent reanalysis target ERA5-Land (`era5_land`).

## Findings 

### 1. ECMWF AIFS (0.25°)
- **Result:** **UNAVAILABLE**
- **Details:** The Open-Meteo historical archive endpoints return 100% `null` values for `ecmwf_aifs025` across August 2026. While AIFS data successfully renders on the Live/Ensemble APIs for current and future horizons, historical archives are not populated for our evaluation window.
- **Missing Rate:** 100%
- **Sample Values:** `[null, null, null, ...]`

### 2. Candidate Models (IFS and GFS)
- **ECMWF IFS (0.25°):** Real historical forecast runs (with initialization times and lead times) are fully populated and valid.
- **NOAA GFS Seamless:** Real historical forecast runs are fully populated and valid.

### 3. Reference Target (ERA5-Land)
- **Result:** **VALID & INDEPENDENT**
- **Details:** The `era5_land` reanalysis data is fully available, structurally sound (numerical values, non-zero variance), and numerically independent from IFS, AIFS, and GFS operational values.

## Viability Verdict
**Verdict:** B) AIFS HISTORICAL FORECAST NOT AVAILABLE

The historical evaluation pipeline cannot logically proceed using `ecmwf_aifs025` without resorting to fake/constant values (e.g. 25.0°C), which is strictly forbidden. 

## Legitimate Alternatives
Rather than fabricating synthetic data or altering the SIH benchmark illegitimately, one of the following fully-archived, high-quality candidate replacements must be chosen for the three-model ensemble:

1. **DWD ICON Global 11km (`icon_global`)**
   - *Tradeoff:* We replace the experimental AI-NWP model with one of the most accurate traditional deterministic physics-based global NWPs. It provides robust historical archive support on Open-Meteo, allowing genuine calculation of initialization + lead time evaluations.
2. **CMA GRAPES Global (`cma_grapes_global`)**
   - *Tradeoff:* Another established high-resolution global deterministic model with proven historical data availability.

Alternatively, we could shift the entire experiment window away from Historical Archives to a live rolling test (collecting live AIFS Ensemble data moving forward), but this would require waiting days to accumulate a valid dataset.

## Conclusion
Awaiting final user instruction on candidate substitution before modifying the data adapter pipeline.
