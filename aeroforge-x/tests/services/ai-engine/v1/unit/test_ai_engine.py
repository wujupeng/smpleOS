import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..'))

import pytest

from services.ai_engine.src.domain.services.aerogpt_designer import AeroGPTDesigner
from services.ai_engine.src.domain.entities.ai_proposal import ProposalStatus


class TestAeroGPTDesigner:
    @pytest.fixture
    def designer(self):
        return AeroGPTDesigner()

    def test_parse_natural_language_basic(self, designer):
        parsed = designer.parse_natural_language(
            "Design a narrow-body aircraft with wingspan of 35.8m, fuselage length of 40m, mtow of 78000kg, cruise speed of 450kts"
        )
        assert parsed["aircraft_type"] == "narrow_body"
        assert parsed["parameters"]["wingspan_m"] == 35.8
        assert parsed["parameters"]["fuselage_length_m"] == 40.0
        assert parsed["parameters"]["mtow_kg"] == 78000.0
        assert parsed["parameters"]["cruise_speed_kts"] == 450.0

    def test_parse_natural_language_missing_fields(self, designer):
        parsed = designer.parse_natural_language("Design a small aircraft")
        assert len(parsed["missing_fields"]) > 0

    def test_parse_natural_language_ambiguous(self, designer):
        parsed = designer.parse_natural_language(
            "Design an aircraft with approximately 35m wingspan"
        )
        assert "approximate_values" in parsed["ambiguities"]

    def test_generate_aircraft_spec(self, designer):
        proposal = designer.generate_aircraft_spec(
            "Design a narrow-body aircraft with wingspan of 35.8m, fuselage length of 40m, mtow of 78000kg, cruise speed of 450kts",
            project_id="PROJ-001",
        )
        assert proposal.status == ProposalStatus.PENDING_REVIEW
        assert proposal.parsed_spec["wingspan_m"] == 35.8
        assert proposal.feasibility_report.is_feasible is True

    def test_generate_spec_with_violations(self, designer):
        proposal = designer.generate_aircraft_spec(
            "Design an aircraft with wingspan of 5m, mtow of 100kg"
        )
        assert len(proposal.feasibility_report.design_rule_violations) > 0
        assert proposal.feasibility_report.is_feasible is False
        assert len(proposal.risk_markers) > 0

    def test_generate_spec_with_clarification_questions(self, designer):
        proposal = designer.generate_aircraft_spec("Design a small aircraft")
        assert len(proposal.clarification_questions) > 0

    @pytest.mark.asyncio
    async def test_generate_initial_model(self, designer):
        proposal = designer.generate_aircraft_spec(
            "Design an aircraft with wingspan of 35.8m, fuselage length of 40m, mtow of 78000kg"
        )
        model = await designer.generate_initial_model(proposal.id)
        assert model["model_type"] == "parametric_aircraft"
        assert model["geometry"]["wingspan_m"] == 35.8
        assert proposal.generated_model_ref == model["model_id"]

    def test_get_proposal(self, designer):
        proposal = designer.generate_aircraft_spec("Design an aircraft with wingspan of 35.8m")
        retrieved = designer.get_proposal(proposal.id)
        assert retrieved is not None
        assert retrieved.id == proposal.id

    def test_list_proposals(self, designer):
        designer.generate_aircraft_spec("Design aircraft A with wingspan of 35.8m")
        designer.generate_aircraft_spec("Design aircraft B with wingspan of 64.8m")
        all_proposals = designer.list_proposals()
        assert len(all_proposals) >= 2
        pending = designer.list_proposals(ProposalStatus.PENDING_REVIEW)
        assert len(pending) >= 2


class TestAeroGPTEngineer:
    @pytest.fixture
    def engineer(self):
        from services.ai_engine.src.domain.services.aerogpt_engineer import AeroGPTEngineer
        return AeroGPTEngineer()

    def test_generate_structure(self, engineer):
        from services.ai_engine.src.domain.services.aerogpt_engineer import AeroGPTEngineer
        result = engineer.generate_structure("PROP-001", {
            "wingspan_m": 35.8,
            "fuselage_length_m": 40.0,
            "mtow_kg": 78000,
        })
        assert len(result.components) > 0
        assert result.status == "generated"
        spar = [c for c in result.components if c.component_type == "wing_spar"]
        assert len(spar) == 1

    def test_generate_structure_frozen_baseline(self, engineer):
        engineer.freeze_baseline("PROP-FROZEN")
        result = engineer.generate_structure("PROP-FROZEN", {"wingspan_m": 35.8})
        assert result.status == "blocked"
        assert len(result.baseline_frozen_violations) > 0

    def test_optimize_structure(self, engineer):
        result = engineer.generate_structure("PROP-OPT", {"wingspan_m": 35.8, "mtow_kg": 78000})
        fea_results = {f"{c.component_id}_max_stress": 200.0 for c in result.components}
        optimized = engineer.optimize_structure(result.result_id, fea_results)
        assert optimized.status == "optimized"


class TestAeroGPTManufacturing:
    @pytest.fixture
    def mfg(self):
        from services.ai_engine.src.domain.services.aerogpt_manufacturing import AeroGPTManufacturing
        return AeroGPTManufacturing()

    def test_generate_process_route_composite(self, mfg):
        route = mfg.generate_process_route("wing_spar", "composite_cfrp", {})
        assert len(route.steps) > 0
        assert route.total_estimated_hours > 0

    def test_generate_process_route_metal(self, mfg):
        route = mfg.generate_process_route("wing_spar", "aluminum_7075", {})
        assert len(route.steps) > 0

    def test_generate_traveler_template(self, mfg):
        route = mfg.generate_process_route("wing_rib", "aluminum_7075", {})
        template = mfg.generate_traveler_template("wing_rib", route)
        assert len(template.fields) > 0
        prefilled = [f for f in template.fields if f.get("prefilled")]
        assert len(prefilled) > 0

    def test_generate_ndt_plan_composite(self, mfg):
        plan = mfg.generate_ndt_plan("wing_spar", "composite_cfrp", ["bonded_joints"])
        assert len(plan.inspections) > 0
        critical = [i for i in plan.inspections if i["critical"]]
        assert len(critical) > 0

    def test_generate_ndt_plan_metal(self, mfg):
        plan = mfg.generate_ndt_plan("fuselage_frame", "aluminum_7075", ["welds"])
        assert len(plan.inspections) > 0


class TestAeroGPTCertification:
    @pytest.fixture
    def cert(self):
        from services.ai_engine.src.domain.services.aerogpt_certification import AeroGPTCertification
        return AeroGPTCertification()

    def test_generate_compliance_matrix(self, cert):
        matrix = cert.generate_compliance_matrix("narrow_body", "FAR-25")
        assert len(matrix.items) > 0
        assert matrix.coverage_percentage == 0.0

    def test_generate_compliance_matrix_with_evidence(self, cert):
        evidence = {"25.301": "RPT-STR-001", "25.303": "RPT-STR-002"}
        matrix = cert.generate_compliance_matrix("narrow_body", "FAR-25", evidence)
        compliant = [i for i in matrix.items if i.compliance_status == "compliant"]
        assert len(compliant) == 2
        assert matrix.coverage_percentage > 0

    def test_generate_compliance_matrix_gaps(self, cert):
        matrix = cert.generate_compliance_matrix("narrow_body")
        gaps = [i for i in matrix.items if i.evidence_gap]
        assert len(gaps) > 0
        assert all(i.suggested_evidence_source is not None for i in gaps)

    def test_generate_certification_plan(self, cert):
        matrix = cert.generate_compliance_matrix("narrow_body")
        plan = cert.generate_certification_plan("narrow_body", matrix.matrix_id)
        assert len(plan.phases) == 5
        assert plan.estimated_duration_months > 0

    def test_generate_evidence_cross_reference(self, cert):
        matrix = cert.generate_compliance_matrix("narrow_body")
        ref = cert.generate_evidence_cross_reference(matrix.matrix_id, {"25.301": ["RPT-001"]})
        assert len(ref.cross_references) > 0


class TestAeroGPTTestPilot:
    @pytest.fixture
    def tp(self):
        from services.ai_engine.src.domain.services.aerogpt_testpilot import AeroGPTTestPilot
        return AeroGPTTestPilot()

    def test_generate_flight_test_plan(self, tp):
        plan = tp.generate_flight_test_plan("narrow_body")
        assert len(plan.sorties) > 0
        assert sum(len(s.test_points) for s in plan.sorties) > 0

    def test_flight_test_plan_with_cert_coverage(self, tp):
        plan = tp.generate_flight_test_plan(
            "narrow_body",
            certification_requirements=["25.201", "25.203", "25.337", "25.629"],
        )
        assert "coverage_percentage" in plan.certification_coverage
        assert plan.certification_coverage["total_requirements"] == 4

    def test_safety_boundaries_generated(self, tp):
        plan = tp.generate_flight_test_plan("narrow_body")
        for sortie in plan.sorties:
            for tp_item in sortie.test_points:
                if tp_item.conditions:
                    assert len(tp_item.safety_boundaries) > 0 or not tp_item.within_flight_envelope

    def test_emergency_procedures(self, tp):
        plan = tp.generate_flight_test_plan("narrow_body")
        for sortie in plan.sorties:
            for tp_item in sortie.test_points:
                assert len(tp_item.emergency_procedures) > 0


class TestMultiObjectiveOptimization:
    @pytest.fixture
    def optimizer(self):
        from services.ai_engine.src.domain.services.multi_objective_optimization import MultiObjectiveOptimization
        return MultiObjectiveOptimization()

    def test_optimize(self, optimizer):
        result = optimizer.optimize(
            task_id="TEST-OPT-001",
            objectives=[
                {"name": "weight", "direction": "minimize", "weight": 0.4},
                {"name": "cost", "direction": "minimize", "weight": 0.3},
                {"name": "lift_drag_ratio", "direction": "maximize", "weight": 0.3},
            ],
            constraints=[
                {"name": "min_wingspan", "type": "greater_than", "bound": 20.0, "variable": "wingspan_m"},
            ],
            design_variables={
                "wingspan_m": {"min": 20.0, "max": 65.0},
                "fuselage_length_m": {"min": 25.0, "max": 70.0},
                "mtow_kg": {"min": 30000.0, "max": 300000.0},
            },
            max_iterations=10,
        )
        assert result.iteration_count == 10
        assert len(result.pareto_front) > 0

    def test_optimize_frozen_baseline(self, optimizer):
        optimizer.freeze_baseline("FROZEN-001")
        result = optimizer.optimize("FROZEN-001", [{"name": "weight", "direction": "minimize"}], [], {"x": {"min": 0, "max": 10}})
        assert result.baseline_frozen_violation is True

    def test_best_compromise_found(self, optimizer):
        result = optimizer.optimize(
            "TEST-COMP-001",
            [{"name": "weight", "direction": "minimize"}, {"name": "cost", "direction": "minimize"}],
            [],
            {"wingspan_m": {"min": 20, "max": 65}, "mtow_kg": {"min": 30000, "max": 300000}},
            max_iterations=10,
        )
        assert result.best_compromise is not None


class TestTopologyOptimization:
    @pytest.fixture
    def topo(self):
        from services.ai_engine.src.domain.services.topology_optimization import TopologyOptimization
        return TopologyOptimization()

    def test_optimize_topology(self, topo):
        result = topo.optimize_topology(
            component_type="wing_spar",
            load_conditions={"loads": [{"type": "bending", "magnitude": 150.0}]},
            material_constraints={"yield_stress_mpa": 600.0, "density_kg_m3": 1600.0},
            volume_fraction=0.3,
            max_iterations=10,
        )
        assert result.iteration_count > 0
        assert result.weight_reduction_percentage >= 0
        assert result.model_ref is not None

    def test_optimize_topology_stress(self, topo):
        result = topo.optimize_topology(
            "wing_rib",
            {"loads": [{"type": "compression", "magnitude": 50.0}]},
            {"yield_stress_mpa": 400.0, "density_kg_m3": 2700.0},
            max_iterations=10,
        )
        assert "max_stress_mpa" in result.stress_distribution
        assert "safety_factor" in result.stress_distribution