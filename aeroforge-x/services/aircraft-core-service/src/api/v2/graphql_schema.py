from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any

from src.domain.services.object_query_service import ObjectQueryService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class GraphQLQuery(BaseModel):
    query: str
    variables: dict[str, Any] | None = None


@router.post("/graphql")
async def graphql_endpoint(req: GraphQLQuery):
    pool = await get_pg_pool()
    query = req.query.strip()
    variables = req.variables or {}

    if "aircraftObject" in query and "id" in query:
        object_id = variables.get("id", "")
        result = await ObjectQueryService.query_unified_view(object_id, pool)
        if result is None:
            return {"data": {"aircraftObject": None}}
        return {"data": {"aircraftObject": result}}

    if "aircraftObjectsByProperty" in query:
        property_type = variables.get("propertyType")
        value_range = variables.get("valueRange")
        result = await ObjectQueryService.query_by_property(
            property_type=property_type, value_range=value_range, pool=pool,
        )
        return {"data": {"aircraftObjectsByProperty": result}}

    if "relationshipTraversal" in query:
        object_id = variables.get("objectId", "")
        depth = variables.get("depth", 3)
        result = await ObjectQueryService.traverse_relationships(object_id, depth=depth, pool=pool)
        return {"data": {"relationshipTraversal": result}}

    if "changeImpactAnalysis" in query:
        object_id = variables.get("objectId", "")
        max_depth = variables.get("maxDepth", 5)
        result = await ObjectQueryService.analyze_change_impact(object_id, max_depth=max_depth, pool=pool)
        return {"data": {"changeImpactAnalysis": result}}

    return {"data": None, "errors": [{"message": "Unknown query"}]}