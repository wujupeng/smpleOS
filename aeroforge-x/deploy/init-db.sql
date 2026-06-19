CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Phase 3 schemas
CREATE SCHEMA IF NOT EXISTS supply_chain;
CREATE SCHEMA IF NOT EXISTS delivery;
CREATE SCHEMA IF NOT EXISTS qms;
CREATE SCHEMA IF NOT EXISTS traceability;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Phase 4 schemas
CREATE SCHEMA IF NOT EXISTS certification;
CREATE SCHEMA IF NOT EXISTS knowledge;
CREATE SCHEMA IF NOT EXISTS ecosystem;
CREATE SCHEMA IF NOT EXISTS data_lake;
CREATE SCHEMA IF NOT EXISTS twin_fusion;

-- Keycloak realm placeholder
-- Run Keycloak realm import via admin API after first boot
