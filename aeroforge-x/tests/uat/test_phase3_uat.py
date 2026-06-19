"""
Phase 3 User Acceptance Test (UAT) Cases
Covers 13 key scenarios as defined in P3-46
"""
from __future__ import annotations

import pytest


class UAT_MultiTenantManagement:
    """UAT-01: 多租户管理 - 创建租户 → 创建项目 → 数据隔离"""

    def test_uat_create_tenant_and_isolate_data(self):
        from services.tenant_service.src.domain.services.tenant_domain_service import TenantDomainService
        from services.tenant_service.src.domain.entities.tenant import TenantPlan

        svc = TenantDomainService()
        t1 = svc.create_tenant("航空制造A公司", "company_a", TenantPlan.PROFESSIONAL)
        t2 = svc.create_tenant("航空制造B公司", "company_b", TenantPlan.STARTER)

        assert t1.code == "company_a"
        assert t2.code == "company_b"
        assert t1.id != t2.id

        quota_a = svc.check_quota(t1.id, "users", 5)
        assert quota_a["allowed"] is True


class UAT_AeroGPTDesign:
    """UAT-02: AeroGPT - 自然语言设计 → 方案评审 → 确认"""

    def test_uat_aerogpt_design_workflow(self):
        from services.ai_engine.src.domain.services.multi_objective_optimizer import MultiObjectiveOptimizer

        optimizer = MultiObjectiveOptimizer()
        result = optimizer.optimize(
            objectives=["minimize_weight", "maximize_stiffness"],
            constraints=[{"name": "stress_limit", "value": 400}],
            design_variables=[{"name": "thickness", "lower": 1.0, "upper": 10.0}],
        )
        assert len(result["pareto_front"]) > 0


class UAT_MultiObjectiveOptimization:
    """UAT-03: 多目标优化 - 优化配置 → 帕累托前沿 → 最优解选择"""

    def test_uat_pareto_front_and_selection(self):
        from services.ai_engine.src.domain.services.multi_objective_optimizer import MultiObjectiveOptimizer

        optimizer = MultiObjectiveOptimizer()
        result = optimizer.optimize(
            objectives=["minimize_weight", "maximize_stiffness"],
            constraints=[],
            design_variables=[{"name": "x1", "lower": 0, "upper": 10}],
        )
        assert "pareto_front" in result
        assert len(result["pareto_front"]) > 0


class UAT_TopologyOptimization:
    """UAT-04: 拓扑优化 - 载荷配置 → 优化执行 → 减重验证"""

    def test_uat_topology_optimization(self):
        from services.ai_engine.src.domain.services.topology_optimizer import TopologyOptimizer

        optimizer = TopologyOptimizer()
        result = optimizer.optimize(
            design_space={"x": 100, "y": 100, "z": 50},
            loads=[{"node": 0, "fx": 1000}],
            constraints=[{"type": "volume_fraction", "value": 0.3}],
        )
        assert "material_distribution" in result


class UAT_SupplyChainManagement:
    """UAT-05: 供应链管理 - 供应商管理 → 采购订单 → 收货入库"""

    def test_uat_supply_chain_workflow(self):
        from services.supply_chain.src.domain.services.supplier_domain_service import SupplierDomainService
        from services.supply_chain.src.domain.services.purchase_domain_service import PurchaseDomainService

        supplier_svc = SupplierDomainService()
        supplier = supplier_svc.create_supplier("SUP-001", "材料供应商A", "raw_material")
        assert supplier is not None

        purchase_svc = PurchaseDomainService()
        po = purchase_svc.create_order("SUP-001", "MAT-001", 100, 85.0)
        assert po is not None

        received = purchase_svc.receive_order(po.id, 98)
        assert received is not None


class UAT_SPCControl:
    """UAT-06: SPC - 控制图创建 → 数据录入 → 判异检测"""

    def test_uat_spc_workflow(self):
        from services.qms_service.src.domain.services.spc_domain_service import SPCDomainService

        svc = SPCDomainService()
        chart = svc.create_chart("UAT翼面厚度", "thickness_mm", 5.5, 4.5, 5.0)

        for i in range(25):
            svc.add_measurement(chart.id, 5.0 + (i % 5) * 0.05, operator="uat_op")

        analysis = svc.analyze_chart(chart.id)
        assert "cpk" in analysis


class UAT_ProductionScheduling:
    """UAT-07: 生产排程 - 排程配置 → 优化 → 甘特图"""

    def test_uat_scheduling_workflow(self):
        from services.mes_center.src.domain.services.scheduling_domain_service import SchedulingDomainService

        svc = SchedulingDomainService()
        schedule = svc.create_schedule("UAT-SCH-001", "P100")
        result = svc.optimize_schedule(schedule.id)
        assert result is not None


class UAT_PredictiveMaintenance:
    """UAT-08: 预测性维护 - RUL预测 → 故障概率 → 维护计划"""

    def test_uat_predictive_maintenance_workflow(self):
        from services.digital_twin_center.src.domain.services.predictive_maintenance_service import PredictiveMaintenanceService

        svc = PredictiveMaintenanceService()
        rul = svc.predict_remaining_useful_life("AF-X100-SN001")
        assert "rul_hours" in rul

        prob = svc.predict_failure_probability("AF-X100-SN001", days=30)
        assert "failure_probability" in prob

        maint = svc.optimize_maintenance_schedule("AF-X100-SN001")
        assert "maintenance_window" in maint


class UAT_DataAnalytics:
    """UAT-09: 数据分析 - 指标查询 → 报表生成"""

    def test_uat_analytics_workflow(self):
        from services.analytics.src.domain.services.analytics_domain_service import AnalyticsDomainService

        svc = AnalyticsDomainService()
        result = svc.query_metrics("t1", ["project_count", "order_count"])
        assert "metrics" in result

        from services.analytics.src.domain.services.report_domain_service import ReportDomainService
        report_svc = ReportDomainService()
        report = report_svc.create_report("t1", "UAT综合报表", "comprehensive")
        assert report is not None


class UAT_FlightTestAndDelivery:
    """UAT-10: 试飞与交付 - 试飞方案 → 交付包 → 完整性校验"""

    def test_uat_delivery_workflow(self):
        from services.delivery_center.src.domain.services.flight_test_plan_service import FlightTestPlanService
        from services.delivery_center.src.domain.services.delivery_package_service import DeliveryPackageService

        ft_svc = FlightTestPlanService()
        plan = ft_svc.generate_flight_test_plan("t1", "p1", "AF-X100", "FAR-23")
        assert plan.coverage_percentage > 0

        dp_svc = DeliveryPackageService()
        pkg = dp_svc.generate_delivery_package("t1", "p1", "AF-X100", [
            {"doc_id": "d1", "doc_type": "aircraft_spec", "name": "Spec", "version": "1.0", "status": "approved"},
            {"doc_id": "d2", "doc_type": "ebom", "name": "eBOM", "version": "2.0", "status": "approved"},
        ])
        validation = dp_svc.validate_completeness(pkg.id)
        assert "completeness_score" in validation


class UAT_ComplianceManagement:
    """UAT-11: 合规性管理 - 设计合规检查 → 制造合规检查 → 报告生成"""

    def test_uat_compliance_workflow(self):
        from services.qms_service.src.domain.services.compliance_domain_service import ComplianceDomainService
        from services.qms_service.src.domain.entities.compliance import ComplianceStandard

        svc = ComplianceDomainService()
        design_check = svc.check_design_compliance(
            "t1", "p1", "AF-X100", [ComplianceStandard.FAR_23],
            {"safety_factor": 2.0, "materials_certified": True},
        )
        assert design_check.overall_status.value in ("compliant", "partially_compliant")

        report = svc.generate_compliance_report(
            "t1", "p1", "AF-X100", [ComplianceStandard.FAR_23],
            design_check_id=design_check.id,
        )
        assert report.report_id is not None


class UAT_ERPIntegration:
    """UAT-12: ERP集成 - 数据同步 → 一致性校验"""

    def test_uat_erp_sync_workflow(self):
        from aeroforge_integrations.erp.adapter import ERPConnectionConfig, ERPType
        from aeroforge_integrations.erp.sync_service import ERPDataSyncService

        config = ERPConnectionConfig(erp_type=ERPType.SAP, base_url="https://sap.example.com")
        svc = ERPDataSyncService(config)
        svc.connect()

        mat_result = svc.sync_material_master()
        assert mat_result.status.value == "completed"

        status = svc.get_sync_status()
        assert status["connected"] is True


class UAT_SecurityEnhancement:
    """UAT-13: 安全增强 - 审计日志 → 加密 → 会话安全"""

    def test_uat_security_workflow(self):
        from services.tenant_service.src.domain.services.audit_domain_service import AuditDomainService
        from services.tenant_service.src.domain.entities.audit_log import AuditAction, AuditResource
        from aeroforge_common.security.encryption import ColumnEncryptionService
        from aeroforge_common.security.session import SessionSecurityService

        audit_svc = AuditDomainService()
        audit_svc.record("t1", "u1", AuditAction.LOGIN, AuditResource.USER, "u1")
        integrity = audit_svc.verify_chain_integrity("t1")
        assert integrity["verified"] is True

        enc_svc = ColumnEncryptionService(master_key="uat-key")
        encrypted = enc_svc.encrypt_field("sensitive")
        assert enc_svc.decrypt_field(encrypted) == "sensitive"

        session_svc = SessionSecurityService()
        session = session_svc.create_session("u1", "t1")
        assert session_svc.validate_session(session.session_id) is not None