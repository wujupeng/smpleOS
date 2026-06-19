$files = @(
  "physics-twin-service\src\domain\services\digital_factory\shop_floor_data_collector_service.py",
  "physics-twin-service\src\domain\services\digital_factory\digital_twin_synchronizer_service.py",
  "physics-twin-service\src\domain\services\generative_design\uncertainty_quantification_service.py",
  "physics-twin-service\src\domain\services\generative_design\seven_discipline_mdo_service.py",
  "physics-twin-service\src\domain\services\data_governance\dataset_versioning_service.py",
  "physics-twin-service\src\domain\services\data_governance\dataset_drift_detection_service.py",
  "physics-twin-service\src\domain\services\data_governance\dataset_quality_score_service.py",
  "physics-twin-service\src\domain\services\fleet_intelligence\phm_model_confidence_service.py",
  "physics-twin-service\src\domain\services\fleet_intelligence\maintenance_decision_audit_service.py",
  "physics-twin-service\src\domain\services\dfx\circuit_breaker_reconnect_service.py",
  "physics-twin-service\src\domain\services\dfx\plugin_registry_service.py",
  "workflow-engine-service\src\domain\services\certification\certification_evidence_assembly_service.py",
  "workflow-engine-service\src\domain\services\configuration_management\configuration_change_control_service.py",
  "workflow-engine-service\src\domain\services\supplier\supplier_car_service.py",
  "workflow-engine-service\src\domain\services\digital_factory\shop_floor_event_emitter_service.py",
  "workflow-engine-service\src\domain\services\integration\cross_program_event_orchestrator_service.py",
  "workflow-engine-service\src\domain\services\dfx\audit_trail_service.py",
  "workflow-engine-service\src\domain\services\dfx\structured_logging_service.py"
)
$base = "C:\Users\DELL\Documents\dev\smpleOS\aeroforge-x\services"
foreach ($f in $files) {
    $path = Join-Path $base $f
    if (-not (Test-Path $path)) {
        Write-Host "SKIP (not found): $f"
        continue
    }
    $content = Get-Content $path -Raw -Encoding UTF8
    $content = $content -replace 'def __init__\(self\) -> None:', 'def __init__(self, repo=None) -> None:'
    $content = $content -replace '(def __init__\(self, repo=None\) -> None:\r?\n(\s+))self\._', "`$1self._repo = repo`n`$1self._"
    [System.IO.File]::WriteAllText($path, $content)
    Write-Host "Updated: $f"
}
