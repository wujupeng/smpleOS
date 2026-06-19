import pytest

from services.qms_service.src.domain.entities.spc_control_chart import (
    SPCControlChart, ChartType, ChartStatus,
    SpecificationLimits, ControlLimits, OutOfControlRule,
)
from services.qms_service.src.domain.entities.spc_measurement import SPCMeasurement
from services.qms_service.src.domain.services.spc_domain_service import SPCDomainService


class TestSPCControlChartEntity:
    def test_create_chart(self) -> None:
        chart = SPCControlChart(
            process_name="CNC Milling",
            characteristic_name="Bore Diameter",
            chart_type=ChartType.X_BAR_R,
            specification_limits=SpecificationLimits(usl=10.05, lsl=9.95, target=10.0),
        )
        assert chart.status == ChartStatus.ACTIVE
        assert len(chart.out_of_control_rules) == 8

    def test_set_control_limits(self) -> None:
        chart = SPCControlChart(process_name="Test", characteristic_name="Test")
        chart.set_control_limits(ucl=10.1, lcl=9.9, cl=10.0)
        assert chart.control_limits.ucl == 10.1
        assert chart.control_limits.lcl == 9.9
        assert chart.control_limits.cl == 10.0

    def test_suspend_activate(self) -> None:
        chart = SPCControlChart(process_name="Test", characteristic_name="Test")
        chart.suspend()
        assert chart.status == ChartStatus.SUSPENDED
        chart.activate()
        assert chart.status == ChartStatus.ACTIVE

    def test_chart_to_dict(self) -> None:
        chart = SPCControlChart(
            tenant_id="t-001", process_name="CNC", characteristic_name="Dia",
            specification_limits=SpecificationLimits(usl=10.05, lsl=9.95, target=10.0),
        )
        d = chart.to_dict()
        assert d["process_name"] == "CNC"
        assert d["specification_limits"]["usl"] == 10.05


class TestSPCMeasurementEntity:
    def test_compute_statistics(self) -> None:
        m = SPCMeasurement(measurement_values=[10.0, 10.1, 9.9, 10.0, 10.05])
        m.compute_statistics()
        assert abs(m.mean - 10.01) < 0.01
        assert m.range_val == pytest.approx(0.2, abs=0.01)
        assert m.std_dev > 0

    def test_single_value(self) -> None:
        m = SPCMeasurement(measurement_values=[10.0])
        m.compute_statistics()
        assert m.mean == 10.0
        assert m.range_val == 0.0
        assert m.std_dev == 0.0


class TestSPCDomainService:
    def test_create_control_chart(self) -> None:
        service = SPCDomainService()
        chart = service.create_control_chart(
            tenant_id="t-001",
            project_id="p-001",
            chart_type=ChartType.X_BAR_R,
            process_name="CNC Milling",
            characteristic_name="Bore Diameter",
            specification_limits=SpecificationLimits(usl=10.05, lsl=9.95, target=10.0),
        )
        assert chart.process_name == "CNC Milling"
        assert len(chart.domain_events) == 1

    def test_add_measurement(self) -> None:
        service = SPCDomainService()
        chart = service.create_control_chart(
            "t-001", "p-001", ChartType.X_BAR_R, "CNC", "Dia",
            SpecificationLimits(usl=10.05, lsl=9.95, target=10.0),
        )
        chart.set_control_limits(ucl=10.05, lcl=9.95, cl=10.0)

        m = service.add_measurement(chart.id, 1, [10.0, 10.01, 9.99, 10.0, 10.02])
        assert m is not None
        assert m.mean > 0
        assert m.range_val > 0

    def test_calculate_control_limits(self) -> None:
        service = SPCDomainService()
        chart = service.create_control_chart(
            "t-001", "p-001", ChartType.X_BAR_R, "CNC", "Dia",
            SpecificationLimits(usl=10.05, lsl=9.95, target=10.0),
            sample_size=5,
        )

        for i in range(5):
            service.add_measurement(chart.id, i + 1, [10.0, 10.01, 9.99, 10.0, 10.02])

        updated = service.calculate_control_limits(chart.id)
        assert updated is not None
        assert updated.control_limits.ucl > updated.control_limits.cl
        assert updated.control_limits.lcl < updated.control_limits.cl

    def test_out_of_control_rule1(self) -> None:
        service = SPCDomainService()
        chart = service.create_control_chart(
            "t-001", "p-001", ChartType.X_BAR_R, "CNC", "Dia",
            SpecificationLimits(usl=10.05, lsl=9.95, target=10.0),
        )
        chart.set_control_limits(ucl=10.05, lcl=9.95, cl=10.0)

        m = service.add_measurement(chart.id, 1, [10.2, 10.2, 10.2, 10.2, 10.2])
        assert m is not None
        assert m.is_out_of_control is True
        assert 1 in m.violation_rules

    def test_out_of_control_rule2(self) -> None:
        service = SPCDomainService()
        chart = service.create_control_chart(
            "t-001", "p-001", ChartType.X_BAR_R, "CNC", "Dia",
            SpecificationLimits(usl=10.05, lsl=9.95, target=10.0),
        )
        chart.set_control_limits(ucl=10.05, lcl=9.95, cl=10.0)

        for i in range(8):
            service.add_measurement(chart.id, i + 1, [10.01, 10.02, 10.01, 10.02, 10.01])

        m = service.add_measurement(chart.id, 9, [10.01, 10.02, 10.01, 10.02, 10.01])
        assert m is not None
        assert 2 in m.violation_rules

    def test_out_of_control_rule3(self) -> None:
        service = SPCDomainService()
        chart = service.create_control_chart(
            "t-001", "p-001", ChartType.X_BAR_R, "CNC", "Dia",
            SpecificationLimits(usl=10.05, lsl=9.95, target=10.0),
        )
        chart.set_control_limits(ucl=10.05, lcl=9.95, cl=10.0)

        for i in range(5):
            base = 9.97 + i * 0.005
            service.add_measurement(chart.id, i + 1, [base, base + 0.001, base + 0.002, base - 0.001, base + 0.003])

        m = service.add_measurement(chart.id, 6, [10.005, 10.006, 10.007, 10.004, 10.008])
        assert m is not None
        assert 3 in m.violation_rules

    def test_in_control_measurement(self) -> None:
        service = SPCDomainService()
        chart = service.create_control_chart(
            "t-001", "p-001", ChartType.X_BAR_R, "CNC", "Dia",
            SpecificationLimits(usl=10.05, lsl=9.95, target=10.0),
        )
        chart.set_control_limits(ucl=10.05, lcl=9.95, cl=10.0)

        m = service.add_measurement(chart.id, 1, [10.0, 10.01, 9.99, 10.0, 10.02])
        assert m is not None
        assert m.is_out_of_control is False

    def test_calculate_process_capability(self) -> None:
        service = SPCDomainService()
        chart = service.create_control_chart(
            "t-001", "p-001", ChartType.X_BAR_R, "CNC", "Dia",
            SpecificationLimits(usl=10.05, lsl=9.95, target=10.0),
            sample_size=5,
        )

        for i in range(10):
            service.add_measurement(chart.id, i + 1, [10.0, 10.01, 9.99, 10.0, 10.02])

        capability = service.calculate_process_capability(chart.id)
        assert capability is not None
        assert capability.cp > 0
        assert capability.cpk > 0
        assert capability.pp > 0
        assert capability.ppk > 0

    def test_generate_spc_report(self) -> None:
        service = SPCDomainService()
        chart = service.create_control_chart(
            "t-001", "p-001", ChartType.X_BAR_R, "CNC", "Dia",
            SpecificationLimits(usl=10.05, lsl=9.95, target=10.0),
        )

        for i in range(5):
            service.add_measurement(chart.id, i + 1, [10.0, 10.01, 9.99, 10.0, 10.02])

        report = service.generate_spc_report(chart.id)
        assert report is not None
        assert report["total_samples"] == 5
        assert "process_capability" in report

    def test_list_charts(self) -> None:
        service = SPCDomainService()
        service.create_control_chart("t-001", "p-001", ChartType.X_BAR_R, "CNC", "Dia",
                                      SpecificationLimits(usl=10.05, lsl=9.95, target=10.0))
        service.create_control_chart("t-001", "p-002", ChartType.X_BAR_R, "Weld", "Strength",
                                      SpecificationLimits(usl=500, lsl=400, target=450))
        assert len(service.list_charts()) == 2
        assert len(service.list_charts(project_id="p-001")) == 1

    def test_get_chart_not_found(self) -> None:
        service = SPCDomainService()
        assert service.get_chart("nonexistent") is None