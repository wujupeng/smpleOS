"""AeroForge-X Supplier Repository

Persistence layer for SupplierRegistryService, MaterialLotTrackerService, NDTIntegrationService.
Target tables: supplier_profiles, supplier_quality_ratings, material_lots, ndt_records,
              supplier_quality_issues, corrective_action_requests
"""

from __future__ import annotations

from typing import Any, Optional

from src.infrastructure.repositories.base_repository import (
    AsyncpgRepository,
    InMemoryRepository,
)


class SupplierRepository(InMemoryRepository):

    def save_supplier(self, supplier: dict) -> None:
        self._put("supplier_profiles", supplier["supplier_id"], supplier)

    def get_supplier(self, supplier_id: str) -> Optional[dict]:
        return self._get("supplier_profiles", supplier_id)

    def list_suppliers(self, **filters) -> list[dict]:
        return self._list("supplier_profiles", **filters)

    def save_rating(self, rating: dict) -> None:
        self._put("supplier_quality_ratings", rating["rating_id"], rating)

    def get_rating_by_supplier(self, supplier_id: str) -> Optional[dict]:
        ratings = self._list("supplier_quality_ratings", supplier_id=supplier_id)
        return ratings[-1] if ratings else None

    def save_lot(self, lot: dict) -> None:
        self._put("material_lots", lot["lot_id"], lot)

    def get_lot(self, lot_id: str) -> Optional[dict]:
        return self._get("material_lots", lot_id)

    def list_lots_by_supplier(self, supplier_id: str) -> list[dict]:
        return self._list("material_lots", supplier_id=supplier_id)

    def save_ndt_record(self, record: dict) -> None:
        self._put("ndt_records", record["ndt_id"], record)

    def get_ndt_record(self, ndt_id: str) -> Optional[dict]:
        return self._get("ndt_records", ndt_id)

    def list_ndt_by_part(self, part_id: str) -> list[dict]:
        return self._list("ndt_records", part_id=part_id)

    def save_quality_issue(self, issue: dict) -> None:
        self._put("supplier_quality_issues", issue["issue_id"], issue)

    def get_quality_issue(self, issue_id: str) -> Optional[dict]:
        return self._get("supplier_quality_issues", issue_id)

    def save_car(self, car: dict) -> None:
        self._put("corrective_action_requests", car["car_id"], car)

    def get_car(self, car_id: str) -> Optional[dict]:
        return self._get("corrective_action_requests", car_id)

    def list_cars_by_supplier(self, supplier_id: str) -> list[dict]:
        return self._list("corrective_action_requests", supplier_id=supplier_id)


class AsyncpgSupplierRepository(AsyncpgRepository):

    async def save_supplier(self, supplier: dict) -> None:
        await self._execute(
            """
            INSERT INTO supplier_profiles
                (supplier_id, company_name, certifications, capability_matrix,
                 quality_history, status)
            VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6)
            ON CONFLICT (supplier_id) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                certifications = EXCLUDED.certifications,
                capability_matrix = EXCLUDED.capability_matrix,
                quality_history = EXCLUDED.quality_history,
                status = EXCLUDED.status
            """,
            supplier["supplier_id"],
            supplier["company_name"],
            supplier.get("certifications", []),
            self._json_dumps(supplier.get("capability_matrix", {})),
            self._json_dumps(supplier.get("quality_history", {})),
            supplier.get("status", "Pending"),
        )

    async def get_supplier(self, supplier_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM supplier_profiles WHERE supplier_id = $1", supplier_id
        )
        if row is None:
            return None
        result = dict(row)
        result["capability_matrix"] = self._json_loads(
            result.get("capability_matrix", "{}")
        )
        result["quality_history"] = self._json_loads(
            result.get("quality_history", "{}")
        )
        return result

    async def list_suppliers(self, **filters) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM supplier_profiles ORDER BY registered_at DESC"
        )
        results = []
        for r in rows:
            d = dict(r)
            d["capability_matrix"] = self._json_loads(d.get("capability_matrix", "{}"))
            d["quality_history"] = self._json_loads(d.get("quality_history", "{}"))
            results.append(d)
        if filters:
            results = [r for r in results if all(r.get(k) == v for k, v in filters.items())]
        return results

    async def save_rating(self, rating: dict) -> None:
        await self._execute(
            """
            INSERT INTO supplier_quality_ratings
                (rating_id, supplier_id, on_time_delivery_rate, first_pass_yield,
                 defect_rate, car_responsiveness, audit_findings_score,
                 overall_rating, is_below_threshold)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            rating["rating_id"],
            rating["supplier_id"],
            rating.get("on_time_delivery_rate", 0.0),
            rating.get("first_pass_yield", 0.0),
            rating.get("defect_rate", 0.0),
            rating.get("car_responsiveness", 0.0),
            rating.get("audit_findings_score", 0.0),
            rating.get("overall_rating", 0.0),
            rating.get("is_below_threshold", False),
        )

    async def get_rating_by_supplier(self, supplier_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM supplier_quality_ratings WHERE supplier_id = $1 ORDER BY rated_at DESC LIMIT 1",
            supplier_id,
        )
        return dict(row) if row else None

    async def save_lot(self, lot: dict) -> None:
        await self._execute(
            """
            INSERT INTO material_lots
                (lot_id, supplier_id, material_specification, heat_number,
                 certificate_of_conformance, test_results, status)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
            ON CONFLICT (lot_id) DO UPDATE SET
                material_specification = EXCLUDED.material_specification,
                test_results = EXCLUDED.test_results,
                status = EXCLUDED.status
            """,
            lot["lot_id"],
            lot["supplier_id"],
            lot["material_specification"],
            lot["heat_number"],
            lot.get("certificate_of_conformance"),
            self._json_dumps(lot.get("test_results", {})),
            lot.get("status", "Received"),
        )

    async def get_lot(self, lot_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM material_lots WHERE lot_id = $1", lot_id
        )
        if row is None:
            return None
        result = dict(row)
        result["test_results"] = self._json_loads(result.get("test_results", "{}"))
        return result

    async def list_lots_by_supplier(self, supplier_id: str) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM material_lots WHERE supplier_id = $1 ORDER BY received_at DESC",
            supplier_id,
        )
        return [dict(r) for r in rows]

    async def save_ndt_record(self, record: dict) -> None:
        await self._execute(
            """
            INSERT INTO ndt_records
                (ndt_id, part_id, inspection_method, equipment_calibration_data,
                 inspection_procedure_ref, inspector_certification,
                 acceptance_criteria, result, linked_lot_id, linked_operation_id)
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10)
            """,
            record["ndt_id"],
            record["part_id"],
            record["inspection_method"],
            self._json_dumps(record.get("equipment_calibration_data", {})),
            record.get("inspection_procedure_ref"),
            record.get("inspector_certification"),
            record.get("acceptance_criteria"),
            record["result"],
            record.get("linked_lot_id"),
            record.get("linked_operation_id"),
        )

    async def get_ndt_record(self, ndt_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM ndt_records WHERE ndt_id = $1", ndt_id
        )
        if row is None:
            return None
        result = dict(row)
        result["equipment_calibration_data"] = self._json_loads(
            result.get("equipment_calibration_data", "{}")
        )
        return result

    async def list_ndt_by_part(self, part_id: str) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM ndt_records WHERE part_id = $1 ORDER BY inspected_at DESC",
            part_id,
        )
        return [dict(r) for r in rows]

    async def save_quality_issue(self, issue: dict) -> None:
        await self._execute(
            """
            INSERT INTO supplier_quality_issues
                (issue_id, supplier_id, issue_type, description, severity,
                 correlated_lots, correlated_ndt_records, affected_aircraft,
                 car_id, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (issue_id) DO UPDATE SET
                status = EXCLUDED.status,
                car_id = EXCLUDED.car_id
            """,
            issue["issue_id"],
            issue["supplier_id"],
            issue["issue_type"],
            issue["description"],
            issue["severity"],
            issue.get("correlated_lots", []),
            issue.get("correlated_ndt_records", []),
            issue.get("affected_aircraft", []),
            issue.get("car_id"),
            issue.get("status", "Reported"),
        )

    async def get_quality_issue(self, issue_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM supplier_quality_issues WHERE issue_id = $1", issue_id
        )
        return dict(row) if row else None

    async def save_car(self, car: dict) -> None:
        await self._execute(
            """
            INSERT INTO corrective_action_requests
                (car_id, issue_id, supplier_id, root_cause, corrective_action,
                 due_date, response_date, is_overdue, verification_status, escalation_level)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (car_id) DO UPDATE SET
                root_cause = EXCLUDED.root_cause,
                corrective_action = EXCLUDED.corrective_action,
                response_date = EXCLUDED.response_date,
                is_overdue = EXCLUDED.is_overdue,
                verification_status = EXCLUDED.verification_status,
                escalation_level = EXCLUDED.escalation_level
            """,
            car["car_id"],
            car["issue_id"],
            car["supplier_id"],
            car.get("root_cause"),
            car.get("corrective_action"),
            car["due_date"],
            car.get("response_date"),
            car.get("is_overdue", False),
            car.get("verification_status", "Pending"),
            car.get("escalation_level", 0),
        )

    async def get_car(self, car_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM corrective_action_requests WHERE car_id = $1", car_id
        )
        return dict(row) if row else None

    async def list_cars_by_supplier(self, supplier_id: str) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM corrective_action_requests WHERE supplier_id = $1 ORDER BY created_at DESC",
            supplier_id,
        )
        return [dict(r) for r in rows]