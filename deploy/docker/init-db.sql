-- Lacuna Production Database Initialization
-- Creates required extensions and optimizes for production workloads

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Create schema
CREATE SCHEMA IF NOT EXISTS lacuna;

-- Set default search path
ALTER DATABASE lacuna SET search_path TO lacuna, public;

-- Create audit log partitioning function (for high-volume deployments)
CREATE OR REPLACE FUNCTION create_audit_partition()
RETURNS void AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- Create partitions for next 12 months
    FOR i IN 0..11 LOOP
        partition_date := DATE_TRUNC('month', CURRENT_DATE) + (i || ' months')::INTERVAL;
        partition_name := 'audit_logs_' || TO_CHAR(partition_date, 'YYYY_MM');
        start_date := partition_date;
        end_date := partition_date + '1 month'::INTERVAL;

        -- Check if partition exists
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = 'lacuna' AND tablename = partition_name
        ) THEN
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS lacuna.%I PARTITION OF lacuna.audit_logs
                FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA lacuna TO lacuna;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA lacuna TO lacuna;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA lacuna TO lacuna;
ALTER DEFAULT PRIVILEGES IN SCHEMA lacuna GRANT ALL ON TABLES TO lacuna;
ALTER DEFAULT PRIVILEGES IN SCHEMA lacuna GRANT ALL ON SEQUENCES TO lacuna;
