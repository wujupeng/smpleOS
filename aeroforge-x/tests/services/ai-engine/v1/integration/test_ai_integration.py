import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

import pytest

from services.ai_engine.src.domain.services.aerogpt_designer import AeroGPTDesigner
from services.ai_engine.src.domain.entities.ai_proposal import ProposalStatus


class TestDesignerEngineerManufacturingChain:
    @pytest.fixture
    def setup(self):
        from services.ai_engine.src.domain.services.aerogpt_engineer import AeroGPTEngineer
        from services.ai_engine.src.domain.services.aerogpt_manufacturing import AeroGPTManufacturing
        designer = AeroGPTDesigner()
        engineer = AeroGPTEngineer()
        manufacturing = AeroGPTManufacturing()
        return designer, engineer, manufacturing

    @pytest.mark.asyncio
    async def test_full_design_to_manufacturing_chain(self, setup):
        designer, engineer, manufacturing = setup

        proposal = designer.generate_aircraft_spec(
            "Design a narrow-body aircraft with wingspan of 35.8m, fuselage length of 40m, mtow of 78000kg, cruise speed of 450kts",
            project_id="CHAIN-001",
        )
        assert proposal.status == ProposalStatus.PENDING_REVIEW
        proposal.confirm()
        assert proposal.status == ProposalStatus.CONFIRMED

        model = await designer.generate_initial_model(proposal.id)
        assert model["model_type"] == "parametric_aircraft"

        structure = engineer.generate_structure(proposal.id, proposal.parsed_spec)
        assert len(structure.components) > 0
        assert structure.status == "generated"

        for component in structure.components:
            route = manufacturing.generate_process_route(component.component_type, component.material, component.parameters)
            assert len(route.steps) > 0

            template = manufacturing.generate_traveler_template(component.component_type, route)
            assert len(template.fields) > 0

            ndt = manufacturing.generate_ndt_plan(component.component_type, component.material)
            assert len(ndt.inspections) > 0


class TestCertificationTestPilotChain:
    @pytest.fixture
    def setup(self):
        from services.ai_engine.src.domain.services.aerogpt_certification import AeroGPTCertification
        from services.ai_engine.src.domain.services.aerogpt_testpilot import AeroGPTTestPilot
        cert = AeroGPTCertification()
        testpilot = AeroGPTTestPilot()
        return cert, testpilot

    def test_certification_to_test_plan(self, setup):
        cert, testpilot = setup

        matrix = cert.generate_compliance_matrix("narrow_body", "FAR-25")
        assert len(matrix.items) > 0

        plan = cert.generate_certification_plan("narrow_body", matrix.matrix_id)
        assert len(plan.phases) == 5

        cert_reqs = [item.section for item in matrix.items if item.evidence_gap][:10]
        flight_plan = testpilot.generate_flight_test_plan("narrow_body", cert_reqs)
        assert len(flight_plan.sorties) > 0

        if flight_plan.uncovered_requirements:
            assert len(flight_plan.uncovered_requirements) < len(cert_reqs)


class TestProposalReviewBaselineProtection:
    @pytest.fixture
    def setup(self):
        from services.ai_engine.src.domain.services.aerogpt_engineer import AeroGPTEngineer
        from services.ai_engine.src.domain.services.multi_objective_optimization import MultiObjectiveOptimization
        designer = AeroGPTDesigner()
        engineer = AeroGPTEngineer()
        optimizer = MultiObjectiveOptimization()
        return designer, engineer, optimizer

    def test_proposal_confirm_reject_flow(self, setup):
        designer, _, _ = setup
        proposal = designer.generate_aircraft_spec(
            "Design an aircraft with wingspan of 35.8m, fuselage length of 40m, mtow of 78000kg"
        )
        assert proposal.status == ProposalStatus.PENDING_REVIEW

        proposal.confirm()
        assert proposal.status == ProposalStatus.CONFIRMED

    def test_proposal_reject(self, setup):
        designer, _, _ = setup
        proposal = designer.generate_aircraft_spec("Design an aircraft with wingspan of 35.8m")
        proposal.reject("Parameters need revision")
        assert proposal.status == ProposalStatus.REJECTED

    def test_frozen_baseline_blocks_engineer(self, setup):
        _, engineer, _ = setup
        engineer.freeze_baseline("FROZEN-PROP")
        result = engineer.generate_structure("FROZEN-PROP", {"wingspan_m": 35.8})
        assert result.status == "blocked"
        assert len(result.baseline_frozen_violations) > 0

    def test_frozen_baseline_blocks_optimizer(self, setup):
        _, _, optimizer = setup
        optimizer.freeze_baseline("FROZEN-OPT")
        result = optimizer.optimize(
            "FROZEN-OPT",
            [{"name": "weight", "direction": "minimize"}],
            [],
            {"x": {"min": 0, "max": 10}},
        )
        assert result.baseline_frozen_violation is True