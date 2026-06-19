import pytest

from services.analytics.src.domain.services.analytics_domain_service import AnalyticsDomainService


class TestDesignMetrics:
    def test_empty_metrics(self) -> None:
        service = AnalyticsDomainService()
        metrics = service.query_design_metrics()
        assert "message" in metrics

    def test_design_progress(self) -> None:
        service = AnalyticsDomainService()
        service.add_design_record("p-001", {"status": "completed", "has_violation": False, "cae_status": "completed", "iteration_count": 3})
        service.add_design_record("p-001", {"status": "in_progress", "has_violation": True, "cae_status": "running", "iteration_count": 5})
        service.add_design_record("p-001", {"status": "completed", "has_violation": False, "cae_status": "completed", "iteration_count": 2})
        metrics = service.query_design_metrics("p-001")
        assert metrics["design_progress_pct"] == pytest.approx(66.7, abs=0.1)
        assert metrics["violation_rate"] == pytest.approx(33.3, abs=0.1)
        assert metrics["cae_completion_rate"] == pytest.approx(66.7, abs=0.1)
        assert metrics["avg_iterations"] == pytest.approx(3.3, abs=0.1)


class TestManufacturingMetrics:
    def test_manufacturing_metrics(self) -> None:
        service = AnalyticsDomainService()
        service.add_manufacturing_record("p-001", {"status": "completed", "on_time": True, "utilization_pct": 85, "deviation_mm": 0.02})
        service.add_manufacturing_record("p-001", {"status": "completed", "on_time": False, "utilization_pct": 70, "deviation_mm": 0.08})
        service.add_manufacturing_record("p-001", {"status": "in_progress", "on_time": True, "utilization_pct": 90, "deviation_mm": 0.005})
        metrics = service.query_manufacturing_metrics("p-001")
        assert metrics["work_order_completion_rate"] == pytest.approx(66.7, abs=0.1)
        assert metrics["on_time_rate"] == pytest.approx(66.7, abs=0.1)
        assert metrics["avg_workstation_utilization"] > 0


class TestQualityMetrics:
    def test_quality_metrics(self) -> None:
        service = AnalyticsDomainService()
        service.add_quality_record("p-001", {"iqc_passed": True, "capa_status": "closed", "cpk": 1.5})
        service.add_quality_record("p-001", {"iqc_passed": True, "capa_status": "open", "cpk": 1.2})
        service.add_quality_record("p-001", {"iqc_passed": False, "capa_status": "closed", "cpk": 0.9, "is_nc": True, "nc_category": "dimension", "nc_count": 3})
        metrics = service.query_quality_metrics("p-001")
        assert metrics["iqc_pass_rate"] == pytest.approx(66.7, abs=0.1)
        assert metrics["capa_close_rate"] == pytest.approx(66.7, abs=0.1)
        assert metrics["avg_cpk"] > 0

    def test_nc_pareto(self) -> None:
        service = AnalyticsDomainService()
        service.add_quality_record("p-001", {"iqc_passed": False, "is_nc": True, "nc_category": "dimension", "nc_count": 5})
        service.add_quality_record("p-001", {"iqc_passed": False, "is_nc": True, "nc_category": "surface", "nc_count": 3})
        service.add_quality_record("p-001", {"iqc_passed": False, "is_nc": True, "nc_category": "dimension", "nc_count": 2})
        metrics = service.query_quality_metrics("p-001")
        assert len(metrics["nc_pareto"]) > 0
        assert metrics["nc_pareto"][0]["category"] == "dimension"


class TestTraceabilityMetrics:
    def test_traceability_metrics(self) -> None:
        service = AnalyticsDomainService()
        service.add_trace_record("p-001", {"is_complete": True, "query_time_ms": 50})
        service.add_trace_record("p-001", {"is_complete": True, "query_time_ms": 80})
        service.add_trace_record("p-001", {"is_complete": False, "query_time_ms": 120, "recall_scope": 5})
        metrics = service.query_traceability_metrics("p-001")
        assert metrics["trace_completeness_rate"] == pytest.approx(66.7, abs=0.1)
        assert metrics["avg_query_time_ms"] > 0


class TestSupplyChainMetrics:
    def test_supply_chain_metrics(self) -> None:
        service = AnalyticsDomainService()
        service.add_supply_record("p-001", {"supplier_id": "sup-001", "performance_score": 0.9, "on_time": True, "turnover_rate": 6.5})
        service.add_supply_record("p-001", {"supplier_id": "sup-002", "performance_score": 0.7, "on_time": False, "turnover_rate": 4.2})
        service.add_supply_record("p-001", {"supplier_id": "sup-001", "performance_score": 0.85, "on_time": True, "turnover_rate": 7.0})
        metrics = service.query_supply_chain_metrics("p-001")
        assert metrics["po_on_time_rate"] == pytest.approx(66.7, abs=0.1)
        assert len(metrics["supplier_ranking"]) > 0
        assert metrics["supplier_ranking"][0]["supplier_id"] == "sup-001"


class TestCrossDomainAnalysis:
    def test_cross_domain_no_issues(self) -> None:
        service = AnalyticsDomainService()
        service.add_design_record("p-001", {"status": "completed", "has_violation": False, "cae_status": "completed", "iteration_count": 1})
        analysis = service.cross_domain_analysis("p-001")
        assert "design_metrics_summary" in analysis
        assert "manufacturing_metrics_summary" in analysis
        assert "quality_metrics_summary" in analysis
        assert "cross_domain_links" in analysis

    def test_cross_domain_with_violations(self) -> None:
        service = AnalyticsDomainService()
        for _ in range(10):
            service.add_design_record("p-001", {"status": "in_progress", "has_violation": True, "cae_status": "running", "iteration_count": 5})
        analysis = service.cross_domain_analysis("p-001")
        assert len(analysis["cross_domain_links"]) > 0

    def test_cross_domain_low_supplier_score(self) -> None:
        service = AnalyticsDomainService()
        service.add_supply_record("p-001", {"supplier_id": "sup-bad", "performance_score": 0.5, "on_time": False})
        analysis = service.cross_domain_analysis("p-001")
        links = analysis["cross_domain_links"]
        supplier_links = [l for l in links if l["source"] == "supplier_quality"]
        assert len(supplier_links) > 0