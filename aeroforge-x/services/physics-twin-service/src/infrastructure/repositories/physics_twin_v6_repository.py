"""AeroForge-X Physics Twin V6 Repository

Persistence layer for ShopFloorDataCollectorService, DigitalTwinSynchronizerService,
DatasetVersioningService, DatasetDriftDetectionService, DatasetQualityScoreService,
PHMModelConfidenceService, MaintenanceDecisionAuditService.
Target tables: shop_floor_equipment, digital_twin_sync_log,
              dataset_versions, model_dataset_links, dataset_drift_records,
              dataset_quality_assessments, phm_confidence_predictions,
              maintenance_decision_audits
"""

from __future__ import annotations

from typing import Any, Optional

from src.infrastructure.repositories.base_repository import (
    AsyncpgRepository,
    InMemoryRepository,
)


class PhysicsTwinV6Repository(InMemoryRepository):

    def save_equipment(self, equip: dict) -> None:
        self._put("shop_floor_equipment", equip["equipment_id"], equip)

    def get_equipment(self, equipment_id: str) -> Optional[dict]:
        return self._get("shop_floor_equipment", equipment_id)

    def list_equipment(self, **filters) -> list[dict]:
        return self._list("shop_floor_equipment", **filters)

    def save_sync_log(self, log: dict) -> None:
        self._put("digital_twin_sync_log", log["sync_id"], log)

    def list_sync_logs(self, **filters) -> list[dict]:
        return self._list("digital_twin_sync_log", **filters)

    def save_dataset_version(self, ver: dict) -> None:
        self._put("dataset_versions", ver["dataset_version_id"], ver)

    def get_dataset_version(self, version_id: str) -> Optional[dict]:
        return self._get("dataset_versions", version_id)

    def list_dataset_versions(self, dataset_id: str) -> list[dict]:
        return self._list("dataset_versions", dataset_id=dataset_id)

    def save_model_dataset_link(self, link: dict) -> None:
        self._put("model_dataset_links", link["link_id"], link)

    def save_drift_record(self, drift: dict) -> None:
        self._put("dataset_drift_records", drift["drift_id"], drift)

    def list_drift_records(self, dataset_id: str) -> list[dict]:
        return self._list("dataset_drift_records", dataset_id=dataset_id)

    def save_quality_assessment(self, assessment: dict) -> None:
        self._put("dataset_quality_assessments", assessment["assessment_id"], assessment)

    def list_quality_assessments(self, dataset_id: str) -> list[dict]:
        return self._list("dataset_quality_assessments", dataset_id=dataset_id)

    def save_phm_prediction(self, pred: dict) -> None:
        self._put("phm_confidence_predictions", pred["prediction_id"], pred)

    def get_phm_prediction(self, prediction_id: str) -> Optional[dict]:
        return self._get("phm_confidence_predictions", prediction_id)

    def save_maintenance_audit(self, audit: dict) -> None:
        self._put("maintenance_decision_audits", audit["audit_id"], audit)

    def get_maintenance_audit(self, audit_id: str) -> Optional[dict]:
        return self._get("maintenance_decision_audits", audit_id)

    def list_maintenance_audits(self, prediction_id: str) -> list[dict]:
        return self._list("maintenance_decision_audits", prediction_id=prediction_id)


class AsyncpgPhysicsTwinV6Repository(AsyncpgRepository):

    async def save_equipment(self, equip: dict) -> None:
        await self._execute(
            """
            INSERT INTO shop_floor_equipment
                (equipment_id, equipment_name, equipment_type, protocol,
                 sampling_rate_ms, location, status, connection_config)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
            ON CONFLICT (equipment_id) DO UPDATE SET
                equipment_name = EXCLUDED.equipment_name,
                status = EXCLUDED.status,
                connection_config = EXCLUDED.connection_config
            """,
            equip["equipment_id"],
            equip["equipment_name"],
            equip["equipment_type"],
            equip["protocol"],
            equip.get("sampling_rate_ms", 1000),
            equip.get("location", ""),
            equip.get("status", "Offline"),
            self._json_dumps(equip.get("connection_config", {})),
        )

    async def get_equipment(self, equipment_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM shop_floor_equipment WHERE equipment_id = $1",
            equipment_id,
        )
        if row is None:
            return None
        result = dict(row)
        result["connection_config"] = self._json_loads(result.get("connection_config", "{}"))
        return result

    async def list_equipment(self, **filters) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM shop_floor_equipment ORDER BY registered_at DESC"
        )
        results = []
        for r in rows:
            d = dict(r)
            d["connection_config"] = self._json_loads(d.get("connection_config", "{}"))
            results.append(d)
        if filters:
            results = [r for r in results if all(r.get(k) == v for k, v in filters.items())]
        return results

    async def save_sync_log(self, log: dict) -> None:
        await self._execute(
            """
            INSERT INTO digital_twin_sync_log
                (sync_id, equipment_id, twin_state_hash, physical_state_hash,
                 is_synchronized, deviation_items, sync_duration_ms)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
            """,
            log["sync_id"],
            log["equipment_id"],
            log["twin_state_hash"],
            log["physical_state_hash"],
            log["is_synchronized"],
            self._json_dumps(log.get("deviation_items", [])),
            log.get("sync_duration_ms"),
        )

    async def list_sync_logs(self, **filters) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM digital_twin_sync_log ORDER BY synced_at DESC LIMIT 500"
        )
        results = []
        for r in rows:
            d = dict(r)
            d["deviation_items"] = self._json_loads(d.get("deviation_items", "[]"))
            results.append(d)
        if filters:
            results = [r for r in results if all(r.get(k) == v for k, v in filters.items())]
        return results

    async def save_dataset_version(self, ver: dict) -> None:
        await self._execute(
            """
            INSERT INTO dataset_versions
                (dataset_version_id, dataset_id, major, minor, patch,
                 source, sample_count, feature_schema, change_summary, fingerprint)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10::jsonb)
            ON CONFLICT (dataset_version_id) DO UPDATE SET
                sample_count = EXCLUDED.sample_count,
                feature_schema = EXCLUDED.feature_schema,
                fingerprint = EXCLUDED.fingerprint
            """,
            ver["dataset_version_id"],
            ver["dataset_id"],
            ver.get("major", 1),
            ver.get("minor", 0),
            ver.get("patch", 0),
            ver.get("source", ""),
            ver.get("sample_count", 0),
            self._json_dumps(ver.get("feature_schema", {})),
            ver.get("change_summary", ""),
            self._json_dumps(ver.get("fingerprint", {})),
        )

    async def get_dataset_version(self, version_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM dataset_versions WHERE dataset_version_id = $1",
            version_id,
        )
        if row is None:
            return None
        result = dict(row)
        result["feature_schema"] = self._json_loads(result.get("feature_schema", "{}"))
        result["fingerprint"] = self._json_loads(result.get("fingerprint", "{}"))
        return result

    async def list_dataset_versions(self, dataset_id: str) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM dataset_versions WHERE dataset_id = $1 ORDER BY major DESC, minor DESC, patch DESC",
            dataset_id,
        )
        results = []
        for r in rows:
            d = dict(r)
            d["feature_schema"] = self._json_loads(d.get("feature_schema", "{}"))
            d["fingerprint"] = self._json_loads(d.get("fingerprint", "{}"))
            results.append(d)
        return results

    async def save_model_dataset_link(self, link: dict) -> None:
        await self._execute(
            """
            INSERT INTO model_dataset_links (link_id, model_id, dataset_version_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (link_id) DO NOTHING
            """,
            link["link_id"],
            link["model_id"],
            link["dataset_version_id"],
        )

    async def save_drift_record(self, drift: dict) -> None:
        await self._execute(
            """
            INSERT INTO dataset_drift_records
                (drift_id, dataset_id, reference_dataset_id, drift_type,
                 ks_statistic, ks_p_value, psi_value, concept_drift_magnitude,
                 is_drift_detected, affected_features, recommended_action)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            drift["drift_id"],
            drift["dataset_id"],
            drift["reference_dataset_id"],
            drift.get("drift_type", "Feature"),
            drift.get("ks_statistic", 0.0),
            drift.get("ks_p_value", 1.0),
            drift.get("psi_value", 0.0),
            drift.get("concept_drift_magnitude", 0.0),
            drift.get("is_drift_detected", False),
            drift.get("affected_features", []),
            drift.get("recommended_action", ""),
        )

    async def list_drift_records(self, dataset_id: str) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM dataset_drift_records WHERE dataset_id = $1 ORDER BY detected_at DESC",
            dataset_id,
        )
        return [dict(r) for r in rows]

    async def save_quality_assessment(self, assessment: dict) -> None:
        await self._execute(
            """
            INSERT INTO dataset_quality_assessments
                (assessment_id, dataset_id, overall_score, completeness_score,
                 consistency_score, timeliness_score, representativeness_score,
                 improvement_recommendations)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            assessment["assessment_id"],
            assessment["dataset_id"],
            assessment.get("overall_score", 0.0),
            assessment.get("completeness_score", 0.0),
            assessment.get("consistency_score", 0.0),
            assessment.get("timeliness_score", 0.0),
            assessment.get("representativeness_score", 0.0),
            assessment.get("improvement_recommendations", ""),
        )

    async def list_quality_assessments(self, dataset_id: str) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM dataset_quality_assessments WHERE dataset_id = $1 ORDER BY assessed_at DESC",
            dataset_id,
        )
        return [dict(r) for r in rows]

    async def save_phm_prediction(self, pred: dict) -> None:
        await self._execute(
            """
            INSERT INTO phm_confidence_predictions
                (prediction_id, component_id, rul_point_estimate,
                 confidence_lower, confidence_upper, data_quality_score,
                 is_low_confidence, confidence_level)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (prediction_id) DO UPDATE SET
                rul_point_estimate = EXCLUDED.rul_point_estimate,
                confidence_lower = EXCLUDED.confidence_lower,
                confidence_upper = EXCLUDED.confidence_upper,
                is_low_confidence = EXCLUDED.is_low_confidence
            """,
            pred["prediction_id"],
            pred["component_id"],
            pred.get("rul_point_estimate", 0.0),
            pred.get("confidence_lower", 0.0),
            pred.get("confidence_upper", 0.0),
            pred.get("data_quality_score", 100.0),
            pred.get("is_low_confidence", False),
            pred.get("confidence_level", 0.95),
        )

    async def get_phm_prediction(self, prediction_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM phm_confidence_predictions WHERE prediction_id = $1",
            prediction_id,
        )
        return dict(row) if row else None

    async def save_maintenance_audit(self, audit: dict) -> None:
        await self._execute(
            """
            INSERT INTO maintenance_decision_audits
                (audit_id, prediction_id, rul_point_estimate, confidence_lower,
                 confidence_upper, data_quality_score, decision_threshold,
                 decision_outcome, engineer_approval, review_required,
                 review_decision, reviewer)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (audit_id) DO UPDATE SET
                decision_outcome = EXCLUDED.decision_outcome,
                review_decision = EXCLUDED.review_decision,
                reviewer = EXCLUDED.reviewer,
                reviewed_at = NOW()
            """,
            audit["audit_id"],
            audit["prediction_id"],
            audit.get("rul_point_estimate", 0.0),
            audit.get("confidence_lower", 0.0),
            audit.get("confidence_upper", 0.0),
            audit.get("data_quality_score", 100.0),
            audit.get("decision_threshold", 0.0),
            audit.get("decision_outcome", ""),
            audit.get("engineer_approval", ""),
            audit.get("review_required", False),
            audit.get("review_decision", ""),
            audit.get("reviewer", ""),
        )

    async def get_maintenance_audit(self, audit_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM maintenance_decision_audits WHERE audit_id = $1",
            audit_id,
        )
        return dict(row) if row else None

    async def list_maintenance_audits(self, prediction_id: str) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM maintenance_decision_audits WHERE prediction_id = $1 ORDER BY created_at DESC",
            prediction_id,
        )
        return [dict(r) for r in rows]