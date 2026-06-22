# AeroForge-X Migration Report

- **Date**: _(auto-generated)_
- **PostgreSQL**: localhost:5432/aeroforge
- **TimescaleDB**: localhost:5433/aeroforge_ts

---

## Phase 1: v2.0 Base Tables (PostgreSQL)

### v2.0: 001_aircraft_core_tables.sql
- **File**: `001_aircraft_core_tables.sql`
- **Status**: _PENDING_

### v2.0: 002_workflow_engine_tables.sql
- **File**: `002_workflow_engine_tables.sql`
- **Status**: _PENDING_

### v2.0: 003_physics_twin_tables.sql
- **File**: `003_physics_twin_tables.sql`
- **Status**: _PENDING_

## Phase 2: v2.0 TimescaleDB Tables

### v2.0 TimescaleDB: 004_timescale_twin_tables.sql
- **File**: `004_timescale_twin_tables.sql`
- **Status**: _PENDING_

## Phase 3: v6.0 Tables (PostgreSQL)

### v6.0: 001_physics_twin_v6_tables.sql
- **File**: `001_physics_twin_v6_tables.sql`
- **Status**: _PENDING_

### v6.0: 002_aircraft_core_v6_tables.sql
- **File**: `002_aircraft_core_v6_tables.sql`
- **Status**: _PENDING_

## Phase 4: v6.0 TimescaleDB Tables

### v6.0 TimescaleDB: 003_timescale_v6_tables.sql
- **File**: `003_timescale_v6_tables.sql`
- **Status**: _PENDING_

## Phase 5: V6.1 Tables (PostgreSQL)

### V6.1: 004_v61_physics_twin_tables.sql
- **File**: `004_v61_physics_twin_tables.sql`
- **Status**: _PENDING_

### V6.1: 005_v61_aircraft_core_tables.sql
- **File**: `005_v61_aircraft_core_tables.sql`
- **Status**: _PENDING_

## Phase 6: v6.2 Configuration UUID Tables (PostgreSQL)

### v6.2: 006_configuration_uuid_tables.sql
- **File**: `006_configuration_uuid_tables.sql`
- **Status**: _PENDING_

---

## Notes

- Neo4j schema is initialized by init-neo4j container in docker-compose
- NATS streams are initialized by init-nats container in docker-compose
- MinIO buckets are initialized by init-minio container in docker-compose