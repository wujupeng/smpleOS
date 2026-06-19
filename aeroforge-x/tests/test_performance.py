import pytest
import time
import statistics

from services.digital_twin_center.src.domain.services.twin_domain_service import TwinDomainService
from services.digital_twin_center.src.domain.services.design_twin_service import DesignTwinService
from services.digital_twin_center.src.domain.services.manufacturing_twin_service import ManufacturingTwinService
from services.digital_twin_center.src.domain.services.flight_twin_service import FlightTwinService
from services.digital_twin_center.src.domain.services.maintenance_twin_service import (
    MaintenanceTwinService, MaintenanceType, MaintenanceContent, MaintenanceResult,
)
from services.digital_twin_center.src.domain.services.twin_loop_service import TwinLoopService
from services.bom_center.src.domain.services.mbom_transform_domain_service import MBOMTransformDomainService
from services.bom_center.src.domain.services.sbom_gen_domain_service import SBOMGenerator
from services.bom_center.src.domain.services.bom_consistency_checker import BOMConsistencyChecker
from services.plm_center.src.domain.services.change_mgmt_domain_service import ChangeMgmtDomainService
from services.mes_center.src.domain.services.process_route_domain_service import ProcessRouteDomainService
from services.design_center.src.domain.entities.aircraft_spec import AircraftSpec
from services.design_center.src.domain.services.model_domain_service import ParametricModelGenerator
from services.bom_center.src.domain.services.ebom_engine import EBOMEngine
from services.cae_center.src.domain.services.cfd.cfd_domain_service import CFDDomainService
from services.cae_center.src.domain.services.fea.fea_domain_service import FEADomainService


PERFORMANCE_THRESHOLDS = {
    "twin_create": 0.05,
    "twin_sync": 0.05,
    "ebom_generate": 0.1,
    "mbom_transform": 0.1,
    "sbom_generate": 0.1,
    "consistency_check": 0.1,
    "ecr_submit": 0.05,
    "flight_telemetry_ingest": 0.1,
    "health_assessment": 0.1,
    "anomaly_detect": 0.05,
    "maintenance_plan_generate": 0.1,
    "process_route_generate": 0.2,
    "cfd_task_create": 0.05,
    "fea_task_create": 0.05,
}


def measure_time(func, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


class TestTwinPerformance:
    def test_twin_create_performance(self) -> None:
        service = TwinDomainService()
        times: list[float] = []

        for i in range(50):
            _, elapsed = measure_time(
                service.create_twin,
                f"PERF-SN-{i:04d}",
                "design",
                f"entity-{i}",
                "aircraft_design",
            )
            times.append(elapsed)

        avg = statistics.mean(times)
        p95 = sorted(times)[int(len(times) * 0.95)]
        assert avg < PERFORMANCE_THRESHOLDS["twin_create"], f"Twin create avg {avg:.4f}s exceeds threshold"
        assert p95 < PERFORMANCE_THRESHOLDS["twin_create"] * 2, f"Twin create p95 {p95:.4f}s exceeds 2x threshold"

    def test_twin_sync_performance(self) -> None:
        service = TwinDomainService()
        twin = service.create_twin("PERF-SYNC-001", "design", "e-1", "aircraft_design")
        times: list[float] = []

        for i in range(50):
            _, elapsed = measure_time(
                twin.sync,
                "parameter_update",
                {"param_v": i, "iteration": i},
            )
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["twin_sync"], f"Twin sync avg {avg:.4f}s exceeds threshold"

    def test_design_twin_sync_performance(self) -> None:
        service = TwinDomainService()
        design_service = DesignTwinService(service)
        times: list[float] = []

        for i in range(20):
            _, elapsed = measure_time(
                design_service.sync_with_design,
                f"PERF-DSN-{i:04d}",
                {"wing_span": 15.0 + i * 0.1, "fuselage_length": 20.0},
                "engineer",
                "perf_test",
            )
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["twin_sync"], f"Design twin sync avg {avg:.4f}s exceeds threshold"

    def test_flight_telemetry_ingest_performance(self) -> None:
        twin_service = TwinDomainService()
        flight_service = FlightTwinService(twin_service)
        times: list[float] = []

        for i in range(20):
            telemetry = [
                {"metric_name": f"sensor_{j}", "metric_value": float(j * i)}
                for j in range(10)
            ]
            _, elapsed = measure_time(
                flight_service.ingest_telemetry,
                f"PERF-FLT-{i:04d}",
                telemetry,
            )
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["flight_telemetry_ingest"], f"Telemetry ingest avg {avg:.4f}s exceeds threshold"

    def test_health_assessment_performance(self) -> None:
        twin_service = TwinDomainService()
        flight_service = FlightTwinService(twin_service)
        flight_service.ingest_telemetry("PERF-HEALTH-001", [
            {"metric_name": k, "metric_value": v}
            for k, v in {
                "wing_lift": 45000, "wing_bending_moment": 100000,
                "fuselage_pressure": 7.5, "tail_lateral_load": 25000,
                "engine_thrust": 22000, "landing_gear_load": 70000,
            }.items()
        ])
        times: list[float] = []

        for _ in range(50):
            _, elapsed = measure_time(
                flight_service.assess_structural_health,
                "PERF-HEALTH-001",
                flight_hours=5000.0,
            )
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["health_assessment"], f"Health assessment avg {avg:.4f}s exceeds threshold"

    def test_anomaly_detection_performance(self) -> None:
        twin_service = TwinDomainService()
        flight_service = FlightTwinService(twin_service)
        times: list[float] = []

        for i in range(50):
            sensor_data = {
                f"sensor_{j}": float(j * 100 + i) for j in range(20)
            }
            _, elapsed = measure_time(
                flight_service.detect_anomaly,
                f"PERF-ANOM-{i:04d}",
                sensor_data,
            )
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["anomaly_detect"], f"Anomaly detect avg {avg:.4f}s exceeds threshold"

    def test_maintenance_plan_generation_performance(self) -> None:
        twin_service = TwinDomainService()
        maintenance_service = MaintenanceTwinService(twin_service)

        for i in range(5):
            maintenance_service.record_maintenance(
                "PERF-MAINT-001",
                maintenance_type=MaintenanceType.PREVENTIVE,
                content=MaintenanceContent.INSPECTION,
                result=MaintenanceResult.COMPLETED,
                component_id=f"comp-{i}",
                flight_hours=float(i * 1000),
            )

        times: list[float] = []
        for _ in range(20):
            _, elapsed = measure_time(
                maintenance_service.generate_maintenance_plan,
                "PERF-MAINT-001",
                flight_hours=5000.0,
            )
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["maintenance_plan_generate"], f"Maintenance plan avg {avg:.4f}s exceeds threshold"


class TestBOMPerformance:
    def _create_ebom(self) -> "EBOM":
        spec = AircraftSpec(
            aircraft_type="fixed_wing",
            payload_kg=120,
            range_km=200,
            cruise_speed_kmh=120,
            takeoff_distance_m=80,
            power_type="electric",
            created_by="perf-test",
        )
        model_gen = ParametricModelGenerator()
        model = model_gen.generate({
            "aircraft_type": spec.aircraft_type,
            "payload_kg": spec.payload_kg,
            "range_km": spec.range_km,
            "cruise_speed_kmh": spec.cruise_speed_kmh,
            "template": {
                "default_params": {
                    "aspect_ratio": 8.0,
                    "wing_sweep_deg": 5.0,
                    "taper_ratio": 0.6,
                },
            },
        })
        ebom_engine = EBOMEngine()
        return ebom_engine.generate_from_model(spec_id=spec.id, model_data=model)

    def test_ebom_generation_performance(self) -> None:
        times: list[float] = []
        for _ in range(10):
            _, elapsed = measure_time(self._create_ebom)
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["ebom_generate"], f"eBOM generate avg {avg:.4f}s exceeds threshold"

    def test_mbom_transform_performance(self) -> None:
        ebom = self._create_ebom()
        ebom.publish()
        mbom_service = MBOMTransformDomainService()
        times: list[float] = []

        for _ in range(10):
            _, elapsed = measure_time(mbom_service.transform, ebom)
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["mbom_transform"], f"mBOM transform avg {avg:.4f}s exceeds threshold"

    def test_sbom_generation_performance(self) -> None:
        ebom = self._create_ebom()
        sbom_gen = SBOMGenerator()
        times: list[float] = []

        for _ in range(10):
            _, elapsed = measure_time(sbom_gen.generate, ebom)
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["sbom_generate"], f"sBOM generate avg {avg:.4f}s exceeds threshold"

    def test_consistency_check_performance(self) -> None:
        ebom = self._create_ebom()
        ebom.publish()
        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform(ebom)
        checker = BOMConsistencyChecker()
        times: list[float] = []

        for _ in range(20):
            _, elapsed = measure_time(checker.check_consistency, ebom, mbom)
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["consistency_check"], f"Consistency check avg {avg:.4f}s exceeds threshold"


class TestChangeManagementPerformance:
    def test_ecr_submission_performance(self) -> None:
        service = ChangeMgmtDomainService()
        times: list[float] = []

        for i in range(50):
            _, elapsed = measure_time(
                service.submit_ecr,
                f"变更请求-{i}",
                f"描述-{i}",
                f"submitter-{i}",
                "material",
                [f"part-{i}"],
            )
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["ecr_submit"], f"ECR submit avg {avg:.4f}s exceeds threshold"


class TestCAEPerformance:
    def test_cfd_task_create_performance(self) -> None:
        service = CFDDomainService()
        times: list[float] = []

        for i in range(20):
            _, elapsed = measure_time(
                service.create_cfd_task,
                f"AC-PERF-{i:04d}",
                "external_aerodynamics",
                f"mesh-{i}",
                {"mach": 0.3, "aoa": 2.0},
            )
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["cfd_task_create"], f"CFD task create avg {avg:.4f}s exceeds threshold"

    def test_fea_task_create_performance(self) -> None:
        service = FEADomainService()
        times: list[float] = []

        for i in range(20):
            _, elapsed = measure_time(
                service.create_fea_task,
                f"AC-PERF-{i:04d}",
                "static_strength",
                f"mesh-{i}",
                {"max_load": 50000},
            )
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["fea_task_create"], f"FEA task create avg {avg:.4f}s exceeds threshold"


class TestProcessRoutePerformance:
    def test_process_route_generation_performance(self) -> None:
        spec = AircraftSpec(
            aircraft_type="fixed_wing",
            payload_kg=120,
            range_km=200,
            cruise_speed_kmh=120,
            takeoff_distance_m=80,
            power_type="electric",
            created_by="perf-test",
        )
        model_gen = ParametricModelGenerator()
        model = model_gen.generate({
            "aircraft_type": spec.aircraft_type,
            "payload_kg": spec.payload_kg,
            "range_km": spec.range_km,
            "cruise_speed_kmh": spec.cruise_speed_kmh,
            "template": {
                "default_params": {
                    "aspect_ratio": 8.0,
                    "wing_sweep_deg": 5.0,
                    "taper_ratio": 0.6,
                },
            },
        })
        ebom_engine = EBOMEngine()
        ebom = ebom_engine.generate_from_model(spec_id=spec.id, model_data=model)
        ebom.publish()
        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform(ebom)
        route_service = ProcessRouteDomainService()
        times: list[float] = []

        for _ in range(10):
            _, elapsed = measure_time(route_service.generate_routes, mbom)
            times.append(elapsed)

        avg = statistics.mean(times)
        assert avg < PERFORMANCE_THRESHOLDS["process_route_generate"], f"Process route avg {avg:.4f}s exceeds threshold"