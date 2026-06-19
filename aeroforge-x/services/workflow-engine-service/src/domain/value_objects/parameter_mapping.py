from __future__ import annotations

from pydantic import BaseModel

from src.domain.enums import ConnectionType


class ParameterMapping(BaseModel):
    mapping_id: str
    source_node_id: str
    source_param_name: str
    target_node_id: str
    target_param_name: str
    transform_expression: str = ""