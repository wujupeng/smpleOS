import asyncio
import time
import statistics

from services.design_center.src.domain.services.spec_domain_service import SpecDomainService
from services.design_center.src.domain.services.model_domain_service import ParametricModelGenerator
from services.design_center.src.domain.services.aircraft_type_config import AircraftTypeConfig
from services.design_center.src.domain.entities.aircraft_spec import AircraftSpec
from services.bom_center.src.domain.services.ebom_engine import EBOMEngine


async def benchmark_spec_creation(iterations: int = 50) -> dict:
    service = SpecDomainService()
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        spec = AircraftSpec(
            aircraft_type="fixed_wing", payload_kg=120, range_km=200,
            cruise_speed_kmh=120, takeoff_distance_m=80, power_type="electric", created_by="bench",
        )
        service.validate_parameters(spec.to_dict())
        service.generate_spec_document(spec)
        times.append(time.perf_counter() - start)
    return {
        "operation": "spec_creation",
        "iterations": iterations,
        "mean_ms": round(statistics.mean(times) * 1000, 2),
        "p95_ms": round(sorted(times)[int(len(times) * 0.95)] * 1000, 2),
        "max_ms": round(max(times) * 1000, 2),
    }


async def benchmark_model_generation(iterations: int = 10) -> dict:
    gen = ParametricModelGenerator()
    type_config = AircraftTypeConfig()
    template = type_config.get_template("fixed_wing")
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        gen.generate({
            "aircraft_type": "fixed_wing", "payload_kg": 120, "range_km": 200,
            "cruise_speed_kmh": 120, "template": template,
        })
        times.append(time.perf_counter() - start)
    return {
        "operation": "model_generation",
        "iterations": iterations,
        "mean_ms": round(statistics.mean(times) * 1000, 2),
        "p95_ms": round(sorted(times)[int(len(times) * 0.95)] * 1000, 2),
        "max_ms": round(max(times) * 1000, 2),
        "target_ms": 30000,
        "pass": max(times) * 1000 < 30000,
    }


async def benchmark_ebom_generation(iterations: int = 10) -> dict:
    gen = EBOMEngine()
    model_gen = ParametricModelGenerator()
    type_config = AircraftTypeConfig()
    template = type_config.get_template("fixed_wing")
    model = model_gen.generate({
        "aircraft_type": "fixed_wing", "payload_kg": 120, "range_km": 200,
        "cruise_speed_kmh": 120, "template": template,
    })
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        ebom = gen.generate_from_model("spec-1", model)
        ebom.publish()
        times.append(time.perf_counter() - start)
    return {
        "operation": "ebom_generation",
        "iterations": iterations,
        "mean_ms": round(statistics.mean(times) * 1000, 2),
        "p95_ms": round(sorted(times)[int(len(times) * 0.95)] * 1000, 2),
        "max_ms": round(max(times) * 1000, 2),
    }


async def run_all_benchmarks() -> None:
    print("=" * 60)
    print("AeroForge-X Performance Benchmark")
    print("=" * 60)

    results = await asyncio.gather(
        benchmark_spec_creation(50),
        benchmark_model_generation(10),
        benchmark_ebom_generation(10),
    )

    for r in results:
        print(f"\n{r['operation']}:")
        for k, v in r.items():
            if k != "operation":
                print(f"  {k}: {v}")

    print("\n" + "=" * 60)
    model_result = results[1]
    if model_result.get("pass"):
        print("3D模型生成性能: PASS (30秒内)")
    else:
        print("3D模型生成性能: NEEDS OPTIMIZATION")


if __name__ == "__main__":
    asyncio.run(run_all_benchmarks())