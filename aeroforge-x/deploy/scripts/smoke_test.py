"""AeroForge-X V6.1 Smoke Test

Validates all infrastructure components and service health endpoints
after Docker Compose startup. Target: complete in <30 seconds.
REQ-VP-003~011
"""

import sys
import time
import urllib.request
import urllib.error


TIMEOUT_S = 5
SERVICE_TIMEOUT_S = 10

CHECKS = [
    {
        "name": "PostgreSQL",
        "type": "postgres",
        "host": "localhost",
        "port": 5432,
    },
    {
        "name": "TimescaleDB",
        "type": "postgres",
        "host": "localhost",
        "port": 5433,
    },
    {
        "name": "Neo4j HTTP",
        "type": "http",
        "url": "http://localhost:7474",
        "expected_status": 200,
    },
    {
        "name": "NATS",
        "type": "http",
        "url": "http://localhost:8222/healthz",
        "expected_status": 200,
    },
    {
        "name": "MinIO",
        "type": "http",
        "url": "http://localhost:9000/minio/health/live",
        "expected_status": 200,
    },
    {
        "name": "aircraft-core-service",
        "type": "http",
        "url": "http://localhost:8001/api/v6/aircraft-core/health",
        "expected_status": 200,
        "timeout": SERVICE_TIMEOUT_S,
    },
    {
        "name": "workflow-engine-service",
        "type": "http",
        "url": "http://localhost:8002/api/v6/workflow-engine/health",
        "expected_status": 200,
        "timeout": SERVICE_TIMEOUT_S,
    },
    {
        "name": "physics-twin-service",
        "type": "http",
        "url": "http://localhost:8003/api/v6/physics-twin/health",
        "expected_status": 200,
        "timeout": SERVICE_TIMEOUT_S,
    },
]


def check_http(name: str, url: str, expected_status: int, timeout: int) -> dict:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            if status == expected_status:
                return {"name": name, "status": "PASS", "detail": f"HTTP {status}"}
            return {"name": name, "status": "FAIL", "detail": f"Expected {expected_status}, got {status}"}
    except urllib.error.URLError as e:
        return {"name": name, "status": "FAIL", "detail": f"Connection error: {e.reason}"}
    except Exception as e:
        return {"name": name, "status": "FAIL", "detail": str(e)}


def check_postgres(name: str, host: str, port: int) -> dict:
    import socket
    try:
        sock = socket.create_connection((host, port), timeout=TIMEOUT_S)
        sock.close()
        return {"name": name, "status": "PASS", "detail": f"TCP {host}:{port} reachable"}
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return {"name": name, "status": "FAIL", "detail": f"TCP {host}:{port} unreachable: {e}"}


def main():
    start = time.time()
    results = []
    passed = 0
    failed = 0

    for check in CHECKS:
        if check["type"] == "http":
            timeout = check.get("timeout", TIMEOUT_S)
            result = check_http(check["name"], check["url"], check["expected_status"], timeout)
        elif check["type"] == "postgres":
            result = check_postgres(check["name"], check["host"], check["port"])
        else:
            result = {"name": check["name"], "status": "SKIP", "detail": "Unknown check type"}

        results.append(result)
        if result["status"] == "PASS":
            passed += 1
        elif result["status"] == "FAIL":
            failed += 1

    elapsed = time.time() - start

    print(f"\n{'='*60}")
    print(f"AeroForge-X V6.1 Smoke Test Results")
    print(f"{'='*60}")
    for r in results:
        icon = "OK" if r["status"] == "PASS" else "FAIL" if r["status"] == "FAIL" else "SKIP"
        print(f"  [{icon}] {r['name']}: {r['detail']}")
    print(f"{'='*60}")
    print(f"  Passed: {passed}  Failed: {failed}  Time: {elapsed:.1f}s")
    print(f"{'='*60}")

    if elapsed > 30:
        print("  WARNING: Smoke test exceeded 30 second target")

    if failed > 0:
        print("  RESULT: FAILED")
        sys.exit(1)
    else:
        print("  RESULT: ALL CHECKS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()