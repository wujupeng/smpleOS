import pytest

from services.ai_engine.src.domain.entities.ai_proposal import (
    AIProposal, ProposalStatus, FeasibilityReport, RiskMarker, RiskSeverity,
)
from services.ai_engine.src.domain.services.aerogpt_domain_service import AeroGPTDomainService


class TestAIProposalEntity:
    def test_create_proposal(self) -> None:
        proposal = AIProposal(project_id="p-001", natural_language_input="设计一架载重120kg的电动固定翼")
        assert proposal.status == ProposalStatus.PENDING_REVIEW

    def test_confirm_proposal(self) -> None:
        proposal = AIProposal(project_id="p-001")
        proposal.confirm()
        assert proposal.status == ProposalStatus.CONFIRMED
        assert len(proposal.domain_events) == 1

    def test_cannot_confirm_rejected(self) -> None:
        proposal = AIProposal(project_id="p-001", status=ProposalStatus.REJECTED)
        with pytest.raises(ValueError):
            proposal.confirm()

    def test_reject_proposal(self) -> None:
        proposal = AIProposal(project_id="p-001")
        proposal.reject("not feasible")
        assert proposal.status == ProposalStatus.REJECTED

    def test_add_iteration(self) -> None:
        proposal = AIProposal(project_id="p-001", parsed_spec={"payload_kg": 100})
        proposal.add_iteration("增加载荷", {"payload_kg": 150})
        assert proposal.status == ProposalStatus.ITERATING
        assert len(proposal.iteration_history) == 1
        assert proposal.parsed_spec["payload_kg"] == 150


class TestAeroGPTDomainService:
    def test_parse_natural_language_basic(self) -> None:
        service = AeroGPTDomainService()
        result = service.parse_natural_language("设计一架载重120kg、航程200km、时速120km的电动固定翼飞行器")
        spec = result["parsed_spec"]
        assert spec["payload_kg"] == 120
        assert spec["range_km"] == 200
        assert spec["cruise_speed_kmh"] == 120
        assert spec["power_type"] == "electric"
        assert spec["aircraft_type"] == "fixed_wing"

    def test_parse_natural_language_vtol(self) -> None:
        service = AeroGPTDomainService()
        result = service.parse_natural_language("设计一架载重200kg、航程50km的电动垂直起降飞行器")
        spec = result["parsed_spec"]
        assert spec["vtol"] is True
        assert spec["takeoff_distance_m"] == 0
        assert spec["aircraft_type"] == "evtol"

    def test_parse_missing_params_generates_questions(self) -> None:
        service = AeroGPTDomainService()
        result = service.parse_natural_language("设计一架飞行器")
        assert len(result["clarification_questions"]) >= 3

    def test_generate_initial_proposal(self) -> None:
        service = AeroGPTDomainService()
        proposal = service.generate_initial_proposal(
            project_id="p-001",
            tenant_id="t-001",
            natural_language_input="设计一架载重120kg、航程200km、时速120km的电动固定翼",
        )
        assert proposal.status == ProposalStatus.PENDING_REVIEW
        assert proposal.parsed_spec["payload_kg"] == 120
        assert len(proposal.domain_events) == 1

    def test_evaluate_feasibility_valid(self) -> None:
        service = AeroGPTDomainService()
        report = service.evaluate_feasibility({
            "payload_kg": 120, "range_km": 200, "cruise_speed_kmh": 120,
            "power_type": "electric", "takeoff_distance_m": 80,
        })
        assert report.is_feasible is True
        assert report.overall_score > 0

    def test_evaluate_feasibility_invalid_speed(self) -> None:
        service = AeroGPTDomainService()
        report = service.evaluate_feasibility({
            "payload_kg": 120, "range_km": 200, "cruise_speed_kmh": 500,
            "power_type": "electric",
        })
        assert len(report.design_rule_violations) > 0

    def test_iterate_with_feedback(self) -> None:
        service = AeroGPTDomainService()
        proposal = service.generate_initial_proposal(
            "p-001", "t-001", "设计一架载重120kg、航程200km、时速120km的电动固定翼",
        )
        updated = service.iterate_with_feedback(
            proposal.id, "增加载荷到150kg", {"payload_kg": 150},
        )
        assert updated is not None
        assert updated.status == ProposalStatus.ITERATING
        assert updated.parsed_spec["payload_kg"] == 150
        assert len(updated.iteration_history) == 1

    def test_confirm_proposal(self) -> None:
        service = AeroGPTDomainService()
        proposal = service.generate_initial_proposal("p-001", "t-001", "载重120kg航程200km电动固定翼")
        confirmed = service.confirm_proposal(proposal.id)
        assert confirmed.status == ProposalStatus.CONFIRMED

    def test_reject_proposal(self) -> None:
        service = AeroGPTDomainService()
        proposal = service.generate_initial_proposal("p-001", "t-001", "载重120kg航程200km电动固定翼")
        rejected = service.reject_proposal(proposal.id, "不可行")
        assert rejected.status == ProposalStatus.REJECTED

    def test_risk_markers_generated(self) -> None:
        service = AeroGPTDomainService()
        proposal = service.generate_initial_proposal(
            "p-001", "t-001", "设计一架载重120kg、航程600km、时速120km的电动固定翼",
        )
        assert len(proposal.risk_markers) > 0

    def test_list_proposals(self) -> None:
        service = AeroGPTDomainService()
        service.generate_initial_proposal("p-001", "t-001", "载重120kg航程200km电动固定翼")
        service.generate_initial_proposal("p-002", "t-001", "载重200kg航程50km电动eVTOL")
        assert len(service.list_proposals()) == 2
        assert len(service.list_proposals("p-001")) == 1