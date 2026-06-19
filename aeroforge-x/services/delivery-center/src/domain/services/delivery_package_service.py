from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from ..entities.delivery_entities import DeliveryDocument, DeliveryPackage

logger = logging.getLogger(__name__)


class DeliveryPackageService:
    REQUIRED_DOC_TYPES = [
        "aircraft_spec",
        "design_review_report",
        "cfd_report",
        "fea_report",
        "ebom",
        "mbom",
        "bom_conformance_report",
        "process_route",
        "work_order_records",
        "manufacturing_deviation_report",
        "iqc_records",
        "ipqc_records",
        "fqc_records",
        "oqc_records",
        "capa_records",
        "spc_report",
        "traceability_report",
        "flight_test_plan",
        "compliance_report",
        "airworthiness_checklist",
    ]

    def __init__(self) -> None:
        self._packages: dict[str, DeliveryPackage] = {}

    def generate_delivery_package(
        self,
        tenant_id: str,
        project_id: str,
        aircraft_model: str,
        available_documents: list[dict[str, Any]],
        package_type: str = "full",
    ) -> DeliveryPackage:
        package = DeliveryPackage(
            tenant_id=tenant_id,
            project_id=project_id,
            aircraft_model=aircraft_model,
            package_type=package_type,
        )

        for doc_data in available_documents:
            doc = DeliveryDocument(
                doc_id=doc_data.get("doc_id", ""),
                doc_type=doc_data.get("doc_type", ""),
                name=doc_data.get("name", ""),
                version=doc_data.get("version", "1.0"),
                status=doc_data.get("status", "pending"),
                file_path=doc_data.get("file_path", ""),
                pages=doc_data.get("pages", 0),
                required=doc_data.get("required", True),
                signatures=doc_data.get("signatures", []),
            )
            package.add_document(doc)

        required_types = self.REQUIRED_DOC_TYPES if package_type == "full" else self._get_minimal_types()
        package.validate_completeness(required_types)

        package.generated_at = datetime.now(timezone.utc)
        package.status = "generated"

        package.add_domain_event(DomainEvent(
            event_type="delivery_package.generated",
            aggregate_id=package.id,
            payload={
                "tenant_id": tenant_id,
                "project_id": project_id,
                "aircraft_model": aircraft_model,
                "total_documents": len(package.documents),
                "completeness_score": package.completeness_score,
            },
        ))

        self._packages[package.id] = package
        logger.info(
            "Delivery package generated: project=%s model=%s docs=%d completeness=%.1f%%",
            project_id, aircraft_model, len(package.documents), package.completeness_score,
        )
        return package

    def get_package(self, package_id: str) -> DeliveryPackage | None:
        return self._packages.get(package_id)

    def validate_completeness(self, package_id: str) -> dict[str, Any]:
        package = self._packages.get(package_id)
        if package is None:
            return {"error": "Package not found"}

        required_types = self.REQUIRED_DOC_TYPES if package.package_type == "full" else self._get_minimal_types()
        return package.validate_completeness(required_types)

    def generate_package_index(self, package_id: str) -> dict[str, Any]:
        package = self._packages.get(package_id)
        if package is None:
            return {"error": "Package not found"}

        return package.generate_index()

    def list_packages(self, tenant_id: str, project_id: str | None = None) -> list[DeliveryPackage]:
        packages = [p for p in self._packages.values() if p.tenant_id == tenant_id]
        if project_id:
            packages = [p for p in packages if p.project_id == project_id]
        return packages

    def _get_minimal_types(self) -> list[str]:
        return [
            "aircraft_spec",
            "ebom",
            "compliance_report",
            "airworthiness_checklist",
        ]