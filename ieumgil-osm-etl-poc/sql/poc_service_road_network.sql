CREATE SCHEMA IF NOT EXISTS poc_service_mapping;
CREATE EXTENSION IF NOT EXISTS postgis;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'surface_type_enum'
          AND n.nspname = 'poc_service_mapping'
    ) THEN
        CREATE TYPE poc_service_mapping.surface_type_enum AS ENUM (
            'ASPHALT',
            'BLOCK',
            'CONCRETE',
            'GRAVEL',
            'UNPAVED',
            'UNKNOWN'
        );
    END IF;
END$$;

DROP TABLE IF EXISTS poc_service_mapping.road_segments;
DROP TABLE IF EXISTS poc_service_mapping.road_nodes;

CREATE TABLE poc_service_mapping.road_nodes (
    "vertexId" BIGSERIAL PRIMARY KEY,
    osm_node_id BIGINT NULL,
    point geometry(Point, 4326) NOT NULL
);

CREATE TABLE poc_service_mapping.road_segments (
    "edgeId" BIGSERIAL PRIMARY KEY,
    from_node_id BIGINT NOT NULL REFERENCES poc_service_mapping.road_nodes("vertexId"),
    to_node_id BIGINT NOT NULL REFERENCES poc_service_mapping.road_nodes("vertexId"),
    geom geometry(LineString, 4326) NOT NULL,
    length_meter NUMERIC(10, 2) NOT NULL,
    avg_slope_percent NUMERIC(6, 2) NULL,
    width_meter NUMERIC(6, 2) NULL,
    has_stairs BOOLEAN NOT NULL DEFAULT false,
    has_curb_gap BOOLEAN NOT NULL DEFAULT false,
    has_elevator BOOLEAN NOT NULL DEFAULT false,
    has_crosswalk BOOLEAN NOT NULL DEFAULT false,
    has_signal BOOLEAN NOT NULL DEFAULT false,
    has_audio_signal BOOLEAN NOT NULL DEFAULT false,
    has_braille_block BOOLEAN NOT NULL DEFAULT false,
    surface_type poc_service_mapping.surface_type_enum NULL DEFAULT 'UNKNOWN',
    "vertexId" BIGINT NOT NULL REFERENCES poc_service_mapping.road_nodes("vertexId")
);
