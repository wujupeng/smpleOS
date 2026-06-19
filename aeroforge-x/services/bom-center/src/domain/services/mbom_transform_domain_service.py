from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from aeroforge_common.utils.helpers import generate_code

from ..entities.bom_item import BOMItem, EBOM, MBOM

logger = logging.getLogger(__name__)


ASSEMBLY_PROCESS_TEMPLATES: dict[str, dict[str, Any]] = {
    "wing": {
        "stations": [
            {
                "station_id": "STN-WING-01",
                "station_name": "左翼装配工位",
                "assembly_order": 1,
                "components": ["spar", "rib", "skin-wing"],
                "dependencies": [],
            },
            {
                "station_id": "STN-WING-02",
                "station_name": "右翼装配工位",
                "assembly_order": 2,
                "components": ["spar", "rib", "skin-wing"],
                "dependencies": ["STN-WING-01"],
            },
        ],
        "virtual_nodes": [
            {"name": "左翼装配组件", "station_id": "STN-WING-01"},
            {"name": "右翼装配组件", "station_id": "STN-WING-02"},
        ],
    },
    "fuselage": {
        "stations": [
            {
                "station_id": "STN-FUSE-01",
                "station_name": "机身前段装配工位",
                "assembly_order": 1,
                "components": ["frame", "skin-fuse"],
                "dependencies": [],
            },
            {
                "station_id": "STN-FUSE-02",
                "station_name": "机身后段装配工位",
                "assembly_order": 2,
                "components": ["frame", "skin-fuse"],
                "dependencies": ["STN-FUSE-01"],
            },
        ],
        "virtual_nodes": [
            {"name": "机身前段装配组件", "station_id": "STN-FUSE-01"},
            {"name": "机身后段装配组件", "station_id": "STN-FUSE-02"},
        ],
    },
    "tail": {
        "stations": [
            {
                "station_id": "STN-TAIL-01",
                "station_name": "尾翼装配工位",
                "assembly_order": 1,
                "components": ["h-spar", "v-spar"],
                "dependencies": [],
            },
        ],
        "virtual_nodes": [
            {"name": "尾翼装配组件", "station_id": "STN-TAIL-01"},
        ],
    },
}


@dataclass
class MappingConflict:
    ebom_item_code: str
    ebom_item_name: str
    reason: str
    suggested_action: str = "manual_review"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ebom_item_code": self.ebom_item_code,
            "ebom_item_name": self.ebom_item_name,
            "reason": self.reason,
            "suggested_action": self.suggested_action,
        }


@dataclass
class ValidationResult:
    is_valid: bool = True
    completeness_check: dict[str, Any] = field(default_factory=dict)
    order_check: dict[str, Any] = field(default_factory=dict)
    virtual_node_check: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "completeness_check": self.completeness_check,
            "order_check": self.order_check,
            "virtual_node_check": self.virtual_node_check,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class AssemblyProcessMapper:
    def map_to_stations(
        self,
        ebom_items: list[BOMItem],
        template: dict[str, Any],
    ) -> dict[str, list[BOMItem]]:
        station_map: dict[str, list[BOMItem]] = {}
        for station in template.get("stations", []):
            station_id = station["station_id"]
            station_map[station_id] = []

        for item in ebom_items:
            assigned = False
            for station in template.get("stations", []):
                component_keywords = station.get("components", [])
                for keyword in component_keywords:
                    if keyword in item.item_code.lower() or keyword in item.name.lower():
                        station_map[station["station_id"]].append(item)
                        assigned = True
                        break
                if assigned:
                    break

            if not assigned:
                first_station = template["stations"][0]["station_id"]
                station_map[first_station].append(item)

        return station_map

    def reorder_hierarchy(
        self,
        station_map: dict[str, list[BOMItem]],
        template: dict[str, Any],
    ) -> list[tuple[str, int, list[BOMItem]]]:
        ordered: list[tuple[str, int, list[BOMItem]]] = []
        stations = sorted(
            template.get("stations", []),
            key=lambda s: s.get("assembly_order", 0),
        )
        for station in stations:
            sid = station["station_id"]
            if sid in station_map:
                ordered.append((sid, station["assembly_order"], station_map[sid]))
        return ordered

    def add_virtual_nodes(
        self,
        ordered_stations: list[tuple[str, int, list[BOMItem]]],
        template: dict[str, Any],
    ) -> list[BOMItem]:
        virtual_nodes_map: dict[str, dict[str, Any]] = {}
        for vn in template.get("virtual_nodes", []):
            virtual_nodes_map[vn["station_id"]] = vn

        result_nodes: list[BOMItem] = []
        for station_id, order, items in ordered_stations:
            vn_config = virtual_nodes_map.get(station_id)
            if vn_config:
                virtual_item = BOMItem(
                    item_code=generate_code("AAF-VASM"),
                    name=vn_config["name"],
                    bom_type="mbom",
                    part_type="virtual_assembly",
                    station=station_id,
                    assembly_order=order,
                    is_virtual=True,
                )
                for item in items:
                    mbom_item = BOMItem(
                        item_code=item.item_code,
                        name=item.name,
                        bom_type="mbom",
                        quantity=item.quantity,
                        unit=item.unit,
                        version=item.version,
                        part_type=item.part_type,
                        attributes=item.attributes,
                        station=station_id,
                        assembly_order=order,
                        ebom_item_code=item.item_code,
                    )
                    virtual_item.add_child(mbom_item)
                result_nodes.append(virtual_item)
            else:
                for item in items:
                    mbom_item = BOMItem(
                        item_code=item.item_code,
                        name=item.name,
                        bom_type="mbom",
                        quantity=item.quantity,
                        unit=item.unit,
                        version=item.version,
                        part_type=item.part_type,
                        attributes=item.attributes,
                        station=station_id,
                        assembly_order=order,
                        ebom_item_code=item.item_code,
                    )
                    result_nodes.append(mbom_item)

        return result_nodes


class MBOMTransformDomainService:
    def __init__(self) -> None:
        self._mapper = AssemblyProcessMapper()
        self._templates = ASSEMBLY_PROCESS_TEMPLATES

    def transform_from_ebom(self, ebom: EBOM, created_by: str = "") -> MBOM:
        if ebom.root_item is None:
            raise ValueError("Cannot transform empty eBOM")

        mbom = MBOM(ebom_id=ebom.id, created_by=created_by)

        all_ebom_items = ebom.root_item.flatten()
        component_items = [item for item in all_ebom_items if item.part_type != "assembly" or item.children]

        grouped_by_component_type = self._group_by_component_type(component_items)

        root_item = BOMItem(
            item_code=generate_code("AAF-MBOM"),
            name="飞行器制造总装",
            bom_type="mbom",
            part_type="assembly",
            station="STN-ROOT",
            assembly_order=0,
        )

        for comp_type, items in grouped_by_component_type.items():
            template = self._templates.get(comp_type)
            if template:
                station_map = self._mapper.map_to_stations(items, template)
                ordered = self._mapper.reorder_hierarchy(station_map, template)
                virtual_nodes = self._mapper.add_virtual_nodes(ordered, template)
                for node in virtual_nodes:
                    root_item.add_child(node)
            else:
                for item in items:
                    mbom_item = BOMItem(
                        item_code=item.item_code,
                        name=item.name,
                        bom_type="mbom",
                        quantity=item.quantity,
                        unit=item.unit,
                        part_type=item.part_type,
                        attributes=item.attributes,
                        ebom_item_code=item.item_code,
                        mapping_status="unmapped",
                    )
                    root_item.add_child(mbom_item)
                    mbom.add_unmapped_item({
                        "ebom_item_code": item.item_code,
                        "ebom_item_name": item.name,
                        "reason": f"No assembly process template for component type: {comp_type}",
                        "suggested_action": "manual_review",
                    })

        mbom.set_root(root_item)

        conflicts = self.resolve_mapping_conflicts(ebom, mbom)
        for conflict in conflicts:
            mbom.add_unmapped_item(conflict.to_dict())

        validation = self.validate_transformation(ebom, mbom)
        mbom.set_validation_result(validation.to_dict())

        logger.info(
            "mBOM transformed: ebom_id=%s mbom_id=%s unmapped=%d valid=%s",
            ebom.id, mbom.id, len(mbom.unmapped_items), validation.is_valid,
        )
        return mbom

    def apply_assembly_process(
        self,
        ebom: EBOM,
        process_template: dict[str, Any],
    ) -> BOMItem:
        if ebom.root_item is None:
            raise ValueError("Cannot apply assembly process to empty eBOM")

        all_items = ebom.root_item.flatten()
        non_root = [i for i in all_items if i is not ebom.root_item]

        station_map = self._mapper.map_to_stations(non_root, process_template)
        ordered = self._mapper.reorder_hierarchy(station_map, process_template)
        virtual_nodes = self._mapper.add_virtual_nodes(ordered, process_template)

        root = BOMItem(
            item_code=generate_code("AAF-MBOM"),
            name="飞行器制造总装",
            bom_type="mbom",
            part_type="assembly",
        )
        for node in virtual_nodes:
            root.add_child(node)

        return root

    def resolve_mapping_conflicts(self, ebom: EBOM, mbom: MBOM) -> list[MappingConflict]:
        conflicts: list[MappingConflict] = []

        if ebom.root_item is None or mbom.root_item is None:
            return conflicts

        ebom_items = ebom.root_item.flatten()
        mbom_items = mbom.root_item.flatten()

        ebom_codes = {item.item_code for item in ebom_items}
        mbom_ebom_refs = {item.ebom_item_code for item in mbom_items if item.ebom_item_code}

        for code in ebom_codes:
            if code not in mbom_ebom_refs:
                ebom_item = next((i for i in ebom_items if i.item_code == code), None)
                if ebom_item and ebom_item.part_type != "assembly":
                    conflicts.append(MappingConflict(
                        ebom_item_code=code,
                        ebom_item_name=ebom_item.name,
                        reason="eBOM item not mapped to any mBOM station",
                        suggested_action="manual_review",
                    ))

        unmapped_mbom = [i for i in mbom_items if i.mapping_status == "unmapped"]
        for item in unmapped_mbom:
            conflicts.append(MappingConflict(
                ebom_item_code=item.item_code,
                ebom_item_name=item.name,
                reason="mBOM item has no assembly process template mapping",
                suggested_action="assign_to_station",
            ))

        return conflicts

    def validate_transformation(self, ebom: EBOM, mbom: MBOM) -> ValidationResult:
        result = ValidationResult()

        if ebom.root_item is None or mbom.root_item is None:
            result.is_valid = False
            result.errors.append("Empty eBOM or mBOM root")
            return result

        ebom_items = ebom.root_item.flatten()
        mbom_items = mbom.root_item.flatten()

        ebom_codes = {item.item_code for item in ebom_items if item.part_type != "assembly"}
        mbom_ebom_refs = {item.ebom_item_code for item in mbom_items if item.ebom_item_code}

        missing = ebom_codes - mbom_ebom_refs
        result.completeness_check = {
            "total_ebom_items": len(ebom_codes),
            "mapped_items": len(ebom_codes & mbom_ebom_refs),
            "unmapped_items": len(missing),
            "missing_codes": list(missing),
        }
        if missing:
            result.warnings.append(f"{len(missing)} eBOM items not mapped to mBOM")

        stations_with_items: dict[str, list[int]] = {}
        for item in mbom_items:
            if item.station:
                stations_with_items.setdefault(item.station, []).append(item.assembly_order)

        order_violations: list[str] = []
        for station, orders in stations_with_items.items():
            if orders != sorted(orders):
                order_violations.append(f"Station {station} has out-of-order assembly steps")

        result.order_check = {
            "total_stations": len(stations_with_items),
            "order_violations": order_violations,
        }
        if order_violations:
            result.warnings.extend(order_violations)

        virtual_nodes = [i for i in mbom_items if i.is_virtual]
        empty_virtual = [i for i in virtual_nodes if not i.children]
        unnecessary_virtual = [i for i in virtual_nodes if len(i.children) <= 1 and not i.is_virtual]

        result.virtual_node_check = {
            "total_virtual_nodes": len(virtual_nodes),
            "empty_virtual_nodes": len(empty_virtual),
            "unnecessary_virtual_nodes": len(unnecessary_virtual),
        }
        if empty_virtual:
            result.warnings.append(f"{len(empty_virtual)} virtual nodes have no children")

        if result.errors:
            result.is_valid = False

        return result

    def _group_by_component_type(self, items: list[BOMItem]) -> dict[str, list[BOMItem]]:
        groups: dict[str, list[BOMItem]] = {}
        for item in items:
            comp_type = self._infer_component_type(item)
            groups.setdefault(comp_type, []).append(item)
        return groups

    def _infer_component_type(self, item: BOMItem) -> str:
        name_lower = item.name.lower()
        code_lower = item.item_code.lower()

        if any(kw in name_lower or kw in code_lower for kw in ["wing", "翼", "spar", "rib", "skin-wing"]):
            return "wing"
        if any(kw in name_lower or kw in code_lower for kw in ["fuselage", "机身", "frame", "skin-fuse"]):
            return "fuselage"
        if any(kw in name_lower or kw in code_lower for kw in ["tail", "尾翼", "h-spar", "v-spar"]):
            return "tail"

        return "unknown"