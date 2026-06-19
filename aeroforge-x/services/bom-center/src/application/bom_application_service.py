from __future__ import annotations

from typing import Any

from ..domain.entities.bom_item import EBOM
from ..domain.services.ebom_engine import EBOMEngine
from ..infrastructure.neo4j.bom_graph_repository import BOMGraphRepository


class BomApplicationService:
    def __init__(self, graph_repo: BOMGraphRepository) -> None:
        self._graph_repo = graph_repo
        self._ebom_engine = EBOMEngine()

    async def generate_ebom(self, spec_id: str, model_data: dict[str, Any]) -> dict[str, Any]:
        ebom = self._ebom_engine.generate_from_model(spec_id, model_data)
        ebom.publish()
        if ebom.root_item:
            await self._graph_repo.save_bom_tree(ebom.id, ebom.root_item.to_dict())
        return {
            "ebom": ebom.to_dict(),
            "events": [e.to_dict() for e in ebom.domain_events],
        }

    async def get_ebom(self, ebom_id: str) -> dict[str, Any] | None:
        return await self._graph_repo.query_bom_tree(ebom_id)