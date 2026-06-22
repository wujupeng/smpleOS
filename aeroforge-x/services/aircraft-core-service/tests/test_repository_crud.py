"""
AeroForge-X EV-3.4 Repository CRUD Verification Script

Tests the complete CRUD path: AsyncpgRepository -> PostgreSQL
Run inside aircraft-core-service container or with access to PostgreSQL.

Usage:
    python test_repository_crud.py [--dsn DSN]

Exit codes:
    0 = all tests passed
    1 = one or more tests failed
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

DSN = os.getenv("DATABASE_URL", os.getenv("POSTGRES_DSN", "postgresql://postgres:aeroforge@localhost:5432/aeroforge"))

results: list[dict] = []


def record(name: str, passed: bool, detail: str = ""):
    results.append({"name": name, "passed": passed, "detail": detail})
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


async def test_configuration_crud(pool):
    from src.infrastructure.repositories.configuration_repository import AsyncpgConfigurationRepository

    repo = AsyncpgConfigurationRepository(pool)
    block_id = f"test-block-{uuid.uuid4().hex[:8]}"
    sn_id = f"test-sn-{uuid.uuid4().hex[:8]}"
    baseline_id = f"test-bl-{uuid.uuid4().hex[:8]}"

    try:
        block = {
            "block_id": block_id,
            "aircraft_type": "A320neo",
            "block_name": "EV3-Test-Block",
            "design_config_id": "DC-001",
            "manufacturing_config_id": "MC-001",
            "operational_config_id": "OC-001",
            "locked": False,
        }
        await repo.save_block(block)
        record("save_block", True)

        fetched = await repo.get_block(block_id)
        record("get_block", fetched is not None and fetched["block_id"] == block_id,
               f"block_id={fetched['block_id']}" if fetched else "not found")

        blocks = await repo.list_blocks_by_aircraft_type("A320neo")
        record("list_blocks_by_aircraft_type", len(blocks) >= 1,
               f"count={len(blocks)}")

        updated = await repo.update_block(block_id, {"block_name": "EV3-Updated"})
        record("update_block", updated, f"updated={updated}")

        fetched2 = await repo.get_block(block_id)
        record("update_block_verify", fetched2 is not None and fetched2.get("block_name") == "EV3-Updated",
               f"block_name={fetched2.get('block_name')}" if fetched2 else "not found")

        sn = {
            "sn_id": sn_id,
            "tail_number": f"TST-{uuid.uuid4().hex[:4].upper()}",
            "block_id": block_id,
            "design_config_id": "DC-001",
            "manufacturing_config_id": "MC-001",
            "operational_config_id": "OC-001",
            "sn_modifications": [{"mod": "test"}],
            "service_bulletins": [],
            "repair_alterations": [],
        }
        await repo.save_sn(sn)
        record("save_sn", True)

        fetched_sn = await repo.get_sn(sn_id)
        record("get_sn", fetched_sn is not None and fetched_sn["sn_id"] == sn_id,
               f"sn_id={fetched_sn['sn_id']}" if fetched_sn else "not found")

        sns = await repo.list_sns_by_block(block_id)
        record("list_sns_by_block", len(sns) >= 1, f"count={len(sns)}")

        baseline = {
            "baseline_id": baseline_id,
            "baseline_type": "Design",
            "block_id": block_id,
            "configuration_snapshot": {"test": True},
            "frozen_items": ["item1"],
            "milestone": "PDR",
            "established_by": "ev3-tester",
            "locked": True,
        }
        await repo.save_baseline(baseline)
        record("save_baseline", True)

        fetched_bl = await repo.get_baseline(baseline_id)
        record("get_baseline", fetched_bl is not None and fetched_bl["baseline_id"] == baseline_id,
               f"baseline_id={fetched_bl['baseline_id']}" if fetched_bl else "not found")

        baselines = await repo.list_baselines_by_block(block_id)
        record("list_baselines_by_block", len(baselines) >= 1, f"count={len(baselines)}")

    except Exception as e:
        record("configuration_crud_exception", False, str(e))
    finally:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM configuration_baselines WHERE baseline_id LIKE 'test-bl-%'")
            await conn.execute("DELETE FROM serial_number_configurations WHERE sn_id LIKE 'test-sn-%'")
            await conn.execute("DELETE FROM block_configurations WHERE block_id LIKE 'test-block-%'")


async def test_supplier_crud(pool):
    from src.infrastructure.repositories.supplier_repository import AsyncpgSupplierRepository

    repo = AsyncpgSupplierRepository(pool)
    supplier_id = f"test-sup-{uuid.uuid4().hex[:8]}"

    try:
        supplier = {
            "supplier_id": supplier_id,
            "company_name": "EV3 Test Supplier",
            "certifications": ["AS9100D"],
            "capability_matrix": {"cnc": True},
            "quality_history": {"defect_rate": 0.01},
            "status": "Active",
        }
        await repo.save_supplier(supplier)
        record("save_supplier", True)

        fetched = await repo.get_supplier(supplier_id)
        record("get_supplier", fetched is not None and fetched["supplier_id"] == supplier_id,
               f"supplier_id={fetched['supplier_id']}" if fetched else "not found")

        suppliers = await repo.list_suppliers()
        record("list_suppliers", len(suppliers) >= 1, f"count={len(suppliers)}")

    except Exception as e:
        record("supplier_crud_exception", False, str(e))
    finally:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM supplier_profiles WHERE supplier_id LIKE 'test-sup-%'")


async def test_certification_crud(pool):
    from src.infrastructure.repositories.certification_repository import AsyncpgCertificationRepository

    repo = AsyncpgCertificationRepository(pool)
    reg_id = f"test-reg-{uuid.uuid4().hex[:8]}"

    try:
        regulation = {
            "regulation_id": reg_id,
            "regulation_type": "FAR",
            "title": "EV3 Test Regulation",
            "version": "1.0",
            "amendment_history": [{"v": "1.0"}],
        }
        await repo.save_regulation(regulation)
        record("save_regulation", True)

        fetched = await repo.get_regulation(reg_id)
        record("get_regulation", fetched is not None and fetched["regulation_id"] == reg_id,
               f"regulation_id={fetched['regulation_id']}" if fetched else "not found")

        regs = await repo.list_regulations()
        record("list_regulations", len(regs) >= 1, f"count={len(regs)}")

    except Exception as e:
        record("certification_crud_exception", False, str(e))
    finally:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM regulatory_libraries WHERE regulation_id LIKE 'test-reg-%'")


async def test_in_memory_fallback():
    from src.infrastructure.repositories.configuration_repository import ConfigurationRepository

    repo = ConfigurationRepository()
    block_id = "mem-test-001"

    block = {
        "block_id": block_id,
        "aircraft_type": "A350",
        "block_name": "Memory Test Block",
    }
    repo.save_block(block)
    fetched = repo.get_block(block_id)
    record("in_memory_save_get", fetched is not None and fetched["block_id"] == block_id,
           f"block_id={fetched['block_id']}" if fetched else "not found")


async def main():
    import asyncpg

    print("=" * 60)
    print("AeroForge-X EV-3.4 Repository CRUD Verification")
    print("=" * 60)
    print(f"DSN: {DSN}")
    print()

    print("--- In-Memory Fallback Tests ---")
    await test_in_memory_fallback()
    print()

    print("--- PostgreSQL CRUD Tests ---")
    try:
        pool = await asyncpg.create_pool(
            DSN,
            min_size=2,
            max_size=5,
            server_settings={"search_path": "aircraft_core,public"},
        )
    except Exception as e:
        record("pool_creation", False, str(e))
        print_summary()
        sys.exit(1)

    record("pool_creation", True, "connected")

    try:
        await test_configuration_crud(pool)
        print()
        await test_supplier_crud(pool)
        print()
        await test_certification_crud(pool)
    finally:
        await pool.close()

    print()
    print_summary()


def print_summary():
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    print("=" * 60)
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['name']}: {r['detail']}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())