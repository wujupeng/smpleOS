-- AeroForge-X v6.3 Optimistic Lock Version Fields
-- Adds version columns to core tables for optimistic concurrency control

BEGIN;

ALTER TABLE block_configurations
    ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 1;

ALTER TABLE serial_number_configurations
    ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 1;

ALTER TABLE configuration_baselines
    ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 1;

ALTER TABLE supplier_profiles
    ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 1;

ALTER TABLE material_lots
    ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 1;

COMMIT;