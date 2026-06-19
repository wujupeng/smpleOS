from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent
from aeroforge_common.utils.helpers import generate_code

logger = logging.getLogger(__name__)


class OperationType(str, Enum):
    ASSEMBLY = "assembly"
    MACHINING = "machining"
    INSPECTION = "inspection"
    INSTALLATION = "installation"
    TESTING = "testing"
    QUALITY_GATE = "quality_gate"


@dataclass
class Operation:
    operation_id: str
    operation_name: str
    operation_type: OperationType
    sequence: int
    station: str = ""
    equipment: str = ""
    estimated_hours: float = 0.0
    dependencies: list[str] = field(default_factory=list)
    is_quality_checkpoint: bool = False
    is_mandatory_gate: bool = False
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "operation_name": self.operation_name,
            "operation_type": self.operation_type.value,
            "sequence": self.sequence,
            "station": self.station,
            "equipment": self.equipment,
            "estimated_hours": self.estimated_hours,
            "dependencies": self.dependencies,
            "is_quality_checkpoint": self.is_quality_checkpoint,
            "is_mandatory_gate": self.is_mandatory_gate,
            "status": self.status,
        }


class ProcessRoute(AggregateRoot):
    def __init__(
        self,
        mbom_id: str = "",
        route_name: str = "",
        created_by: str = "",
    ) -> None:
        super().__init__()
        self.route_code: str = generate_code("AAF-PR")
        self.mbom_id = mbom_id
        self.route_name = route_name
        self.operations: list[Operation] = []
        self.status: str = "draft"
        self.total_estimated_hours: float = 0.0
        self.created_by = created_by
        self.created_at: datetime = datetime.now(timezone.utc)

    def add_operation(self, op: Operation) -> None:
        self.operations.append(op)
        self._recalculate_hours()

    def remove_operation(self, operation_id: str) -> bool:
        for i, op in enumerate(self.operations):
            if op.operation_id == operation_id:
                self.operations.pop(i)
                self._recalculate_hours()
                return True
        return False

    def reorder_operations(self, ordered_ids: list[str]) -> None:
        op_map = {op.operation_id: op for op in self.operations}
        reordered: list[Operation] = []
        for seq, oid in enumerate(ordered_ids, 1):
            if oid in op_map:
                op_map[oid].sequence = seq
                reordered.append(op_map[oid])
        self.operations = reordered

    def _recalculate_hours(self) -> None:
        self.total_estimated_hours = sum(op.estimated_hours for op in self.operations)

    def publish(self) -> None:
        if not self.operations:
            raise ValueError("Cannot publish empty process route")
        self.status = "published"
        self.add_domain_event(DomainEvent(
            event_type="process_route.published",
            aggregate_id=self.id,
            payload={
                "route_id": self.id,
                "route_code": self.route_code,
                "operation_count": len(self.operations),
                "total_estimated_hours": self.total_estimated_hours,
            },
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "route_code": self.route_code,
            "mbom_id": self.mbom_id,
            "route_name": self.route_name,
            "operations": [op.to_dict() for op in self.operations],
            "operation_count": len(self.operations),
            "status": self.status,
            "total_estimated_hours": self.total_estimated_hours,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
        }


PROCESS_TEMPLATES: dict[str, dict[str, Any]] = {
    "wing": {
        "template_name": "机翼装配工艺模板",
        "operations": [
            {"name": "翼梁定位与预装配", "type": OperationType.ASSEMBLY, "station": "STN-WING-01", "equipment": "定位夹具", "hours": 4.0},
            {"name": "肋板安装", "type": OperationType.ASSEMBLY, "station": "STN-WING-01", "equipment": "铆接设备", "hours": 6.0, "depends_on": [0]},
            {"name": "蒙皮铺设", "type": OperationType.ASSEMBLY, "station": "STN-WING-01", "equipment": "热压罐", "hours": 8.0, "depends_on": [1]},
            {"name": "IPQC-翼梁装配检验", "type": OperationType.INSPECTION, "station": "STN-WING-01", "equipment": "CMM", "hours": 2.0, "depends_on": [1], "is_qc": True, "is_gate": True},
            {"name": "蒙皮固化", "type": OperationType.ASSEMBLY, "station": "STN-WING-01", "equipment": "热压罐", "hours": 12.0, "depends_on": [2]},
            {"name": "FQC-机翼总检", "type": OperationType.QUALITY_GATE, "station": "STN-WING-01", "equipment": "CMM", "hours": 3.0, "depends_on": [4], "is_qc": True, "is_gate": True},
        ],
    },
    "fuselage": {
        "template_name": "机身装配工艺模板",
        "operations": [
            {"name": "加强框定位", "type": OperationType.ASSEMBLY, "station": "STN-FUSE-01", "equipment": "定位夹具", "hours": 3.0},
            {"name": "机身蒙皮铺设", "type": OperationType.ASSEMBLY, "station": "STN-FUSE-01", "equipment": "热压罐", "hours": 10.0, "depends_on": [0]},
            {"name": "蒙皮固化", "type": OperationType.ASSEMBLY, "station": "STN-FUSE-01", "equipment": "热压罐", "hours": 14.0, "depends_on": [1]},
            {"name": "IPQC-机身段检验", "type": OperationType.INSPECTION, "station": "STN-FUSE-01", "equipment": "CMM", "hours": 2.5, "depends_on": [1], "is_qc": True, "is_gate": True},
            {"name": "FQC-机身总检", "type": OperationType.QUALITY_GATE, "station": "STN-FUSE-01", "equipment": "CMM", "hours": 4.0, "depends_on": [2], "is_qc": True, "is_gate": True},
        ],
    },
    "tail": {
        "template_name": "尾翼装配工艺模板",
        "operations": [
            {"name": "水平尾翼梁安装", "type": OperationType.ASSEMBLY, "station": "STN-TAIL-01", "equipment": "定位夹具", "hours": 3.0},
            {"name": "垂直尾翼梁安装", "type": OperationType.ASSEMBLY, "station": "STN-TAIL-01", "equipment": "定位夹具", "hours": 3.0, "depends_on": [0]},
            {"name": "尾翼蒙皮铺设", "type": OperationType.ASSEMBLY, "station": "STN-TAIL-01", "equipment": "热压罐", "hours": 6.0, "depends_on": [1]},
            {"name": "FQC-尾翼总检", "type": OperationType.QUALITY_GATE, "station": "STN-TAIL-01", "equipment": "CMM", "hours": 2.0, "depends_on": [2], "is_qc": True, "is_gate": True},
        ],
    },
    "powerplant": {
        "template_name": "动力系统安装工艺模板",
        "operations": [
            {"name": "发动机吊架安装", "type": OperationType.INSTALLATION, "station": "STN-PP-01", "equipment": "起重设备", "hours": 5.0},
            {"name": "发动机安装", "type": OperationType.INSTALLATION, "station": "STN-PP-01", "equipment": "起重设备", "hours": 8.0, "depends_on": [0]},
            {"name": "燃油管路连接", "type": OperationType.INSTALLATION, "station": "STN-PP-01", "equipment": "管路工具", "hours": 4.0, "depends_on": [1]},
            {"name": "IPQC-动力系统检验", "type": OperationType.INSPECTION, "station": "STN-PP-01", "equipment": "测试台", "hours": 3.0, "depends_on": [2], "is_qc": True, "is_gate": True},
            {"name": "试车测试", "type": OperationType.TESTING, "station": "STN-PP-01", "equipment": "试车台", "hours": 6.0, "depends_on": [3]},
        ],
    },
    "electrical": {
        "template_name": "电气线束安装工艺模板",
        "operations": [
            {"name": "线束预组装", "type": OperationType.ASSEMBLY, "station": "STN-ELEC-01", "equipment": "线束工作台", "hours": 6.0},
            {"name": "线束铺设", "type": OperationType.INSTALLATION, "station": "STN-ELEC-01", "equipment": "铺设工具", "hours": 8.0, "depends_on": [0]},
            {"name": "连接器压接", "type": OperationType.INSTALLATION, "station": "STN-ELEC-01", "equipment": "压接工具", "hours": 4.0, "depends_on": [1]},
            {"name": "导通测试", "type": OperationType.TESTING, "station": "STN-ELEC-01", "equipment": "万用表", "hours": 3.0, "depends_on": [2]},
            {"name": "FQC-电气系统检验", "type": OperationType.QUALITY_GATE, "station": "STN-ELEC-01", "equipment": "综合测试台", "hours": 2.0, "depends_on": [3], "is_qc": True, "is_gate": True},
        ],
    },
}

EQUIPMENT_REGISTRY: dict[str, list[dict[str, Any]]] = {
    "assembly": [
        {"equipment_id": "EQ-FIXTURE-01", "name": "定位夹具", "type": "assembly"},
        {"equipment_id": "EQ-AUTOCLAVE-01", "name": "热压罐", "type": "assembly"},
        {"equipment_id": "EQ-RIVET-01", "name": "铆接设备", "type": "assembly"},
    ],
    "machining": [
        {"equipment_id": "EQ-CNC-01", "name": "CNC加工中心", "type": "machining"},
    ],
    "inspection": [
        {"equipment_id": "EQ-CMM-01", "name": "三坐标测量机", "type": "inspection"},
        {"equipment_id": "EQ-UT-01", "name": "超声检测仪", "type": "inspection"},
    ],
    "installation": [
        {"equipment_id": "EQ-CRANE-01", "name": "起重设备", "type": "installation"},
    ],
    "testing": [
        {"equipment_id": "EQ-TESTBENCH-01", "name": "综合测试台", "type": "testing"},
    ],
}

WORK_HOUR_FACTORS: dict[str, float] = {
    "CFRP": 1.3,
    "aluminum": 1.0,
    "steel": 0.9,
    "titanium": 1.2,
    "composite": 1.25,
}


class ProcessRouteDomainService:
    def generate_from_mbom(
        self,
        mbom_data: dict[str, Any],
        created_by: str = "",
    ) -> ProcessRoute:
        mbom_id = mbom_data.get("id", "")
        route_name = f"工艺路线-{mbom_data.get('mbom_code', 'UNKNOWN')}"

        route = ProcessRoute(mbom_id=mbom_id, route_name=route_name, created_by=created_by)

        root_item = mbom_data.get("root_item", {})
        if not root_item:
            return route

        component_types = self._extract_component_types(root_item)
        seq = 1
        op_id_map: dict[int, str] = {}

        for comp_type in component_types:
            template = PROCESS_TEMPLATES.get(comp_type)
            if template is None:
                continue

            for op_def in template["operations"]:
                op_id = generate_code("OP")
                dep_ids = [op_id_map[i] for i in op_def.get("depends_on", []) if i in op_id_map]

                op = Operation(
                    operation_id=op_id,
                    operation_name=op_def["name"],
                    operation_type=op_def["type"],
                    sequence=seq,
                    station=op_def.get("station", ""),
                    equipment=op_def.get("equipment", ""),
                    estimated_hours=op_def.get("hours", 0.0),
                    dependencies=dep_ids,
                    is_quality_checkpoint=op_def.get("is_qc", False),
                    is_mandatory_gate=op_def.get("is_gate", False),
                )
                route.add_operation(op)
                op_id_map[len(op_id_map)] = op_id
                seq += 1

        self.insert_quality_checkpoints(route)
        self.assign_equipment(route)
        self.estimate_work_hours(route, mbom_data)
        self.optimize_sequence(route)

        logger.info(
            "Process route generated: route_id=%s ops=%d hours=%.1f",
            route.id, len(route.operations), route.total_estimated_hours,
        )
        return route

    def assign_equipment(self, route: ProcessRoute) -> None:
        for op in route.operations:
            if op.equipment:
                continue
            op_type = op.operation_type.value
            available = EQUIPMENT_REGISTRY.get(op_type, [])
            if available:
                op.equipment = available[0]["equipment_id"]

    def estimate_work_hours(self, route: ProcessRoute, mbom_data: dict[str, Any]) -> None:
        material = self._get_primary_material(mbom_data)
        factor = WORK_HOUR_FACTORS.get(material, 1.0)

        for op in route.operations:
            if op.estimated_hours > 0:
                op.estimated_hours = round(op.estimated_hours * factor, 1)

        route._recalculate_hours()

    def optimize_sequence(self, route: ProcessRoute) -> None:
        dep_graph: dict[str, list[str]] = {}
        for op in route.operations:
            dep_graph[op.operation_id] = op.dependencies

        sorted_ops = self._topological_sort(route.operations, dep_graph)
        for seq, op in enumerate(sorted_ops, 1):
            op.sequence = seq
        route.operations = sorted_ops

    def insert_quality_checkpoints(self, route: ProcessRoute) -> None:
        existing_qc = {op.operation_id for op in route.operations if op.is_quality_checkpoint}
        assembly_ops = [op for op in route.operations if op.operation_type == OperationType.ASSEMBLY]

        for i, op in enumerate(assembly_ops):
            if i > 0 and i % 3 == 0:
                has_downstream_qc = any(
                    qop.operation_id in op.dependencies or qop.sequence > op.sequence
                    for qop in route.operations
                    if qop.is_quality_checkpoint and qop.sequence > op.sequence
                )
                if not has_downstream_qc:
                    qc_op = Operation(
                        operation_id=generate_code("OP"),
                        operation_name=f"IPQC-{op.operation_name}过程检验",
                        operation_type=OperationType.INSPECTION,
                        sequence=op.sequence + 1,
                        station=op.station,
                        equipment="CMM",
                        estimated_hours=1.5,
                        dependencies=[op.operation_id],
                        is_quality_checkpoint=True,
                        is_mandatory_gate=False,
                    )
                    route.add_operation(qc_op)

    def _extract_component_types(self, root_item: dict[str, Any]) -> list[str]:
        types: list[str] = []
        children = root_item.get("children", [])
        for child in children:
            name = child.get("name", "").lower()
            code = child.get("item_code", "").lower()
            if any(kw in name or kw in code for kw in ["wing", "翼", "左翼", "右翼"]):
                if "wing" not in types:
                    types.append("wing")
            elif any(kw in name or kw in code for kw in ["fuselage", "机身"]):
                if "fuselage" not in types:
                    types.append("fuselage")
            elif any(kw in name or kw in code for kw in ["tail", "尾翼"]):
                if "tail" not in types:
                    types.append("tail")
            elif any(kw in name or kw in code for kw in ["power", "动力", "engine"]):
                if "powerplant" not in types:
                    types.append("powerplant")
            elif any(kw in name or kw in code for kw in ["electrical", "电气", "线束"]):
                if "electrical" not in types:
                    types.append("electrical")

            sub_types = self._extract_component_types(child)
            for st in sub_types:
                if st not in types:
                    types.append(st)

        return types

    def _get_primary_material(self, mbom_data: dict[str, Any]) -> str:
        root = mbom_data.get("root_item", {})
        if root:
            attrs = root.get("attributes", {})
            mat = attrs.get("material", "")
            if mat:
                return str(mat).lower()
        return "aluminum"

    def _topological_sort(self, ops: list[Operation], dep_graph: dict[str, list[str]]) -> list[Operation]:
        op_map = {op.operation_id: op for op in ops}
        in_degree: dict[str, int] = {op.operation_id: 0 for op in ops}
        for op_id, deps in dep_graph.items():
            for dep in deps:
                if dep in in_degree:
                    pass

        for op_id, deps in dep_graph.items():
            in_degree[op_id] = len([d for d in deps if d in in_degree])

        queue = [op_id for op_id, deg in in_degree.items() if deg == 0]
        result: list[Operation] = []

        while queue:
            current = queue.pop(0)
            if current in op_map:
                result.append(op_map[current])

            for op_id, deps in dep_graph.items():
                if current in deps:
                    in_degree[op_id] -= 1
                    if in_degree[op_id] == 0:
                        queue.append(op_id)

        for op in ops:
            if op not in result:
                result.append(op)

        return result