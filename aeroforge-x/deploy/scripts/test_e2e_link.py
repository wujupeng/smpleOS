"""
AeroForge-X EV-3.5 End-to-End Link Verification Script

Validates the complete business chain:
  React Configuration Manager → FastAPI → ConfigurationManagerService → ConfigurationRepository → PostgreSQL

Prerequisites:
  - Docker Compose stack running (docker-compose -f deploy/docker-compose.v61.yml up -d)
  - curl available

Usage:
  python test_e2e_link.py [--api-host HOST] [--api-port PORT]
"""

import asyncio
import json
import sys
import os
import time
import urllib.request
import urllib.error

API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = os.getenv("API_PORT", "8001")
BASE_URL = f"http://{API_HOST}:{API_PORT}/api/v6/aircraft-core"

results: list[dict] = []


def record(name: str, passed: bool, detail: str = ""):
    results.append({"name": name, "passed": passed, "detail": detail})
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def api_call(method: str, path: str, body: dict = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body_text = e.read().decode()
            return e.code, json.loads(body_text)
        except Exception:
            return e.code, {"error": body_text}
    except Exception as e:
        return 0, {"error": str(e)}


def wait_for_service(max_retries: int = 30, interval: int = 3) -> bool:
    print("Waiting for aircraft-core-service...")
    for i in range(max_retries):
        try:
            url = f"http://{API_HOST}:{API_PORT}/health"
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status == 200:
                    print(f"  Service is healthy (attempt {i+1})")
                    return True
        except Exception:
            pass
        print(f"  Waiting... (attempt {i+1}/{max_retries})")
        time.sleep(interval)
    return False


def test_health():
    status, data = api_call("GET", "/../health")
    record("health_check", status == 200, f"status={status}")


def test_v6_health():
    status, data = api_call("GET", "/health")
    record("v6_health_check", status == 200, f"status={status}")


def test_create_block():
    body = {
        "aircraft_type": "A350-900",
        "block_name": "EV3-E2E-Test",
    }
    status, data = api_call("POST", "/block-configurations", body)
    record("create_block_config", status == 200, f"block_id={data.get('block_id', 'N/A')}")
    return data.get("block_id")


def test_get_hierarchy(aircraft_type: str):
    status, data = api_call("GET", f"/config-hierarchies/{aircraft_type}")
    record("get_config_hierarchy", status == 200,
           f"blocks={len(data.get('blocks', []))}" if status == 200 else f"status={status}")


def test_create_sn(block_id: str):
    import uuid
    tail = f"E2E-{uuid.uuid4().hex[:4].upper()}"
    body = {
        "block_id": block_id,
        "tail_number": tail,
    }
    status, data = api_call("POST", "/sn-configurations", body)
    record("create_sn_config", status == 200, f"sn_id={data.get('sn_id', 'N/A')}")
    return data.get("sn_id")


def test_verify_db_persistence():
    """Verify data persists by calling the API again (which reads from DB via repo)."""
    status, data = api_call("GET", "/config-hierarchies/A350-900")
    if status == 200:
        blocks = data.get("blocks", [])
        has_e2e_block = any(b.get("block_name") == "EV3-E2E-Test" for b in blocks)
        record("verify_db_persistence", has_e2e_block,
               f"found EV3-E2E-Test block in hierarchy" if has_e2e_block else "block not found in hierarchy")
    else:
        record("verify_db_persistence", False, f"status={status}")


def test_openapi_schema():
    try:
        url = f"http://{API_HOST}:{API_PORT}/openapi.json"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            paths = list(data.get("paths", {}).keys())
            v6_paths = [p for p in paths if "/api/v6/" in p]
            record("openapi_schema", len(v6_paths) > 0,
                   f"v6_endpoints={len(v6_paths)}")
    except Exception as e:
        record("openapi_schema", False, str(e))


def main():
    print("=" * 60)
    print("AeroForge-X EV-3.5 End-to-End Link Verification")
    print("=" * 60)
    print(f"API: {BASE_URL}")
    print()

    if not wait_for_service():
        print("ERROR: Service not available after max retries")
        sys.exit(1)

    print()
    print("--- Health Checks ---")
    test_health()
    test_v6_health()
    test_openapi_schema()

    print()
    print("--- Configuration CRUD (E2E) ---")
    block_id = test_create_block()
    if block_id:
        test_get_hierarchy("A350-900")
        test_create_sn(block_id)
    else:
        record("get_config_hierarchy", False, "skipped: block creation failed")
        record("create_sn_config", False, "skipped: block creation failed")

    print()
    print("--- DB Persistence Verification ---")
    test_verify_db_persistence()

    print()
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
    main()