from fastapi import APIRouter, HTTPException

from src.domain.services.aerogpt_designer import AeroGPTDesigner
from src.domain.services.aerogpt_engineer import AeroGPTEngineer
from src.domain.services.aerogpt_manufacturing import AeroGPTManufacturing
from src.domain.services.aerogpt_certification import AeroGPTCertification
from src.domain.services.aerogpt_testpilot import AeroGPTTestPilot
from src.domain.services.multi_objective_optimization import MultiObjectiveOptimization
from src.domain.services.topology_optimization import TopologyOptimization
from src.domain.entities.ai_proposal import ProposalStatus
from src.infrastructure.event_bus import event_bus

router = APIRouter()

_designer = AeroGPTDesigner(event_publisher=event_bus)
_engineer = AeroGPTEngineer(event_publisher=event_bus)
_manufacturing = AeroGPTManufacturing(event_publisher=event_bus)
_certification = AeroGPTCertification(event_publisher=event_bus)
_testpilot = AeroGPTTestPilot(event_publisher=event_bus)
_optimizer = MultiObjectiveOptimization(event_publisher=event_bus)
_topology = TopologyOptimization(event_publisher=event_bus)


@router.post("/ai/designer/generate-spec")
async def generate_spec(body: dict):
    description = body.get("description", "")
    project_id = body.get("project_id", "")
    created_by = body.get("created_by", "")
    if not description:
        raise HTTPException(status_code=400, detail="description is required")
    proposal = _designer.generate_aircraft_spec(description, project_id, created_by)
    return proposal.to_dict()


@router.post("/ai/designer/generate-model")
async def generate_model(body: dict):
    proposal_id = body.get("proposal_id", "")
    if not proposal_id:
        raise HTTPException(status_code=400, detail="proposal_id is required")
    try:
        model = await _designer.generate_initial_model(proposal_id)
        return model
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ai/engineer/generate-structure")
async def generate_structure(body: dict):
    proposal_id = body.get("proposal_id", "")
    spec = body.get("spec", {})
    if not proposal_id:
        raise HTTPException(status_code=400, detail="proposal_id is required")
    result = _engineer.generate_structure(proposal_id, spec)
    return result.to_dict()


@router.post("/ai/manufacturing/generate-process")
async def generate_process_route(body: dict):
    component_type = body.get("component_type", "")
    material = body.get("material", "aluminum_7075")
    dimensions = body.get("dimensions", {})
    if not component_type:
        raise HTTPException(status_code=400, detail="component_type is required")
    route = _manufacturing.generate_process_route(component_type, material, dimensions)
    result = route.to_dict()
    template = None
    ndt_plan = None
    if body.get("include_traveler", False):
        template = _manufacturing.generate_traveler_template(component_type, route)
        result["traveler_template"] = template.to_dict()
    if body.get("include_ndt", False):
        ndt_plan = _manufacturing.generate_ndt_plan(component_type, material)
        result["ndt_plan"] = ndt_plan.to_dict()
    return result


@router.post("/ai/certification/generate-compliance")
async def generate_compliance(body: dict):
    aircraft_type = body.get("aircraft_type", "")
    regulation = body.get("regulation", "FAR-25")
    existing_evidence = body.get("existing_evidence")
    if not aircraft_type:
        raise HTTPException(status_code=400, detail="aircraft_type is required")
    matrix = _certification.generate_compliance_matrix(aircraft_type, regulation, existing_evidence)
    result = matrix.to_dict()
    if body.get("include_plan", False):
        plan = _certification.generate_certification_plan(aircraft_type, matrix.matrix_id)
        result["certification_plan"] = plan.to_dict()
    return result


@router.post("/ai/testpilot/generate-test-plan")
async def generate_test_plan(body: dict):
    aircraft_type = body.get("aircraft_type", "")
    certification_requirements = body.get("certification_requirements")
    flight_envelope = body.get("flight_envelope")
    if not aircraft_type:
        raise HTTPException(status_code=400, detail="aircraft_type is required")
    plan = _testpilot.generate_flight_test_plan(aircraft_type, certification_requirements, flight_envelope)
    return plan.to_dict()


@router.post("/ai/optimization/multi-objective")
async def multi_objective_optimization(body: dict):
    task_id = body.get("task_id", "")
    objectives = body.get("objectives", [])
    constraints = body.get("constraints", [])
    design_variables = body.get("design_variables", {})
    max_iterations = body.get("max_iterations", 100)
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id is required")
    if not objectives or not design_variables:
        raise HTTPException(status_code=400, detail="objectives and design_variables are required")
    result = _optimizer.optimize(task_id, objectives, constraints, design_variables, max_iterations)
    return result.to_dict()


@router.post("/ai/optimization/topology")
async def topology_optimization(body: dict):
    component_type = body.get("component_type", "")
    load_conditions = body.get("load_conditions", {})
    material_constraints = body.get("material_constraints", {})
    volume_fraction = body.get("volume_fraction", 0.3)
    max_iterations = body.get("max_iterations", 50)
    if not component_type:
        raise HTTPException(status_code=400, detail="component_type is required")
    result = _topology.optimize_topology(component_type, load_conditions, material_constraints, volume_fraction, max_iterations)
    return result.to_dict()


@router.get("/ai/proposals/{proposal_id}")
async def get_proposal(proposal_id: str):
    proposal = _designer.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    return proposal.to_dict()


@router.post("/ai/proposals/{proposal_id}/review")
async def review_proposal(proposal_id: str, body: dict):
    proposal = _designer.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    decision = body.get("decision", "")
    if decision == "confirm":
        try:
            proposal.confirm()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif decision == "reject":
        reason = body.get("reason", "")
        proposal.reject(reason)
    else:
        raise HTTPException(status_code=400, detail="decision must be 'confirm' or 'reject'")
    return proposal.to_dict()


@router.get("/ai/proposals/{proposal_id}/progress")
async def get_proposal_progress(proposal_id: str):
    proposal = _designer.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    return {
        "proposal_id": proposal_id,
        "status": proposal.status.value,
        "feasibility_score": proposal.feasibility_report.overall_score,
        "has_model": bool(proposal.generated_model_ref),
        "clarification_questions_count": len(proposal.clarification_questions),
        "iteration_count": len(proposal.iteration_history),
    }