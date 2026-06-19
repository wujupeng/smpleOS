from __future__ import annotations

import logging
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from ..entities.delivery_entities import (
    FlightCondition,
    FlightTestPlan,
    SafetyBoundary,
    TestDataRequirement,
    TestPoint,
    TestPointStatus,
    TestSubject,
    TestCategory,
)

logger = logging.getLogger(__name__)


class FlightTestPlanService:
    def __init__(self) -> None:
        self._plans: dict[str, FlightTestPlan] = {}
        self._certification_clauses: dict[str, list[str]] = {}
        self._init_certification_clauses()

    def _init_certification_clauses(self) -> None:
        self._certification_clauses["FAR-23"] = [
            "23.21", "23.23", "23.25", "23.141", "23.143", "23.145",
            "23.147", "23.149", "23.151", "23.153", "23.155", "23.157",
            "23.161", "23.173", "23.175", "23.177", "23.179", "23.181",
            "23.201", "23.203", "23.207", "23.211", "23.213", "23.221",
            "23.231", "23.233", "23.251", "23.253", "23.255", "23.301",
            "23.305", "23.307", "23.321", "23.337", "23.341", "23.349",
            "23.351", "23.361", "23.363", "23.367", "23.421", "23.441",
            "23.459", "23.471", "23.473", "23.475", "23.479", "23.481",
            "23.483", "23.485", "23.491", "23.493", "23.501", "23.507",
            "23.509", "23.521", "23.571", "23.573", "23.575", "23.601",
            "23.603", "23.609", "23.611", "23.613", "23.619", "23.623",
            "23.625", "23.627", "23.629", "23.651", "23.653", "23.655",
            "23.657", "23.659", "23.671", "23.672", "23.673", "23.674",
            "23.675", "23.677", "23.679", "23.681", "23.683", "23.685",
            "23.689", "23.691", "23.693", "23.695", "23.697", "23.701",
            "23.703", "23.705", "23.709", "23.711", "23.713", "23.715",
            "23.719", "23.721", "23.723", "23.725", "23.727", "23.729",
            "23.731", "23.733", "23.735", "23.771", "23.773", "23.775",
            "23.777", "23.779", "23.781", "23.783", "23.785", "23.787",
            "23.789", "23.791", "23.793", "23.795", "23.801", "23.803",
            "23.805", "23.807", "23.811", "23.831", "23.841", "23.851",
            "23.853", "23.855", "23.857", "23.859", "23.861", "23.863",
            "23.865", "23.867", "23.869", "23.871", "23.873", "23.901",
            "23.903", "23.905", "23.907", "23.909", "23.911", "23.913",
            "23.1141", "23.1143", "23.1145", "23.1147", "23.1149", "23.1151",
            "23.1153", "23.1155", "23.1157", "23.1159", "23.1161", "23.1163",
            "23.1165", "23.1167", "23.1169", "23.1171", "23.1173", "23.1175",
            "23.1301", "23.1303", "23.1305", "23.1307", "23.1309", "23.1311",
            "23.1313", "23.1315", "23.1317", "23.1319", "23.1321", "23.1323",
            "23.1325", "23.1327", "23.1329", "23.1331", "23.1333", "23.1335",
            "23.1337", "23.1351", "23.1353", "23.1357", "23.1359", "23.1361",
            "23.1363", "23.1365", "23.1367", "23.1369", "23.1371", "23.1381",
            "23.1383", "23.1385", "23.1387", "23.1389", "23.1391", "23.1393",
            "23.1395", "23.1397", "23.1399", "23.1401", "23.1403", "23.1405",
            "23.1407", "23.1409", "23.1411", "23.1413", "23.1415", "23.1419",
            "23.1421", "23.1423", "23.1431", "23.1435", "23.1439", "23.1441",
            "23.1443", "23.1445", "23.1447", "23.1449", "23.1451", "23.1453",
            "23.1455", "23.1457", "23.1459", "23.1461", "23.1501", "23.1505",
            "23.1509", "23.1511", "23.1513", "23.1515", "23.1517", "23.1519",
            "23.1521", "23.1523", "23.1525", "23.1527", "23.1529", "23.1531",
            "23.1533", "23.1535", "23.1541", "23.1543", "23.1545", "23.1547",
            "23.1549", "23.1551", "23.1553", "23.1555", "23.1557", "23.1559",
            "23.1561", "23.1563", "23.1565", "23.1581", "23.1583", "23.1585",
            "23.1587", "23.1589", "23.2001", "23.2005", "23.2007", "23.2009",
            "23.2011", "23.2013", "23.2015", "23.2017", "23.2019", "23.2021",
            "23.2023", "23.2025", "23.2027", "23.2029", "23.2031", "23.2033",
            "23.2035", "23.2037", "23.2039", "23.2041", "23.2043", "23.2045",
            "23.2047", "23.2049", "23.2051", "23.2053", "23.2055", "23.2057",
            "23.2059", "23.2061", "23.2063", "23.2065", "23.2067", "23.2069",
            "23.2071", "23.2073", "23.2075", "23.2077", "23.2079", "23.2081",
            "23.2083", "23.2085", "23.2087", "23.2089", "23.2091", "23.2093",
            "23.2095", "23.2097", "23.2099", "23.2101", "23.2103", "23.2105",
            "23.2107", "23.2109", "23.2111", "23.2113", "23.2115", "23.2117",
            "23.2119", "23.2121", "23.2123", "23.2125", "23.2127", "23.2129",
            "23.2131", "23.2133", "23.2135", "23.2137", "23.2139", "23.2141",
            "23.2143", "23.2145", "23.2147", "23.2149", "23.2151", "23.2153",
            "23.2155", "23.2157", "23.2159", "23.2161", "23.2163", "23.2165",
            "23.2167", "23.2169", "23.2171", "23.2173", "23.2175", "23.2177",
            "23.2179", "23.2181", "23.2183", "23.2185", "23.2187", "23.2189",
            "23.2191", "23.2193", "23.2195", "23.2197", "23.2199", "23.2201",
            "23.2203", "23.2205", "23.2207", "23.2209", "23.2211", "23.2213",
            "23.2215", "23.2217", "23.2219", "23.2221", "23.2223", "23.2225",
        ]
        self._certification_clauses["FAR-25"] = [
            "25.21", "25.23", "25.25", "25.27", "25.101", "25.103", "25.105",
            "25.107", "25.109", "25.111", "25.113", "25.115", "25.117", "25.119",
            "25.121", "25.123", "25.125", "25.141", "25.143", "25.145", "25.147",
            "25.149", "25.161", "25.173", "25.175", "25.177", "25.181", "25.201",
            "25.203", "25.207", "25.211", "25.213", "25.221", "25.231", "25.233",
            "25.235", "25.237", "25.239", "25.251", "25.253", "25.255", "25.271",
            "25.301", "25.303", "25.305", "25.307", "25.321", "25.331", "25.333",
            "25.337", "25.341", "25.343", "25.345", "25.349", "25.351", "25.361",
            "25.363", "25.365", "25.367", "25.371", "25.373", "25.391", "25.393",
            "25.395", "25.397", "25.399", "25.401", "25.403", "25.405", "25.407",
            "25.409", "25.411", "25.413", "25.415", "25.417", "25.427", "25.429",
            "25.431", "25.433", "25.435", "25.437", "25.439", "25.441", "25.443",
            "25.445", "25.447", "25.451", "25.453", "25.455", "25.457", "25.459",
            "25.471", "25.473", "25.475", "25.477", "25.479", "25.481", "25.483",
            "25.485", "25.487", "25.489", "25.491", "25.493", "25.495", "25.497",
            "25.499", "25.501", "25.503", "25.505", "25.507", "25.509", "25.511",
            "25.519", "25.521", "25.523", "25.525", "25.527", "25.529", "25.531",
            "25.533", "25.535", "25.537", "25.539", "25.541", "25.543", "25.545",
            "25.571", "25.573", "25.575", "25.581", "25.601", "25.603", "25.605",
            "25.607", "25.609", "25.611", "25.613", "25.615", "25.619", "25.621",
            "25.623", "25.625", "25.629", "25.631", "25.633", "25.635", "25.641",
            "25.643", "25.647", "25.649", "25.651", "25.653", "25.655", "25.657",
            "25.659", "25.661", "25.663", "25.665", "25.667", "25.669", "25.671",
            "25.673", "25.675", "25.677", "25.679", "25.681", "25.683", "25.685",
            "25.687", "25.689", "25.691", "25.693", "25.695", "25.697", "25.699",
            "25.701", "25.703", "25.705", "25.709", "25.711", "25.713", "25.715",
            "25.719", "25.721", "25.723", "25.725", "25.727", "25.729", "25.731",
            "25.733", "25.735", "25.737", "25.739", "25.741", "25.743", "25.745",
            "25.749", "25.751", "25.753", "25.755", "25.757", "25.759", "25.761",
            "25.763", "25.765", "25.767", "25.769", "25.771", "25.773", "25.775",
            "25.777", "25.779", "25.781", "25.783", "25.785", "25.787", "25.789",
            "25.791", "25.793", "25.795", "25.797", "25.799", "25.801", "25.803",
            "25.805", "25.807", "25.809", "25.811", "25.812", "25.813", "25.815",
            "25.816", "25.817", "25.819", "25.831", "25.832", "25.841", "25.843",
            "25.845", "25.849", "25.851", "25.853", "25.855", "25.856", "25.857",
            "25.859", "25.861", "25.863", "25.865", "25.867", "25.869", "25.871",
            "25.873", "25.875", "25.877", "25.879", "25.881", "25.883", "25.885",
            "25.887", "25.889", "25.891", "25.893", "25.895", "25.901", "25.903",
            "25.905", "25.907", "25.909", "25.911", "25.913", "25.915", "25.917",
            "25.919", "25.921", "25.923", "25.925", "25.927", "25.929", "25.931",
            "25.933", "25.934", "25.935", "25.937", "25.939", "25.941", "25.943",
            "25.945", "25.949", "25.951", "25.953", "25.955", "25.957", "25.959",
            "25.961", "25.963", "25.965", "25.967", "25.969", "25.971", "25.973",
            "25.975", "25.977", "25.979", "25.981", "25.983", "25.985", "25.987",
            "25.989", "25.991", "25.993", "25.995", "25.997", "25.999", "25.1001",
            "25.1301", "25.1305", "25.1307", "25.1309", "25.1310", "25.1315",
            "25.1316", "25.1317", "25.1318", "25.1319", "25.1321", "25.1322",
            "25.1323", "25.1325", "25.1326", "25.1327", "25.1329", "25.1331",
            "25.1333", "25.1335", "25.1337", "25.1341", "25.1343", "25.1345",
            "25.1347", "25.1349", "25.1351", "25.1353", "25.1355", "25.1357",
            "25.1359", "25.1361", "25.1362", "25.1363", "25.1365", "25.1367",
            "25.1369", "25.1371", "25.1381", "25.1383", "25.1385", "25.1387",
            "25.1389", "25.1391", "25.1393", "25.1395", "25.1397", "25.1399",
            "25.1401", "25.1403", "25.1405", "25.1407", "25.1409", "25.1411",
            "25.1413", "25.1415", "25.1419", "25.1421", "25.1423", "25.1431",
            "25.1435", "25.1438", "25.1439", "25.1441", "25.1443", "25.1445",
            "25.1447", "25.1449", "25.1451", "25.1453", "25.1455", "25.1457",
            "25.1459", "25.1461", "25.1501", "25.1503", "25.1505", "25.1509",
            "25.1511", "25.1513", "25.1515", "25.1516", "25.1517", "25.1521",
            "25.1523", "25.1525", "25.1527", "25.1529", "25.1531", "25.1533",
            "25.1535", "25.1541", "25.1543", "25.1545", "25.1547", "25.1549",
            "25.1551", "25.1553", "25.1555", "25.1557", "25.1559", "25.1561",
            "25.1563", "25.1565", "25.1567", "25.1569", "25.1571", "25.1581",
            "25.1583", "25.1585", "25.1587", "25.1589", "25.1701", "25.1703",
            "25.1705", "25.1707", "25.1709", "25.1711", "25.1713", "25.1715",
            "25.1717", "25.1719", "25.1721", "25.1723", "25.1725", "25.1727",
            "25.1729", "25.1731", "25.1733", "25.1735", "25.1737", "25.1739",
        ]
        self._certification_clauses["CCAR-23"] = [
            "23.21", "23.23", "23.25", "23.141", "23.143", "23.145",
            "23.147", "23.149", "23.201", "23.203", "23.207", "23.221",
            "23.301", "23.305", "23.307", "23.321", "23.337", "23.341",
            "23.571", "23.601", "23.603", "23.609", "23.613",
            "23.771", "23.1309", "23.1529",
        ]
        self._certification_clauses["CCAR-25"] = [
            "25.21", "25.23", "25.25", "25.101", "25.107", "25.111",
            "25.119", "25.121", "25.141", "25.143", "25.147", "25.149",
            "25.161", "25.173", "25.175", "25.201", "25.207", "25.221",
            "25.251", "25.255", "25.301", "25.305", "25.307", "25.321",
            "25.337", "25.341", "25.345", "25.349", "25.351",
            "25.471", "25.473", "25.479", "25.481", "25.483",
            "25.571", "25.601", "25.603", "25.609", "25.613",
            "25.629", "25.721", "25.771", "25.783", "25.807",
            "25.831", "25.841", "25.853", "25.901",
            "25.1309", "25.1321", "25.1351", "25.1353",
            "25.1439", "25.1529", "25.1541", "25.1581",
        ]

    def generate_flight_test_plan(
        self,
        tenant_id: str,
        project_id: str,
        aircraft_model: str,
        certification_standard: str,
        design_parameters: dict[str, Any] | None = None,
    ) -> FlightTestPlan:
        plan = FlightTestPlan(
            tenant_id=tenant_id,
            project_id=project_id,
            aircraft_model=aircraft_model,
            certification_standard=certification_standard,
        )

        self._generate_performance_subjects(plan, design_parameters or {})
        self._generate_stability_subjects(plan, design_parameters or {})
        self._generate_controllability_subjects(plan, design_parameters or {})
        self._generate_structural_subjects(plan, design_parameters or {})
        self._generate_systems_subjects(plan, design_parameters or {})

        required_clauses = self._certification_clauses.get(certification_standard, [])
        plan.calculate_coverage(required_clauses)

        plan.add_domain_event(DomainEvent(
            event_type="flight_test_plan.generated",
            aggregate_id=plan.id,
            payload={
                "tenant_id": tenant_id,
                "project_id": project_id,
                "aircraft_model": aircraft_model,
                "total_subjects": len(plan.subjects),
                "total_flights": plan.total_flights,
                "coverage": plan.coverage_percentage,
            },
        ))

        self._plans[plan.id] = plan
        logger.info(
            "Flight test plan generated: project=%s model=%s subjects=%d flights=%d coverage=%.1f%%",
            project_id, aircraft_model, len(plan.subjects), plan.total_flights, plan.coverage_percentage,
        )
        return plan

    def get_plan(self, plan_id: str) -> FlightTestPlan | None:
        return self._plans.get(plan_id)

    def map_certification_requirements(self, certification_standard: str) -> dict[str, Any]:
        clauses = self._certification_clauses.get(certification_standard, [])
        mapped: dict[str, list[str]] = {
            TestCategory.PERFORMANCE.value: [],
            TestCategory.STABILITY.value: [],
            TestCategory.CONTROLLABILITY.value: [],
            TestCategory.STRUCTURAL.value: [],
            TestCategory.SYSTEMS.value: [],
        }

        for clause in clauses:
            if any(k in clause for k in ["101", "103", "105", "107", "109", "111", "113", "115", "117", "119", "121", "123", "125"]):
                mapped[TestCategory.PERFORMANCE.value].append(clause)
            elif any(k in clause for k in ["141", "143", "145", "147", "149", "161", "173", "175", "177", "181"]):
                mapped[TestCategory.CONTROLLABILITY.value].append(clause)
            elif any(k in clause for k in ["201", "203", "207", "211", "213", "221", "231", "233", "251", "253", "255"]):
                mapped[TestCategory.STABILITY.value].append(clause)
            elif any(k in clause for k in ["301", "305", "307", "321", "331", "333", "337", "341", "343", "345", "349", "351", "471", "473", "479", "481", "483", "491", "493", "571", "573", "575", "601", "603", "609", "613", "619", "621", "623", "625", "627", "629"]):
                mapped[TestCategory.STRUCTURAL.value].append(clause)
            elif any(k in clause for k in ["1301", "1303", "1305", "1307", "1309", "1311", "1321", "1323", "1325", "1327", "1329", "1331", "1333", "1335", "1337", "1351", "1353", "1357", "1359", "1361", "1363", "1365", "1367", "1369", "1371", "1381", "1383", "1385", "1387", "1389", "1391", "1393", "1395", "1397", "1399", "1401", "1403", "1405", "1407", "1409", "1411", "1413", "1415"]):
                mapped[TestCategory.SYSTEMS.value].append(clause)

        total_mapped = sum(len(v) for v in mapped.values())
        unmapped = [c for c in clauses if not any(c in v for v in mapped.values())]

        return {
            "standard": certification_standard,
            "total_clauses": len(clauses),
            "mapped_clauses": total_mapped,
            "unmapped_clauses": unmapped,
            "mapping": mapped,
        }

    def validate_coverage(self, plan_id: str) -> dict[str, Any]:
        plan = self._plans.get(plan_id)
        if plan is None:
            return {"error": "Plan not found"}

        required_clauses = self._certification_clauses.get(plan.certification_standard, [])
        return plan.calculate_coverage(required_clauses)

    def optimize_test_sequence(self, plan_id: str) -> dict[str, Any]:
        plan = self._plans.get(plan_id)
        if plan is None:
            return {"error": "Plan not found"}

        sorted_subjects = sorted(plan.subjects, key=lambda s: s.priority)

        dependency_graph: dict[str, list[str]] = {}
        for subject in sorted_subjects:
            dependency_graph[subject.subject_id] = subject.dependencies

        ordered: list[str] = []
        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(sid: str) -> None:
            if sid in visited:
                return
            if sid in visiting:
                return
            visiting.add(sid)
            for dep in dependency_graph.get(sid, []):
                visit(dep)
            visiting.discard(sid)
            visited.add(sid)
            ordered.append(sid)

        for subject in sorted_subjects:
            visit(subject.subject_id)

        subject_map = {s.subject_id: s for s in plan.subjects}
        optimized_sequence = []
        flight_num = 1
        current_flight_points: list[dict] = []
        current_duration = 0.0

        for sid in ordered:
            subject = subject_map.get(sid)
            if not subject:
                continue
            for point in subject.test_points:
                if current_duration + point.estimated_duration_minutes > 180:
                    if current_flight_points:
                        optimized_sequence.append({
                            "flight_number": flight_num,
                            "test_points": current_flight_points,
                            "estimated_duration_minutes": current_duration,
                        })
                        flight_num += 1
                        current_flight_points = []
                        current_duration = 0.0
                current_flight_points.append({
                    "subject_id": sid,
                    "point_id": point.point_id,
                    "name": point.name,
                    "flight_condition": point.flight_condition.value,
                })
                current_duration += point.estimated_duration_minutes

        if current_flight_points:
            optimized_sequence.append({
                "flight_number": flight_num,
                "test_points": current_flight_points,
                "estimated_duration_minutes": round(current_duration, 1),
            })

        return {
            "plan_id": plan_id,
            "total_flights": len(optimized_sequence),
            "sequence": optimized_sequence,
            "total_flight_hours": round(sum(f["estimated_duration_minutes"] for f in optimized_sequence) / 60, 1),
        }

    def _generate_performance_subjects(self, plan: FlightTestPlan, params: dict[str, Any]) -> None:
        subject = TestSubject(
            subject_id="PERF-001",
            category=TestCategory.PERFORMANCE,
            objective="Verify aircraft performance meets certification requirements",
            method="Steady-state and accelerated flight tests",
            certification_clauses=["23.101", "23.103", "23.105", "23.107", "23.109", "23.111", "23.113", "23.115", "23.117", "23.119", "23.121", "23.123", "23.125",
                                   "25.101", "25.103", "25.105", "25.107", "25.109", "25.111", "25.113", "25.115", "25.117", "25.119", "25.121", "25.123", "25.125"],
            priority=1,
        )

        subject.test_points = [
            TestPoint("PERF-001-01", "Takeoff distance", FlightCondition.TAKEOFF, altitude_ft=0, speed_ktas=params.get("v2_ktas", 80), estimated_duration_minutes=20,
                      data_requirements=[TestDataRequirement("distance", "m", 10), TestDataRequirement("airspeed", "ktas", 20)],
                      safety_boundaries=[SafetyBoundary("airspeed", max_value=params.get("v2_ktas", 80) * 1.3, unit="ktas")],
                      certification_clause="23.107"),
            TestPoint("PERF-001-02", "Climb rate", FlightCondition.CLIMB, altitude_ft=5000, speed_ktas=params.get("vy_ktas", 75), estimated_duration_minutes=30,
                      data_requirements=[TestDataRequirement("climb_rate", "fpm", 10), TestDataRequirement("engine_torque", "ft-lb", 50)],
                      safety_boundaries=[SafetyBoundary("climb_rate", min_value=300, unit="fpm")],
                      certification_clause="23.111"),
            TestPoint("PERF-001-03", "Cruise speed", FlightCondition.CRUISE, altitude_ft=10000, speed_ktas=params.get("cruise_speed_ktas", 150), estimated_duration_minutes=25,
                      data_requirements=[TestDataRequirement("airspeed", "ktas", 20), TestDataRequirement("fuel_flow", "kg/h", 5)],
                      certification_clause="23.119"),
            TestPoint("PERF-001-04", "Landing distance", FlightCondition.LANDING, altitude_ft=0, speed_ktas=params.get("vref_ktas", 70), estimated_duration_minutes=20,
                      data_requirements=[TestDataRequirement("distance", "m", 10), TestDataRequirement("approach_speed", "ktas", 20)],
                      safety_boundaries=[SafetyBoundary("approach_speed", max_value=params.get("vref_ktas", 70) * 1.3, unit="ktas")],
                      certification_clause="23.125"),
        ]
        plan.add_subject(subject)

    def _generate_stability_subjects(self, plan: FlightTestPlan, params: dict[str, Any]) -> None:
        subject = TestSubject(
            subject_id="STAB-001",
            category=TestCategory.STABILITY,
            objective="Verify static and dynamic stability characteristics",
            method="Trim shots, pulse inputs, and doublet inputs",
            certification_clauses=["23.173", "23.175", "23.177", "23.179", "23.181", "23.201", "23.203", "23.207", "23.221",
                                   "25.173", "25.175", "25.177", "25.181", "25.201", "25.203", "25.207", "25.221", "25.233", "25.251", "25.253", "25.255"],
            priority=2,
            dependencies=["PERF-001"],
        )
        subject.test_points = [
            TestPoint("STAB-001-01", "Longitudinal static stability", FlightCondition.CRUISE, altitude_ft=10000, speed_ktas=params.get("cruise_speed_ktas", 150), estimated_duration_minutes=45,
                      data_requirements=[TestDataRequirement("stick_force", "lbf", 50), TestDataRequirement("pitch_rate", "deg/s", 100)],
                      certification_clause="23.173"),
            TestPoint("STAB-001-02", "Lateral-directional stability", FlightCondition.CRUISE, altitude_ft=10000, speed_ktas=params.get("cruise_speed_ktas", 150), estimated_duration_minutes=40,
                      data_requirements=[TestDataRequirement("roll_rate", "deg/s", 100), TestDataRequirement("yaw_rate", "deg/s", 100)],
                      certification_clause="23.177"),
            TestPoint("STAB-001-03", "Stall characteristics", FlightCondition.LOW_SPEED, altitude_ft=5000, speed_ktas=params.get("vs_ktas", 55), estimated_duration_minutes=35,
                      data_requirements=[TestDataRequirement("aoa", "deg", 100), TestDataRequirement("stick_force", "lbf", 50)],
                      safety_boundaries=[SafetyBoundary("altitude", min_value=3000, unit="ft")],
                      certification_clause="23.201"),
        ]
        plan.add_subject(subject)

    def _generate_controllability_subjects(self, plan: FlightTestPlan, params: dict[str, Any]) -> None:
        subject = TestSubject(
            subject_id="CTRL-001",
            category=TestCategory.CONTROLLABILITY,
            objective="Verify aircraft controllability and maneuverability",
            method="Control displacement and force measurements",
            certification_clauses=["23.141", "23.143", "23.145", "23.147", "23.149", "23.151", "23.153", "23.155", "23.157", "23.161",
                                   "25.141", "25.143", "25.145", "25.147", "25.149", "25.161"],
            priority=2,
            dependencies=["PERF-001"],
        )
        subject.test_points = [
            TestPoint("CTRL-001-01", "Controllability during takeoff", FlightCondition.TAKEOFF, altitude_ft=0, speed_ktas=params.get("v2_ktas", 80), estimated_duration_minutes=25,
                      certification_clause="23.143"),
            TestPoint("CTRL-001-02", "Controllability during landing", FlightCondition.LANDING, altitude_ft=0, speed_ktas=params.get("vref_ktas", 70), estimated_duration_minutes=25,
                      certification_clause="23.143"),
            TestPoint("CTRL-001-03", "VMC demonstration", FlightCondition.CLIMB, altitude_ft=5000, speed_ktas=params.get("vmc_ktas", 65), estimated_duration_minutes=30,
                      safety_boundaries=[SafetyBoundary("airspeed", min_value=params.get("vs_ktas", 55), unit="ktas")],
                      certification_clause="23.149"),
        ]
        plan.add_subject(subject)

    def _generate_structural_subjects(self, plan: FlightTestPlan, params: dict[str, Any]) -> None:
        subject = TestSubject(
            subject_id="STRU-001",
            category=TestCategory.STRUCTURAL,
            objective="Verify structural integrity under flight loads",
            method="Strain gauge measurements during maneuvering flight",
            certification_clauses=["23.301", "23.305", "23.307", "23.321", "23.337", "23.341", "23.345", "23.349", "23.351", "23.471", "23.473", "23.479", "23.481", "23.571",
                                   "25.301", "25.305", "25.307", "25.321", "25.337", "25.341", "25.345", "25.349", "25.351", "25.471", "25.473", "25.479", "25.481", "25.571"],
            priority=3,
            dependencies=["STAB-001", "CTRL-001"],
        )
        subject.test_points = [
            TestPoint("STRU-001-01", "Maneuvering load factors", FlightCondition.HIGH_SPEED, altitude_ft=10000, speed_ktas=params.get("vd_ktas", 200), estimated_duration_minutes=40,
                      data_requirements=[TestDataRequirement("load_factor", "g", 100), TestDataRequirement("strain_wing_root", "microstrain", 500)],
                      safety_boundaries=[SafetyBoundary("load_factor", max_value=params.get("limit_load_factor", 3.8), unit="g")],
                      certification_clause="23.337"),
            TestPoint("STRU-001-02", "Gust response", FlightCondition.CRUISE, altitude_ft=10000, speed_ktas=params.get("vc_ktas", 150), estimated_duration_minutes=35,
                      data_requirements=[TestDataRequirement("load_factor", "g", 100), TestDataRequirement("acceleration_z", "g", 200)],
                      certification_clause="23.341"),
        ]
        plan.add_subject(subject)

    def _generate_systems_subjects(self, plan: FlightTestPlan, params: dict[str, Any]) -> None:
        subject = TestSubject(
            subject_id="SYST-001",
            category=TestCategory.SYSTEMS,
            objective="Verify aircraft systems operation and reliability",
            method="Systems functional tests in flight",
            certification_clauses=["23.1301", "23.1309", "23.1321", "23.1323", "23.1325", "23.1327", "23.1331", "23.1335", "23.1337", "23.1351", "23.1353", "23.1357", "23.1361", "23.1363", "23.1365", "23.1381", "23.1383", "23.1385", "23.1387", "23.1389", "23.1391", "23.1393", "23.1395", "23.1397", "23.1399", "23.1401", "23.1403", "23.1405", "23.1407", "23.1409", "23.1411", "23.1413", "23.1415", "23.1529",
                                   "25.1301", "25.1309", "25.1321", "25.1323", "25.1325", "25.1327", "25.1329", "25.1331", "25.1333", "25.1335", "25.1337", "25.1351", "25.1353", "25.1357", "25.1359", "25.1361", "25.1363", "25.1365", "25.1367", "25.1369", "25.1371", "25.1381", "25.1383", "25.1385", "25.1387", "25.1389", "25.1391", "25.1393", "25.1395", "25.1397", "25.1399", "25.1401", "25.1403", "25.1405", "25.1407", "25.1409", "25.1411", "25.1413", "25.1415", "25.1431", "25.1435", "25.1438", "25.1439", "25.1441", "25.1443", "25.1445", "25.1447", "25.1449", "25.1451", "25.1453", "25.1455", "25.1457", "25.1459", "25.1461", "25.1529"],
            priority=4,
            dependencies=["STRU-001"],
        )
        subject.test_points = [
            TestPoint("SYST-001-01", "Flight instruments check", FlightCondition.CRUISE, altitude_ft=10000, speed_ktas=params.get("cruise_speed_ktas", 150), estimated_duration_minutes=30,
                      data_requirements=[TestDataRequirement("airspeed_indicated", "ktas", 10), TestDataRequirement("altitude_indicated", "ft", 5)],
                      certification_clause="23.1301"),
            TestPoint("SYST-001-02", "Electrical system load test", FlightCondition.CRUISE, altitude_ft=10000, speed_ktas=params.get("cruise_speed_ktas", 150), estimated_duration_minutes=40,
                      data_requirements=[TestDataRequirement("bus_voltage", "V", 10), TestDataRequirement("bus_current", "A", 10)],
                      certification_clause="23.1351"),
            TestPoint("SYST-001-03", "Emergency systems verification", FlightCondition.CRUISE, altitude_ft=10000, speed_ktas=params.get("cruise_speed_ktas", 150), estimated_duration_minutes=35,
                      certification_clause="23.1309"),
        ]
        plan.add_subject(subject)