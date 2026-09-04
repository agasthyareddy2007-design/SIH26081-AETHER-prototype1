-- Migration 001: Initial schema for SIH26081/AETHER forecast persistence
-- Run with: psql <connection_string> -f 001_initial_schema.sql

-- Locations table
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(latitude, longitude)
);

CREATE INDEX idx_locations_coords ON locations(latitude, longitude);

-- Model versions table (tracks MLPGatingNet model provenance)
CREATE TABLE IF NOT EXISTS model_versions (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    sha256_hash VARCHAR(64) NOT NULL UNIQUE,
    architecture VARCHAR(50) NOT NULL,
    trained_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- NWP forecasts table (raw model outputs: IFS, GFS, ICON)
CREATE TABLE IF NOT EXISTS nwp_forecasts (
    id SERIAL PRIMARY KEY,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    model_name VARCHAR(50) NOT NULL,
    model_identifier VARCHAR(100) NOT NULL,
    valid_time TIMESTAMP WITH TIME ZONE NOT NULL,
    lead_time_hours INTEGER NOT NULL,
    temperature_c DECIMAL(6, 2) NOT NULL,
    api_endpoint VARCHAR(255) NOT NULL,
    data_source VARCHAR(100) NOT NULL,
    is_live_api BOOLEAN NOT NULL DEFAULT TRUE,
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(location_id, model_name, valid_time, lead_time_hours)
);

CREATE INDEX idx_nwp_valid_time ON nwp_forecasts(valid_time);
CREATE INDEX idx_nwp_location_model ON nwp_forecasts(location_id, model_name);

-- Blended forecasts table (MLPGatingNet output)
CREATE TABLE IF NOT EXISTS blended_forecasts (
    id SERIAL PRIMARY KEY,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    model_version_id INTEGER NOT NULL REFERENCES model_versions(id),
    valid_time TIMESTAMP WITH TIME ZONE NOT NULL,
    lead_time_hours INTEGER NOT NULL,
    blended_temperature_c DECIMAL(6, 2) NOT NULL,
    weight_ifs DECIMAL(5, 3) NOT NULL CHECK (weight_ifs >= 0 AND weight_ifs <= 1),
    weight_gfs DECIMAL(5, 3) NOT NULL CHECK (weight_gfs >= 0 AND weight_gfs <= 1),
    weight_icon DECIMAL(5, 3) NOT NULL CHECK (weight_icon >= 0 AND weight_icon <= 1),
    forecast_ifs_c DECIMAL(6, 2) NOT NULL,
    forecast_gfs_c DECIMAL(6, 2) NOT NULL,
    forecast_icon_c DECIMAL(6, 2) NOT NULL,
    disagreement DECIMAL(5, 2),
    uncertainty DECIMAL(5, 2),
    confidence VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(location_id, model_version_id, valid_time, lead_time_hours),
    CONSTRAINT weights_sum_to_one CHECK (
        ABS((weight_ifs + weight_gfs + weight_icon) - 1.0) < 0.01
    )
);

CREATE INDEX idx_blended_valid_time ON blended_forecasts(valid_time);
CREATE INDEX idx_blended_location ON blended_forecasts(location_id);

-- Forecast requests table (API access log)
CREATE TABLE IF NOT EXISTS forecast_requests (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    requested_valid_time TIMESTAMP WITH TIME ZONE NOT NULL,
    lead_time_hours INTEGER NOT NULL,
    request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_time_ms INTEGER,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    client_info JSONB
);

CREATE INDEX idx_requests_timestamp ON forecast_requests(request_timestamp);

-- AETHER interactions table (conversational AI queries)
CREATE TABLE IF NOT EXISTS aether_interactions (
    id SERIAL PRIMARY KEY,
    user_query TEXT NOT NULL,
    forecast_id INTEGER REFERENCES blended_forecasts(id),
    response_text TEXT,
    interaction_type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_aether_created ON aether_interactions(created_at);

-- Insert production model version
INSERT INTO model_versions (
    model_name,
    version,
    sha256_hash,
    architecture,
    trained_at,
    metadata
) VALUES (
    'MLPGatingNet',
    '1.0-production',
    '11180fb2b72d49154434ecad3276281b305277d0eeb2098df86d4485d5ad32b4',
    'PyTorch MLP Softmax Gating',
    '2026-09-04 08:00:00+00',
    '{"features": ["IFS", "ICON", "GFS", "hour_sin", "hour_cos", "doy_sin", "doy_cos", "lead_time", "lead_time_sqrt", "latitude", "longitude"], "training_samples": 7000, "validation_samples": 1500, "test_samples": 1500}'::jsonb
) ON CONFLICT (sha256_hash) DO NOTHING;
