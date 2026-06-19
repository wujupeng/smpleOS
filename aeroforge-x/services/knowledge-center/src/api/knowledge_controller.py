from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from ..domain.services.knowledge_graph_service import KnowledgeGraphService
from ..domain.services.decision_support_service import (
    DecisionSupportService,
    IntelligentRecommendationService,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])
_kg_service = KnowledgeGraphService()
_rec_service = IntelligentRecommendationService()
_decision_service = DecisionSupportService()


class IngestRequest(BaseModel):
    tenant_id: str


class QueryRequest(BaseModel):
    tenant_id: str
    query: str = ""
    entity_type: str | None = None


class RecommendDesignRequest(BaseModel):
    tenant_id: str
    project_id: str
    design_context: dict[str, Any] | None = None


class RecommendMaterialRequest(BaseModel):
    tenant_id: str
    project_id: str
    requirements: dict[str, Any] | None = None


class RecommendProcessRequest(BaseModel):
    tenant_id: str
    project_id: str
    material: str = "Ti-6Al-4V"


class RecommendFailurePreventionRequest(BaseModel):
    tenant_id: str
    project_id: str
    component_type: str = "forged_part"


class DesignDecisionRequest(BaseModel):
    tenant_id: str
    project_id: str
    alternatives: list[dict[str, Any]] | None = None


class MakeOrBuyRequest(BaseModel):
    tenant_id: str
    project_id: str
    component: str = "forged_billet"


class SupplierSelectionRequest(BaseModel):
    tenant_id: str
    project_id: str
    material: str = "titanium_alloy"


# --- Knowledge Graph APIs ---

@router.post("/ingest/regulation")
async def ingest_regulation(req: IngestRequest):
    entities = _kg_service.ingest_regulation_knowledge(req.tenant_id)
    return {"data": {"ingested_count": len(entities), "entities": [e.to_dict() for e in entities]}}


@router.post("/ingest/material")
async def ingest_material(req: IngestRequest):
    entities = _kg_service.ingest_material_knowledge(req.tenant_id)
    return {"data": {"ingested_count": len(entities), "entities": [e.to_dict() for e in entities]}}


@router.post("/ingest/process")
async def ingest_process(req: IngestRequest):
    entities = _kg_service.ingest_process_knowledge(req.tenant_id)
    return {"data": {"ingested_count": len(entities), "entities": [e.to_dict() for e in entities]}}


@router.post("/ingest/failure-mode")
async def ingest_failure_mode(req: IngestRequest):
    entities = _kg_service.ingest_failure_mode_knowledge(req.tenant_id)
    return {"data": {"ingested_count": len(entities), "entities": [e.to_dict() for e in entities]}}


@router.post("/graph/build")
async def build_graph(req: IngestRequest):
    result = _kg_service.build_knowledge_graph(req.tenant_id)
    return {"data": result}


@router.post("/graph/query")
async def query_graph(req: QueryRequest):
    results = _kg_service.query_knowledge_graph(
        tenant_id=req.tenant_id,
        query=req.query,
        entity_type=req.entity_type,
    )
    return {"data": results}


# --- Recommendation APIs ---

@router.post("/recommend/design-parameters")
async def recommend_design_params(req: RecommendDesignRequest):
    result = _rec_service.recommend_design_parameters(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        design_context=req.design_context,
    )
    return {"data": result}


@router.post("/recommend/material")
async def recommend_material(req: RecommendMaterialRequest):
    result = _rec_service.recommend_material_selection(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        requirements=req.requirements,
    )
    return {"data": result}


@router.post("/recommend/process")
async def recommend_process(req: RecommendProcessRequest):
    result = _rec_service.recommend_process_parameters(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        material=req.material,
    )
    return {"data": result}


@router.post("/recommend/failure-prevention")
async def recommend_failure_prevention(req: RecommendFailurePreventionRequest):
    result = _rec_service.recommend_failure_prevention(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        component_type=req.component_type,
    )
    return {"data": result}


# --- Decision Support APIs ---

@router.post("/decision/design")
async def design_decision(req: DesignDecisionRequest):
    result = _decision_service.support_design_decision(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        alternatives=req.alternatives,
    )
    return {"data": result}


@router.post("/decision/make-or-buy")
async def make_or_buy_decision(req: MakeOrBuyRequest):
    result = _decision_service.support_make_or_buy_decision(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        component=req.component,
    )
    return {"data": result}


@router.post("/decision/supplier-selection")
async def supplier_selection_decision(req: SupplierSelectionRequest):
    result = _decision_service.support_supplier_selection_decision(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        material=req.material,
    )
    return {"data": result}