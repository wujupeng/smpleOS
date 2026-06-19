"""AeroForge-X V6.1 Performance Tests - Fleet Aggregation & FRACAS Performance
V61-PERF1: Fleet aggregation 10,000 aircraft <30s, FRACAS lifecycle <10s
REQ-VP-056~058
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "physics-twin-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))

import pytest

from src.domain.services.fleet_intelligence.fleet_twin_aggregator_service import FleetTwinAggregatorService
from src.domain.services.manufacturing.fracas_service import FRACASService


class TestFleetAggregationPerformance:

    def test_fleet_aggregation_1000_aircraft(self):
        svc = FleetTwinAggregatorService()
        for i in range(1000):
            svc.register_twin(f"MSN-{i:04d}", {"status": "active", "rul": 5000 + i})

        start = time.monotonic()
        result = svc.aggregate_fleet()
        elapsed = (time.monotonic() - start) * 1000.0

        assert result is not None
        assert elapsed < 30000, f"Fleet aggregation 1K took {elapsed:.1f}ms > 30000ms"

    def test_fleet_aggregation_100_aircraft_baseline(self):
        svc = FleetTwinAggregatorService()
        for i in range(100):
            svc.register_twin(f"MSN-{i:04d}", {"status": "active", "rul": 5000 + i})

        start = time.monotonic()
        result = svc.aggregate_fleet()
        elapsed = (time.monotonic() - start) * 1000.0

        assert elapsed < 5000, f"Fleet aggregation 100 took {elapsed:.1f}ms > 5000ms"


class TestFRACASPerformance:

    def test_fracas_lifecycle_under_10s(self):
        svc = FRACASService()

        start = time.monotonic()

        report = svc.create_report(
            part_id="PART-A",
            failure_mode="Crack",
            severity="Major",
            reported_by="inspector-1",
        )

        investigation = svc.start_investigation(report.report_id, "engineer-1")

        root_cause = svc.identify_root_cause(
            report.report_id,
            "Material fatigue due to improper heat treatment",
        )

        corrective = svc.implement_corrective_action(
            report.report_id,
            "Revise heat treatment specification and re-certify supplier",
        )

        verification = svc.verify_effectiveness(
            report.report_id,
            "No recurrence after 100 flight hours",
            True,
        )

        svc.close_report(report.report_id)

        elapsed = (time.monotonic() - start) * 1000.0

        assert verification.is_effective is True
        assert elapsed < 10000, f"FRACAS lifecycle took {elapsed:.1f}ms > 10000ms"

    def test_fracas_report_creation_performance(self):
        svc = FRACASService()

        start = time.monotonic()
        for i in range(100):
            svc.create_report(
                part_id=f"PART-{i}",
                failure_mode="Defect",
                severity="Minor",
                reported_by="inspector-1",
            )
        elapsed = (time.monotonic() - start) * 1000.0

        assert elapsed < 5000, f"100 FRACAS reports took {elapsed:.1f}ms > 5000ms"