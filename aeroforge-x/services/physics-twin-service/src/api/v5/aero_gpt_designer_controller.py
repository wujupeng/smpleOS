from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.generative_design.aero_gpt_designer_service import (
    AeroGPTDesignerService,
    RequirementParserService,
)

router = APIRouter(prefix="/api/v5/physics-twin", tags=["AeroGPT Designer v5"])

_req_service = RequirementParserService()
_service = AeroGPTDesignerService()


@router.post("/design-suggestions")
async def suggest_designs(body: dict[str, Any]):
    requirement_id = body.get("requirement_id", "")
    req = _req_service.get_requirement_version(requirement_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Requirement not found")

    max_suggestions = body.get("max_suggestions", 5)
    suggestions = _service.suggest_designs(requirement=req, max_suggestions=max_suggestions)

    return {
        "requirement_id": requirement_id,
        "suggestions": [
            {
                "suggestion_id": s.suggestion_id,
                "compliance_score": s.compliance_score,
                "satisfied_constraints": s.satisfied_constraints,
                "violated_constraints": s.violated_constraints,
                "reasoning": s.reasoning,
                "source_designs": s.source_designs,
                "configuration": s.configuration,
            }
            for s in suggestions
        ],
    }


@router.post("/design-suggestions/evaluate")
async def evaluate_alternatives(body: dict[str, Any]):
    suggestion_ids = body.get("suggestion_ids", [])
    all_suggestions = _service._suggestions
    suggestions = [all_suggestions[sid] for sid in suggestion_ids if sid in all_suggestions]

    if not suggestions:
        raise HTTPException(status_code=404, detail="No valid suggestions found")

    evaluated = _service.evaluate_alternatives(suggestions)
    return {
        "evaluated": [
            {
                "suggestion_id": s.suggestion_id,
                "compliance_score": s.compliance_score,
                "satisfied_constraints": s.satisfied_constraints,
                "violated_constraints": s.violated_constraints,
            }
            for s in evaluated
        ],
    }


@router.get("/design-suggestions/{suggestion_id}/explanation")
async def explain_suggestion(suggestion_id: str):
    result = _service.explain_suggestion(suggestion_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return {
        "suggestion_id": result.suggestion_id,
        "satisfied_constraints": result.satisfied_constraints,
        "violated_constraints": result.violated_constraints,
        "reasoning": result.reasoning,
        "source_design_references": result.source_design_references,
    }


@router.post("/design-suggestions/{suggestion_id}/instantiate")
async def instantiate_design(suggestion_id: str):
    config = _service.instantiate_design(suggestion_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return config.to_dict()


@router.put("/aircraft-configurations/{configuration_id}/iterate")
async def iterate_design(configuration_id: str, body: dict[str, Any]):
    modifications = body.get("modifications", {})
    config = _service.iterate_design(configuration_id=configuration_id, modifications=modifications)
    if config is None:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config.to_dict()