CREATE TABLE IF NOT EXISTS raw_telemetry (
    id SERIAL PRIMARY KEY,
    mission_id UUID,
    ingest_time TIMESTAMP DEFAULT NOW(),
    flight_payload JSONB
);

CREATE INDEX idx_mission_id ON raw_telemetry(mission_id);