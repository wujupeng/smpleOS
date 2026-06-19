"""AeroForge-X v6.0 DFX API (aircraft-core-service)

Endpoints for observability, certification dashboard, RBAC,
encryption, idempotent propagation, and data integrity.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.domain.services.dfx.certification_compliance_dashboard_service import (
    CertificationComplianceDashboardService,
    DashboardPeriod,
)
from src.domain.services.dfx.data_integrity_verification_service import (
    DataIntegrityVerificationService,
    IntegrityCheckType,
)
from src.domain.services.dfx.idempotent_propagation_service import (
    IdempotentPropagationService,
)
from src.domain.services.dfx.observability_metrics_service import (
    ObservabilityMetricsService,
)
from src.domain.services.dfx.rbac_permission_service import (
    RBACPermissionService,
    Permission,
    Role,
    User,
)
from src.domain.services.dfx.supplier_data_encryption_service import (
    SupplierDataEncryptionService,
    EncryptionAlgorithm,
    TLSVersion,
    TLSConfig,
)

router = APIRouter(prefix="/api/v6/aircraft-core/dfx", tags=["v6-dfx"])

_metrics_svc = ObservabilityMetricsService()
_dashboard_svc = CertificationComplianceDashboardService()
_rbac_svc = RBACPermissionService()
_encryption_svc = SupplierDataEncryptionService()
_idempotent_svc = IdempotentPropagationService()
_integrity_svc = DataIntegrityVerificationService()


@router.get("/metrics")
async def get_metrics():
    return [s.to_dict() for s in _metrics_svc.getAllSummaries()]


@router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    return {"content": _metrics_svc.exportPrometheusFormat()}


@router.get("/metrics/alerts")
async def check_metric_alerts():
    return _metrics_svc.checkAlerts()


@router.post("/metrics/record")
async def record_metric(body: dict):
    metric_name = body.get("metric_name", "")
    value = body.get("value", 0.0)
    labels = body.get("labels", {})
    sample = _metrics_svc.recordDuration(metric_name, value, labels)
    if sample is None:
        sample = _metrics_svc.recordGauge(metric_name, value, labels)
    if sample is None:
        return {"recorded": False, "reason": "Unknown metric"}
    return {"recorded": True, "sample": sample.to_dict()}


@router.post("/compliance-dashboard")
async def generate_compliance_dashboard(body: dict):
    project_id = body.get("project_id", "")
    period = DashboardPeriod(body.get("period", "Monthly"))
    dashboard = _dashboard_svc.generateDashboard(
        project_id=project_id,
        period=period,
        traceability_data=body.get("traceability"),
        checklist_data=body.get("checklists"),
        evidence_data=body.get("evidence_packages"),
    )
    return dashboard.to_dict()


@router.post("/rbac/users")
async def register_user(body: dict):
    user = User(
        user_id=body.get("user_id", ""),
        username=body.get("username", ""),
        roles=[Role(r) for r in body.get("roles", [])],
    )
    registered = _rbac_svc.registerUser(user)
    return registered.to_dict()


@router.post("/rbac/check")
async def check_permission(body: dict):
    user_id = body.get("user_id", "")
    permission = Permission(body.get("permission", ""))
    result = _rbac_svc.checkPermission(user_id, permission)
    return result.to_dict()


@router.post("/rbac/dual-auth/check")
async def check_dual_auth(body: dict):
    prod_user = body.get("production_user_id", "")
    safety_user = body.get("safety_user_id", "")
    permission = Permission(body.get("permission", "shop_floor:command"))
    result = _rbac_svc.checkDualAuthorization(prod_user, safety_user, permission)
    return result.to_dict()


@router.post("/encryption/keys")
async def generate_encryption_key(body: dict):
    algorithm = EncryptionAlgorithm(body.get("algorithm", "AES-256-GCM"))
    key = _encryption_svc.generateEncryptionKey(algorithm)
    return key.to_dict()


@router.post("/encryption/encrypt")
async def encrypt_data(body: dict):
    plaintext = body.get("plaintext", "")
    key_id = body.get("key_id", "")
    payload = _encryption_svc.encryptData(plaintext, key_id)
    return payload.to_dict()


@router.post("/encryption/decrypt")
async def decrypt_data(body: dict):
    payload_id = body.get("payload_id", "")
    result = _encryption_svc.decryptData(payload_id)
    return result.to_dict()


@router.get("/encryption/tls-config")
async def get_tls_config():
    return _encryption_svc.getTLSConfig().to_dict()


@router.post("/idempotent/propagate")
async def idempotent_propagate(body: dict):
    block_id = body.get("block_id", "")
    change_data = body.get("change_data", {})
    expected_version = body.get("expected_version", 0)
    result = _idempotent_svc.propagateWithIdempotency(
        block_id, change_data, expected_version
    )
    return result.to_dict()


@router.get("/idempotent/dashboard/{equipment_id}")
async def get_dashboard_degradation(equipment_id: str):
    dashboard = _idempotent_svc.checkDashboardDegradation(equipment_id)
    return dashboard.to_dict()


@router.post("/integrity/verify")
async def verify_integrity(body: dict):
    check_type = IntegrityCheckType(body.get("check_type", ""))
    resource_id = body.get("resource_id", "")
    data = body.get("data", {})

    handlers = {
        IntegrityCheckType.BASELINE_CONSISTENCY: lambda: _integrity_svc.verifyBaselineConsistency(
            resource_id, data.get("baseline", {}), data.get("current", {})
        ),
        IntegrityCheckType.EVIDENCE_IMMUTABILITY: lambda: _integrity_svc.verifyEvidenceImmutability(
            resource_id, data
        ),
        IntegrityCheckType.SUPPLIER_AUDIT_TRAIL: lambda: _integrity_svc.verifySupplierAuditTrail(
            resource_id, data.get("entries", [])
        ),
        IntegrityCheckType.SHOP_FLOOR_DATA_QUALITY: lambda: _integrity_svc.verifyShopFloorDataQuality(
            resource_id, data.get("data_points", [])
        ),
        IntegrityCheckType.MATERIAL_LOT_VERIFIABILITY: lambda: _integrity_svc.verifyMaterialLotVerifiability(
            resource_id, data.get("lot_data", {}), data.get("trace_chain", [])
        ),
        IntegrityCheckType.UQ_REPRODUCIBILITY: lambda: _integrity_svc.verifyUQReproducibility(
            resource_id, data.get("original", {}), data.get("reproduced", {})
        ),
    }

    handler = handlers.get(check_type)
    if handler is None:
        return {"verified": False, "reason": "Unknown check type"}

    result = handler()
    return result.to_dict()


@router.post("/integrity/report")
async def generate_integrity_report(body: dict):
    checks_data = body.get("checks", [])
    from src.domain.services.dfx.data_integrity_verification_service import (
        IntegrityCheckResult,
        IntegrityStatus,
    )
    checks = []
    for c in checks_data:
        checks.append(IntegrityCheckResult(
            check_id=c.get("check_id", ""),
            check_type=IntegrityCheckType(c.get("check_type", "")),
            resource_id=c.get("resource_id", ""),
            status=IntegrityStatus(c.get("status", "NotChecked")),
        ))
    report = _integrity_svc.generateFullReport(checks)
    return report.to_dict()