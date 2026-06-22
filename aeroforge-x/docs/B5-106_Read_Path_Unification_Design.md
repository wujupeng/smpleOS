# B5-106: Read Path Unification Design

**Document ID**: AFX-RP-DESIGN-001  
**Version**: 1.0  
**Date**: 2026-06-22  
**Status**: Draft  
**Author**: AeroForge-X Development Team  
**Reviewer**: Big-G Project Manager

---

## 1. Purpose

This document defines the unified read path architecture for AeroForge-X Configuration Management. It resolves the inconsistencies identified during EV-3.7 where different API endpoints follow different read paths (some bypass cache, some have no DB fallback), leading to data format inconsistency, reliability issues, and maintenance burden.

---

## 2. Problem Statement

### 2.1 Current Read Path Inconsistencies

| Issue | Severity | Description |
|-------|----------|-------------|
| **P1**: `GET /block-configurations/{id}` bypasses cache | HIGH | Directly calls `repo.get_block()`, returns raw DB dict instead of domain model. Other endpoints go through Service cache. |
| **P2**: `detectConfigConflicts()` has no DB fallback | HIGH | Only reads `_blocks`/`_sns` cache. After service restart, always fails even if DB has data. |
| **P3**: `compareBaselines()` has no DB fallback | MEDIUM | Only reads `_baselines` cache. Same restart-vulnerability as P2. |
| **P4**: Baseline cache has no invalidation | MEDIUM | `_baselines` dict only grows, never evicted. Stale data after updates. |
| **P5**: Cache backfill produces incomplete objects | MEDIUM | `_block_from_dict()` reconstructs domain objects without `configuration_items` detail. |
| **P6**: Multi-worker cache inconsistency | LOW | Module-level singleton caches are per-process. Currently acceptable (single worker). |

### 2.2 Current Architecture (As-Is)

```
Controller                          Service                          Repository
─────────                           ───────                          ──────────

GET /block-configurations/{id}
  └── repo.get_block(id) ─────────────────────────────────────────→ DB
      [BYPASSES CACHE — returns raw dict]

GET /config-hierarchies/{type}
  └── service.getConfigHierarchy(type)
      ├── cache HIT → return cached
      └── cache MISS → repo.list_blocks() + repo.list_sns() ──────→ DB
                → backfill _blocks, _sns, _hierarchies

GET /configs/{id}/inconsistencies
  └── service.getBlock(id)
      ├── cache HIT → return cached
      └── cache MISS → repo.get_block(id) ────────────────────────→ DB
      → propagation.detectInconsistencies(block)

POST /config-conflicts/detect
  └── service.detectConfigConflicts(block_id, sn_id)
      ├── _blocks[id] missing → ValueError [NO DB FALLBACK]
      └── _sns[id] missing → ValueError [NO DB FALLBACK]

POST /baselines/compare
  └── baseline_service.compareBaselines(id1, id2)
      ├── _baselines[id1] missing → ValueError [NO DB FALLBACK]
      └── _baselines[id2] missing → ValueError [NO DB FALLBACK]
```

---

## 3. Design Decisions

### 3.1 Decision: Unified Read Path — "Service-First with Cache-Aside"

**Principle**: All reads must go through the Service layer. The Controller never directly accesses the Repository for reads.

**Rationale**:
- Eliminates P1 (bypass inconsistency)
- Single point of control for caching, transformation, and validation
- Consistent data format (domain model `to_dict()`) across all endpoints
- Future-ready: if we need to add cross-cutting concerns (authorization, audit, rate-limit), they go in one place

### 3.2 Decision: All Cache-Miss Reads Must Fall Through to DB

**Principle**: Every Service read method that checks cache must have a DB fallback via Repository.

**Rationale**:
- Eliminates P2, P3 (no-DB-fallback methods)
- Service restart should not cause "data not found" errors when DB has data
- Cache is an optimization, not a source of truth

### 3.3 Decision: Cache Invalidation via Explicit Event Points

**Principle**: Cache invalidation happens at well-defined mutation points, not via TTL or background sync.

**Rationale**:
- Fixes P4 (baseline cache never invalidated)
- Simple and deterministic — easy to reason about correctness
- Consistent with current `invalidate_cache()` approach, just needs to be extended

### 3.4 Decision: Defer Read Model / CQRS to EV-5+

**Principle**: No new infrastructure (Redis, Read Model tables, CQRS projections) in EV-4.

**Rationale**:
- Current in-memory Cache-Aside is sufficient for TRL 5
- P5 (incomplete cache backfill) can be mitigated by fixing `_block_from_dict()` without architectural change
- P6 (multi-worker) is not a concern at current scale
- Adding Redis or Read Model tables would violate the "no new infrastructure" constraint

---

## 4. Target Architecture (To-Be)

### 4.1 Read Path Rules

```
Rule 1: Controller → Service → (Cache? → Repository → DB)
Rule 2: Never: Controller → Repository (for reads)
Rule 3: Every cache-check must have a DB fallback
Rule 4: Every mutation must trigger cache invalidation
Rule 5: Return domain model (to_dict()) from Service, never raw DB rows
```

### 4.2 Target Architecture Diagram

```
Controller                          Service                          Repository
─────────                           ───────                          ──────────

GET /block-configurations/{id}
  └── service.getBlock(id)
      ├── _blocks[id] HIT → return domain model
      └── MISS → repo.get_block(id) ──────────────────────────────→ DB
                → backfill _blocks → return domain model

GET /config-hierarchies/{type}
  └── service.getConfigHierarchy(type)
      ├── _hierarchies[type] HIT → return cached
      └── MISS → repo.list_blocks() + repo.list_sns() ────────────→ DB
                → backfill all caches → return hierarchy

GET /configs/{id}/inconsistencies
  └── service.getBlock(id)                    [unified — same as above]
      → propagation.detectInconsistencies(block)

POST /config-conflicts/detect
  └── service.detectConfigConflicts(block_id, sn_id)
      ├── service.getBlock(block_id)          [unified — has DB fallback]
      ├── service.getSN(sn_id)                [unified — has DB fallback]
      └── compute conflict report

POST /baselines/compare
  └── baseline_service.compareBaselines(id1, id2)
      ├── baseline_service.getBaseline(id1)   [unified — has DB fallback]
      └── baseline_service.getBaseline(id2)   [unified — has DB fallback]
```

### 4.3 Cache Invalidation Map

| Mutation | Invalidated Caches | Scope |
|----------|-------------------|-------|
| `PATCH /block-configurations/{id}` | `_blocks[id]`, `_hierarchies[aircraft_type]`, related `_sns[*]` | Already implemented |
| `POST /block-configurations` (create) | `_hierarchies[aircraft_type]` | Already implemented (write-through) |
| `PATCH /serial-number-configurations/{id}` | `_sns[sn_id]`, `_hierarchies[aircraft_type]` | **NEW — to be added** |
| `POST /baselines/establish` | `_baselines[baseline_id]` | Already implemented (write-through) |
| `PATCH /baselines/{id}` | `_baselines[baseline_id]` | **NEW — to be added** |

---

## 5. Implementation Plan

### 5.1 Fix P1: `GET /block-configurations/{id}` — Route Through Service

**File**: `configuration_controller.py`

**Before**:
```python
@router.get("/block-configurations/{block_id}")
async def get_block_config(block_id: str):
    repo = await _ensure_repo()
    block = await repo.get_block(block_id)
    if block is None:
        raise HTTPException(status_code=404, detail=f"Block not found: {block_id}")
    return block
```

**After**:
```python
@router.get("/block-configurations/{block_id}")
async def get_block_config(block_id: str):
    block = await _config_service.getBlock(block_id)
    if block is None:
        raise HTTPException(status_code=404, detail=f"Block not found: {block_id}")
    return block.to_dict()
```

**Impact**: Returns domain model format (consistent with other endpoints). Benefits from cache. No behavior change for consumers (field names are the same).

### 5.2 Fix P2: `detectConfigConflicts()` — Add DB Fallback

**File**: `configuration_manager_service.py`

**Before**:
```python
def detectConfigConflicts(self, block_id: str, sn_id: str) -> ConflictResolutionReport:
    if block_id not in self._blocks:
        raise ValueError(f"Block not found: {block_id}")
    if sn_id not in self._sns:
        raise ValueError(f"SN not found: {sn_id}")
    block = self._blocks[block_id]
    sn = self._sns[sn_id]
```

**After**:
```python
async def detectConfigConflicts(self, block_id: str, sn_id: str) -> ConflictResolutionReport:
    block = await self.getBlock(block_id)
    if block is None:
        raise ValueError(f"Block not found: {block_id}")
    sn = await self.getSN(sn_id)
    if sn is None:
        raise ValueError(f"SN not found: {sn_id}")
```

**Impact**: Method becomes `async` (callers must `await`). Uses existing `getBlock()`/`getSN()` which have Cache-Aside + DB fallback.

### 5.3 Fix P3: `compareBaselines()` — Add DB Fallback

**File**: `configuration_baseline_service.py`

**Before**:
```python
def compareBaselines(self, baseline_id_1: str, baseline_id_2: str) -> BaselineDeltaReport:
    if baseline_id_1 not in self._baselines:
        raise ValueError(f"Baseline not found: {baseline_id_1}")
    if baseline_id_2 not in self._baselines:
        raise ValueError(f"Baseline not found: {baseline_id_2}")
    baseline_1 = self._baselines[baseline_id_1]
    baseline_2 = self._baselines[baseline_id_2]
```

**After**:
```python
async def compareBaselines(self, baseline_id_1: str, baseline_id_2: str) -> BaselineDeltaReport:
    baseline_1 = await self.getBaseline(baseline_id_1)
    if baseline_1 is None:
        raise ValueError(f"Baseline not found: {baseline_id_1}")
    baseline_2 = await self.getBaseline(baseline_id_2)
    if baseline_2 is None:
        raise ValueError(f"Baseline not found: {baseline_id_2}")
```

**Impact**: Same pattern as P2. Also applies to `freezeBaselineItems()` and `trackBaselineChanges()`.

### 5.4 Fix P4: Baseline Cache Invalidation

**File**: `configuration_baseline_service.py`

Add `invalidate_cache()` method:
```python
def invalidate_cache(self, baseline_id: str | None = None) -> None:
    if baseline_id is not None:
        self._baselines.pop(baseline_id, None)
    else:
        self._baselines.clear()
```

Call from controller after any baseline mutation (PATCH, delete).

### 5.5 Fix P5: Complete Cache Backfill

**File**: `configuration_manager_service.py`

The `_block_from_dict()` method must reconstruct `configuration_items` from DB data. This requires:

1. `repo.list_config_items_by_block(block_id)` — new repository method
2. `_block_from_dict()` calls this method to populate items
3. Items are also cached in a new `_config_items: dict[str, list]` indexed by block_id

**Note**: This is a lower priority fix. Current EV-3.7 verification shows that `configuration_items` is not used in any GET endpoint response (the hierarchy endpoint returns block summary, not item details). Defer to EV-4.1 if time-constrained.

---

## 6. Verification Criteria

| # | Test | Expected Result |
|---|------|-----------------|
| V1 | `GET /block-configurations/{id}` after service restart | Returns domain model format (same as create response) |
| V2 | `POST /config-conflicts/detect` after service restart | Returns conflict report (not ValueError) |
| V3 | `POST /baselines/compare` after service restart | Returns delta report (not ValueError) |
| V4 | `GET /block-configurations/{id}` — verify response format matches `to_dict()` | Field names and types consistent with POST response |
| V5 | Patch baseline, then GET baseline | Returns updated data (cache invalidated) |
| V6 | All GET endpoints return within 50ms on cache hit | Performance baseline established |

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `to_dict()` format differs from raw DB row | Medium | Low | Field mapping is 1:1 for simple types; JSONB columns already handled |
| `async` conversion breaks existing callers | Low | Medium | Only 2-3 internal callers, all in controller layer, already async |
| Cache backfill for items adds latency | Low | Low | Only on cache miss; subsequent reads are fast |
| Multi-worker cache drift | Low | Low | Single worker deployment; defer to EV-5 |

---

## 8. Out of Scope (Deferred to EV-5+)

- Redis or external cache layer
- Read Model / CQRS projections
- Event-driven cache synchronization across workers
- TimescaleDB materialized views for analytics reads
- Full-text search read path (pg_trgm / Elasticsearch)

---

## 9. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-22 | AeroForge-X Dev Team | Initial draft |
