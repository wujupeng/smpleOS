# B5-105: Version Domain Model Specification

**Document ID**: AFX-DM-SPEC-001  
**Version**: 1.0  
**Date**: 2026-06-22  
**Status**: Approved  
**Author**: AeroForge-X Development Team  
**Reviewer**: Big-G Project Manager

---

## 1. Purpose

This document defines the version semantics for all version fields within the AeroForge-X Configuration Management domain model. It resolves the ambiguity identified during EV-3.7 where `block.version` and `design_config.version` coexist with different semantics.

---

## 2. Version Taxonomy

### 2.1 Aggregate Root Version (`block_configurations.version`)

| Property | Value |
|----------|-------|
| **Type** | `bigint` |
| **Default** | `1` |
| **Owner** | Database (never set by application code) |
| **Increment Rule** | Only via `update_block(expected_version=N)` → `version = version + 1` |
| **Semantic Meaning** | The number of **intentional configuration changes** applied to this Block |
| **Analogy** | PLM revision counter (Windchill / Teamcenter / ENOVIA) |

**What increments it:**
- `PATCH /block-configurations/{id}` with `expected_version` parameter
- Any business operation that modifies the Block's configuration state

**What does NOT increment it:**
- `save_block()` (INSERT ON CONFLICT DO NOTHING)
- `update_block()` without `expected_version` (metadata-only updates)
- Repeated reads or cache refreshes

### 2.2 Sub-Configuration Version (`DesignConfiguration.version`, `ManufacturingConfiguration.version`, `OperationalConfiguration.version`)

| Property | Value |
|----------|-------|
| **Type** | `integer` (in-memory dataclass field) |
| **Default** | `1` |
| **Owner** | Domain Service (set during creation/derivation) |
| **Semantic Meaning** | The iteration count within a specific configuration view (Design/Manufacturing/Operational) |
| **Storage** | Currently in-memory only; not persisted to `block_configurations` table |

**Key distinction:**
```
block.version = 3           ← "This Block has been changed 3 times"
design_config.version = 1   ← "The Design view has been derived once"
```

These are **independent counters**. A Block version change does NOT automatically increment sub-configuration versions.

---

## 3. Version Lifecycle

### 3.1 Block Version Lifecycle

```
CREATE block
  → block.version = 1 (database default)

UPDATE block (with expected_version=1)
  → block.version = 2
  → updated_at = NOW()

UPDATE block (with expected_version=2)
  → block.version = 3

UPDATE block (with expected_version=2, stale)
  → 409 VersionConflictError
  → block.version remains 3
```

### 3.2 Sub-Configuration Version Lifecycle

```
CREATE block
  → design_config.version = 1 (initial derivation)
  → manufacturing_config = null
  → operational_config = null

DERIVE manufacturing (from design)
  → manufacturing_config.version = 1

DERIVE operational (from manufacturing)
  → operational_config.version = 1

PROPAGATE design change
  → design_config.version = 2
  → (manufacturing/operational may need re-derivation)
```

---

## 4. Database Schema

### 4.1 `block_configurations` Table

```sql
CREATE TABLE block_configurations (
    block_id                VARCHAR(64)  NOT NULL PRIMARY KEY,
    aircraft_type           VARCHAR(64)  NOT NULL,
    block_name              VARCHAR(32)  NOT NULL,
    design_config_id        VARCHAR(64),
    manufacturing_config_id VARCHAR(64),
    operational_config_id   VARCHAR(64),
    locked                  BOOLEAN      NOT NULL DEFAULT false,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    version                 BIGINT       NOT NULL DEFAULT 1
);
```

### 4.2 Version Column Constraints

- **Protected**: Application code MUST NOT write to `version` column directly
- **Enforced by**: `ProtectedColumnError` exception in Repository layer
- **Increment**: Only via SQL `version = version + 1` within `UPDATE ... WHERE version = $N`
- **Optimistic Lock**: `expected_version` parameter required for version increment

---

## 5. API Contract

### 5.1 Version in Responses

```json
{
    "block_id": "BLK-B737-MAIN-WING",
    "version": 3,
    "design_config_id": "DC-BLK-B737-MAIN-WING-1",
    "locked": false,
    "updated_at": "2026-06-19T12:36:28.129668+00:00"
}
```

**Note**: `version` in the API response is the **Aggregate Root Version** (block_configurations.version), NOT the sub-configuration version.

### 5.2 Version in Update Requests

```json
PATCH /api/v6/aircraft-core/block-configurations/BLK-B737-MAIN-WING
{
    "block_name": "Updated-Wing",
    "expected_version": 3
}
```

- `expected_version` is **removed** from the update payload before applying
- If `expected_version` matches current DB version → update succeeds, version increments
- If `expected_version` does not match → `409 Conflict`

### 5.3 Error Responses

| HTTP Status | Error Type | Condition |
|-------------|-----------|-----------|
| 409 | VersionConflictError | `expected_version` does not match current DB version |
| 422 | ProtectedColumnError | Attempt to write `version`, `created_at`, or `block_id` in update payload |

---

## 6. Version Strategy Summary Table

| Operation | `block.version` | `design_config.version` | `updated_at` |
|-----------|----------------|------------------------|--------------|
| `save_block()` (INSERT) | Set to 1 (DB default) | Set to 1 (Service) | Set by DB |
| `update_block()` (no lock) | No change | N/A | Set by DB |
| `update_block(expected_version=N)` | +1 | N/A | Set by DB |
| `createBlockConfig()` | Set to 1 (via save_block) | Set to 1 (Service) | Set by DB |
| `inheritBlockConfig()` | Set to 1 (new block) | Set to 1 (Service) | Set by DB |
| `deriveManufacturingConfig()` | No change | No change | No change |
| `propagateDesignChange()` | No change* | +1* | No change* |

*Note: Propagation currently operates on in-memory objects. Version increment for propagation is a future enhancement tracked as B5-107.

---

## 7. Known Gaps (Technical Debt)

| ID | Gap | Priority | Target |
|----|-----|----------|--------|
| B5-107 | `propagateDesignChange()` does not increment `block.version` | Medium | EV-4 |
| B5-108 | Sub-configuration versions (`design_config.version` etc.) are not persisted to DB | Medium | EV-4 |
| B5-109 | No version history table (audit trail) | Low | EV-5 |
| B5-110 | `locked` flag does not prevent updates | Medium | EV-4 |

---

## 8. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-19 | `save_block()` uses ON CONFLICT DO NOTHING | Prevents false version increments on re-save |
| 2026-06-19 | `update_block()` without `expected_version` does NOT increment version | Not every update is a configuration change |
| 2026-06-19 | `version` column is protected (ProtectedColumnError) | Prevents application code from bypassing optimistic lock |
| 2026-06-22 | `block.version` and `design_config.version` are independent | Aggregate root version ≠ sub-entity version |

---

## Appendix A: Real System Evidence

Current data in production database (2026-06-22):

```
            block_id            |  aircraft_type   |   block_name   | version | locked 
--------------------------------+------------------+----------------+---------+--------
 BLK-API-TEST-LockTest          | API-TEST         | LockTest-Final |       3 | f
 BLK-CONCURRENCY-TEST-RaceBlock | CONCURRENCY-TEST | RaceBlock      |       2 | t
 BLK-B737-MAIN-WING             | B737             | MAIN-WING      |       3 | f
```

API response for `BLK-B737-MAIN-WING`:

```json
{
    "block_id": "BLK-B737-MAIN-WING",
    "aircraft_type": "B737",
    "block_name": "MAIN-WING",
    "design_config_id": "DC-BLK-B737-MAIN-WING-1",
    "manufacturing_config_id": null,
    "operational_config_id": null,
    "locked": false,
    "created_at": "2026-06-19T10:54:20.311668+00:00",
    "updated_at": "2026-06-19T12:36:28.129668+00:00",
    "version": 3
}
```