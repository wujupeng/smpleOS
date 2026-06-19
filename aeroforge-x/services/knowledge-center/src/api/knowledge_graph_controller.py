from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any

from ..domain.services.knowledge_graph_service import KnowledgeGraphService
from ..domain.value_objects.node_type import NodeType
from ..domain.value_objects.link_type import LinkType

router = APIRouter(prefix="/api/v1/knowledge-graph", tags=["Knowledge Graph"])

_service = KnowledgeGraphService()


class CreateGraphRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    created_by: str | None = None


class CreateNodeRequest(BaseModel):
    graph_id: str
    node_type: str
    name: str = Field(..., min_length=1, max_length=512)
    properties: dict[str, Any] = {}
    tags: list[str] = []
    confidence: float = Field(default=1.0, ge=0, le=1)
    source: str = "manual"
    source_ref: str | None = None
    created_by: str | None = None


class UpdateNodeRequest(BaseModel):
    name: str | None = None
    properties: dict[str, Any] | None = None
    tags: list[str] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class CreateLinkRequest(BaseModel):
    graph_id: str
    source_node_id: str
    target_node_id: str
    link_type: str
    weight: float = Field(default=1.0, ge=0, le=1)
    confidence: float = Field(default=1.0, ge=0, le=1)
    bidirectional: bool = False
    properties: dict[str, Any] = {}
    created_by: str | None = None


class BatchCreateNodesRequest(BaseModel):
    graph_id: str
    nodes: list[CreateNodeRequest]


class BatchCreateLinksRequest(BaseModel):
    graph_id: str
    links: list[CreateLinkRequest]


@router.post("/graphs")
async def create_graph(req: CreateGraphRequest):
    graph = _service.create_graph(name=req.name, description=req.description, created_by=req.created_by)
    return {"graph_id": graph.graph_id, "name": graph.name, "version": graph.version}


@router.get("/graphs/{graph_id}")
async def get_graph(graph_id: str):
    graph = _service.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    return {
        "graph_id": graph.graph_id,
        "name": graph.name,
        "version": graph.version,
        "status": graph.status,
        "node_count": graph.node_count,
        "link_count": graph.link_count,
    }


@router.post("/nodes")
async def create_node(req: CreateNodeRequest):
    try:
        node = _service.create_node(
            graph_id=req.graph_id,
            node_type=req.node_type,
            name=req.name,
            properties=req.properties,
            tags=req.tags,
            confidence=req.confidence,
            source=req.source,
            source_ref=req.source_ref,
            created_by=req.created_by,
        )
        return {"node_id": node.node_id, "node_type": node.node_type, "name": node.name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/nodes/{node_id}")
async def get_node(node_id: str, graph_id: str):
    graph = _service.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    node = graph.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return {
        "node_id": node.node_id,
        "node_type": node.node_type,
        "name": node.name,
        "properties": node.properties,
        "tags": node.tags,
        "confidence": node.confidence,
        "source": node.source,
        "version": node.version,
    }


@router.put("/nodes/{node_id}")
async def update_node(node_id: str, graph_id: str, req: UpdateNodeRequest):
    try:
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        node = _service.update_node(graph_id, node_id, **updates)
        return {"node_id": node.node_id, "version": node.version}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/nodes/{node_id}")
async def delete_node(node_id: str, graph_id: str):
    try:
        _service.delete_node(graph_id, node_id)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/nodes")
async def search_nodes(graph_id: str, node_type: str | None = None, skip: int = 0, limit: int = 50):
    graph = _service.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    nodes = graph.get_all_nodes()
    if node_type:
        nodes = [n for n in nodes if n.node_type == node_type]
    return {
        "nodes": [
            {"node_id": n.node_id, "node_type": n.node_type, "name": n.name, "confidence": n.confidence}
            for n in nodes[skip : skip + limit]
        ],
        "total": len(nodes),
    }


@router.post("/nodes/batch")
async def batch_create_nodes(req: BatchCreateNodesRequest):
    try:
        nodes_data = [n.model_dump() for n in req.nodes]
        for nd in nodes_data:
            nd["graph_id"] = req.graph_id
        nodes = _service.batch_create_nodes(req.graph_id, nodes_data)
        return {"created": len(nodes), "node_ids": [n.node_id for n in nodes]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/links")
async def create_link(req: CreateLinkRequest):
    try:
        link = _service.create_link(
            graph_id=req.graph_id,
            source_node_id=req.source_node_id,
            target_node_id=req.target_node_id,
            link_type=req.link_type,
            weight=req.weight,
            confidence=req.confidence,
            bidirectional=req.bidirectional,
            properties=req.properties,
            created_by=req.created_by,
        )
        return {"link_id": link.link_id, "link_type": link.link_type}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/links/{link_id}")
async def get_link(link_id: str, graph_id: str):
    graph = _service.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    link = graph.get_link(link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return {
        "link_id": link.link_id,
        "source_node_id": link.source_node_id,
        "target_node_id": link.target_node_id,
        "link_type": link.link_type,
        "weight": link.weight,
        "confidence": link.confidence,
        "bidirectional": link.bidirectional,
    }


@router.put("/links/{link_id}")
async def update_link(link_id: str, graph_id: str, req: dict):
    try:
        link = _service.update_link(graph_id, link_id, **req)
        return {"link_id": link.link_id, "version": link.version}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/links/{link_id}")
async def delete_link(link_id: str, graph_id: str):
    try:
        _service.delete_link(graph_id, link_id)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/links")
async def search_links(graph_id: str, link_type: str | None = None, skip: int = 0, limit: int = 50):
    graph = _service.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    links = graph.get_all_links()
    if link_type:
        links = [l for l in links if l.link_type == link_type]
    return {
        "links": [
            {"link_id": l.link_id, "source": l.source_node_id, "target": l.target_node_id, "type": l.link_type}
            for l in links[skip : skip + limit]
        ],
        "total": len(links),
    }


@router.post("/links/batch")
async def batch_create_links(req: BatchCreateLinksRequest):
    try:
        links_data = [l.model_dump() for l in req.links]
        for ld in links_data:
            ld["graph_id"] = req.graph_id
        links = _service.batch_create_links(req.graph_id, links_data)
        return {"created": len(links), "link_ids": [l.link_id for l in links]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))