"""AeroForge-X v5.0 BOMThreeViewManagerService

Manages EBOM/MBOM/SBOM three-view BOM lifecycle: creation, automatic conversion,
change propagation, consistency detection, and version management.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BOMType(str, Enum):
    EBOM = "EBOM"
    MBOM = "MBOM"
    SBOM = "SBOM"


class ChangeType(str, Enum):
    ADD_PART = "AddPart"
    REMOVE_PART = "RemovePart"
    MODIFY_PART = "ModifyPart"
    CHANGE_QUANTITY = "ChangeQuantity"


class MakeOrBuy(str, Enum):
    MAKE = "Make"
    BUY = "Buy"


@dataclass
class BOMNode:
    node_id: str
    part_number: str
    part_name: str
    quantity: int
    unit: str = "EA"
    material: str = ""
    make_or_buy: MakeOrBuy = MakeOrBuy.MAKE
    specifications: dict = field(default_factory=dict)
    parent_node_id: Optional[str] = None
    children: list[BOMNode] = field(default_factory=list)
    sort_order: int = 0

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "part_number": self.part_number,
            "part_name": self.part_name,
            "quantity": self.quantity,
            "unit": self.unit,
            "material": self.material,
            "make_or_buy": self.make_or_buy.value,
            "specifications": self.specifications,
            "parent_node_id": self.parent_node_id,
            "children": [c.to_dict() for c in self.children],
            "sort_order": self.sort_order,
        }

    def find_node(self, node_id: str) -> Optional[BOMNode]:
        if self.node_id == node_id:
            return self
        for child in self.children:
            found = child.find_node(node_id)
            if found:
                return found
        return None


@dataclass
class EBOMChange:
    change_id: str
    change_type: ChangeType
    affected_node_id: Optional[str]
    new_values: dict
    reason: str
    requested_by: str


@dataclass
class ManufacturingRule:
    rule_id: str
    rule_type: str
    condition: str
    action: dict
    priority: int = 0


@dataclass
class ServiceRule:
    rule_id: str
    rule_type: str
    condition: str
    action: dict


@dataclass
class PropagationResult:
    change_id: str
    mbom_changes: list[dict]
    sbom_changes: list[dict]
    manual_resolutions_needed: list[dict]
    propagation_time_ms: float
    status: str = "Completed"


@dataclass
class ReconciliationReport:
    bom_id: str
    inconsistencies: list[dict]
    is_consistent: bool


@dataclass
class EBOM:
    bom_id: str
    project_id: str
    version: int
    root_node: Optional[BOMNode]
    locked: bool = False
    change_history: list[EBOMChange] = field(default_factory=list)


@dataclass
class MBOM:
    bom_id: str
    source_ebom_id: str
    version: int
    root_node: Optional[BOMNode]
    manufacturing_rules_applied: list[str] = field(default_factory=list)


@dataclass
class SBOM:
    bom_id: str
    source_mbom_id: str
    version: int
    root_node: Optional[BOMNode]
    service_rules_applied: list[str] = field(default_factory=list)


class BOMThreeViewManagerService:

    def __init__(self) -> None:
        self._eboms: dict[str, EBOM] = {}
        self._mboms: dict[str, MBOM] = {}
        self._sboms: dict[str, SBOM] = {}
        self._propagation_idempotency: dict[str, bool] = {}

    def create_ebom(
        self,
        project_id: str,
        root_node_data: dict | None = None,
    ) -> EBOM:
        bom_id = f"EBOM-{project_id}-{uuid.uuid4().hex[:6].upper()}"

        root_node = None
        if root_node_data:
            root_node = self._dict_to_node(root_node_data)

        ebom = EBOM(
            bom_id=bom_id,
            project_id=project_id,
            version=1,
            root_node=root_node,
        )
        self._eboms[bom_id] = ebom
        return ebom

    def convert_ebom_to_mbom(
        self,
        ebom_id: str,
        rules: list[ManufacturingRule] | None = None,
    ) -> MBOM:
        ebom = self._eboms.get(ebom_id)
        if ebom is None:
            raise ValueError(f"EBOM {ebom_id} not found")

        mbom_id = f"MBOM-{ebom.project_id}-{uuid.uuid4().hex[:6].upper()}"

        mbom_root = self._deep_copy_node(ebom.root_node) if ebom.root_node else None

        applied_rules: list[str] = []
        if rules:
            for rule in sorted(rules, key=lambda r: r.priority, reverse=True):
                mbom_root = self._apply_manufacturing_rule(mbom_root, rule)
                applied_rules.append(rule.rule_id)

        if mbom_root:
            self._assign_assembly_sequence(mbom_root)

        mbom = MBOM(
            bom_id=mbom_id,
            source_ebom_id=ebom_id,
            version=1,
            root_node=mbom_root,
            manufacturing_rules_applied=applied_rules,
        )
        self._mboms[mbom_id] = mbom
        return mbom

    def convert_mbom_to_sbom(
        self,
        mbom_id: str,
        rules: list[ServiceRule] | None = None,
    ) -> SBOM:
        mbom = self._mboms.get(mbom_id)
        if mbom is None:
            raise ValueError(f"MBOM {mbom_id} not found")

        sbom_id = f"SBOM-{uuid.uuid4().hex[:6].upper()}"

        sbom_root = self._deep_copy_node(mbom.root_node) if mbom.root_node else None

        applied_rules: list[str] = []
        if rules:
            for rule in rules:
                sbom_root = self._apply_service_rule(sbom_root, rule)
                applied_rules.append(rule.rule_id)

        if sbom_root:
            self._mark_life_limited_parts(sbom_root)

        sbom = SBOM(
            bom_id=sbom_id,
            source_mbom_id=mbom_id,
            version=1,
            root_node=sbom_root,
            service_rules_applied=applied_rules,
        )
        self._sboms[sbom_id] = sbom
        return sbom

    def propagate_ebom_change(
        self,
        ebom_id: str,
        change: EBOMChange,
    ) -> PropagationResult:
        idempotency_key = f"{ebom_id}:{change.change_id}"
        if idempotency_key in self._propagation_idempotency:
            return PropagationResult(
                change_id=change.change_id,
                mbom_changes=[],
                sbom_changes=[],
                manual_resolutions_needed=[],
                propagation_time_ms=0.0,
                status="AlreadyPropagated",
            )

        start = time.time()

        ebom = self._eboms.get(ebom_id)
        if ebom is None:
            raise ValueError(f"EBOM {ebom_id} not found")

        if ebom.locked:
            raise ValueError(f"EBOM {ebom_id} is locked")

        self._apply_change_to_node(ebom.root_node, change)
        ebom.change_history.append(change)

        mbom_changes: list[dict] = []
        sbom_changes: list[dict] = []
        manual_resolutions: list[dict] = []

        for mbom_id, mbom in self._mboms.items():
            if mbom.source_ebom_id == ebom_id:
                propagated = self._propagate_to_mbom(mbom, change)
                mbom_changes.append(propagated)
                if not propagated.get("auto_resolved", True):
                    manual_resolutions.append(propagated)

                for sbom_id, sbom in self._sboms.items():
                    if sbom.source_mbom_id == mbom_id:
                        sbom_prop = self._propagate_to_sbom(sbom, change)
                        sbom_changes.append(sbom_prop)

        elapsed = (time.time() - start) * 1000

        self._propagation_idempotency[idempotency_key] = True

        return PropagationResult(
            change_id=change.change_id,
            mbom_changes=mbom_changes,
            sbom_changes=sbom_changes,
            manual_resolutions_needed=manual_resolutions,
            propagation_time_ms=elapsed,
        )

    def detect_inconsistencies(self, bom_id: str) -> ReconciliationReport:
        inconsistencies: list[dict] = []

        ebom = self._eboms.get(bom_id)
        if ebom is not None:
            if ebom.root_node:
                inconsistencies.extend(self._check_node_inconsistencies(ebom.root_node))

        mbom = self._mboms.get(bom_id)
        if mbom is not None:
            if mbom.root_node:
                inconsistencies.extend(self._check_node_inconsistencies(mbom.root_node))

        sbom = self._sboms.get(bom_id)
        if sbom is not None:
            if sbom.root_node:
                inconsistencies.extend(self._check_node_inconsistencies(sbom.root_node))

        return ReconciliationReport(
            bom_id=bom_id,
            inconsistencies=inconsistencies,
            is_consistent=len(inconsistencies) == 0,
        )

    def get_bom_version(
        self,
        bom_id: str,
        version: int | None = None,
    ) -> Optional[dict]:
        if bom_id in self._eboms:
            ebom = self._eboms[bom_id]
            return {
                "bom_id": ebom.bom_id,
                "bom_type": "EBOM",
                "version": ebom.version,
                "project_id": ebom.project_id,
                "locked": ebom.locked,
                "root_node": ebom.root_node.to_dict() if ebom.root_node else None,
            }
        if bom_id in self._mboms:
            mbom = self._mboms[bom_id]
            return {
                "bom_id": mbom.bom_id,
                "bom_type": "MBOM",
                "version": mbom.version,
                "source_ebom_id": mbom.source_ebom_id,
                "root_node": mbom.root_node.to_dict() if mbom.root_node else None,
            }
        if bom_id in self._sboms:
            sbom = self._sboms[bom_id]
            return {
                "bom_id": sbom.bom_id,
                "bom_type": "SBOM",
                "version": sbom.version,
                "source_mbom_id": sbom.source_mbom_id,
                "root_node": sbom.root_node.to_dict() if sbom.root_node else None,
            }
        return None

    def _dict_to_node(self, data: dict) -> BOMNode:
        children = [self._dict_to_node(c) for c in data.get("children", [])]
        return BOMNode(
            node_id=data.get("node_id", f"NODE-{uuid.uuid4().hex[:6].upper()}"),
            part_number=data.get("part_number", ""),
            part_name=data.get("part_name", ""),
            quantity=data.get("quantity", 1),
            unit=data.get("unit", "EA"),
            material=data.get("material", ""),
            make_or_buy=MakeOrBuy(data.get("make_or_buy", "Make")),
            specifications=data.get("specifications", {}),
            parent_node_id=data.get("parent_node_id"),
            children=children,
            sort_order=data.get("sort_order", 0),
        )

    def _deep_copy_node(self, node: BOMNode | None) -> BOMNode | None:
        if node is None:
            return None
        return BOMNode(
            node_id=node.node_id,
            part_number=node.part_number,
            part_name=node.part_name,
            quantity=node.quantity,
            unit=node.unit,
            material=node.material,
            make_or_buy=node.make_or_buy,
            specifications=dict(node.specifications),
            parent_node_id=node.parent_node_id,
            children=[self._deep_copy_node(c) for c in node.children],
            sort_order=node.sort_order,
        )

    def _apply_manufacturing_rule(self, node: BOMNode | None, rule: ManufacturingRule) -> BOMNode | None:
        if node is None:
            return None

        if rule.rule_type == "AssemblySequence":
            self._assign_assembly_sequence(node)
        elif rule.rule_type == "MakeBuyDecision":
            self._apply_make_buy_decision(node, rule.action)
        elif rule.rule_type == "MaterialSubstitution":
            self._apply_material_substitution(node, rule.action)

        for child in node.children:
            self._apply_manufacturing_rule(child, rule)

        return node

    def _apply_service_rule(self, node: BOMNode | None, rule: ServiceRule) -> BOMNode | None:
        if node is None:
            return None

        if rule.rule_type == "SparePartIdentification":
            if node.make_or_buy == MakeOrBuy.BUY or node.quantity > 1:
                node.specifications["is_spare_part"] = True
        elif rule.rule_type == "MaintenanceItemExtraction":
            node.specifications["requires_maintenance"] = True
        elif rule.rule_type == "LifeLimitedPart":
            node.specifications["life_limited"] = True

        for child in node.children:
            self._apply_service_rule(child, rule)

        return node

    def _assign_assembly_sequence(self, node: BOMNode, seq: int = 0) -> int:
        node.sort_order = seq
        for child in node.children:
            seq += 1
            seq = self._assign_assembly_sequence(child, seq)
        return seq

    def _apply_make_buy_decision(self, node: BOMNode, action: dict) -> None:
        condition_part = action.get("part_number_prefix", "")
        if node.part_number.startswith(condition_part):
            node.make_or_buy = MakeOrBuy(action.get("decision", "Buy"))

    def _apply_material_substitution(self, node: BOMNode, action: dict) -> None:
        original = action.get("original_material", "")
        substitute = action.get("substitute_material", "")
        if node.material == original:
            node.material = substitute

    def _mark_life_limited_parts(self, node: BOMNode) -> None:
        life_limited_prefixes = ["ENG-", "LG-", "HYD-"]
        if any(node.part_number.startswith(p) for p in life_limited_prefixes):
            node.specifications["life_limited"] = True
            node.specifications["life_limit_hours"] = 30000
        for child in node.children:
            self._mark_life_limited_parts(child)

    def _apply_change_to_node(self, node: BOMNode | None, change: EBOMChange) -> None:
        if node is None:
            return

        if change.affected_node_id and node.node_id == change.affected_node_id:
            if change.change_type == ChangeType.MODIFY_PART:
                for k, v in change.new_values.items():
                    if hasattr(node, k):
                        setattr(node, k, v)
            elif change.change_type == ChangeType.CHANGE_QUANTITY:
                node.quantity = change.new_values.get("quantity", node.quantity)
            elif change.change_type == ChangeType.ADD_PART:
                new_child = self._dict_to_node(change.new_values)
                new_child.parent_node_id = node.node_id
                node.children.append(new_child)
            elif change.change_type == ChangeType.REMOVE_PART:
                node.children = [c for c in node.children if c.node_id != change.new_values.get("node_id")]
            return

        for child in node.children:
            self._apply_change_to_node(child, change)

    def _propagate_to_mbom(self, mbom: MBOM, change: EBOMChange) -> dict:
        if mbom.root_node:
            affected = mbom.root_node.find_node(change.affected_node_id) if change.affected_node_id else None
            if affected:
                self._apply_change_to_node(mbom.root_node, change)
                return {
                    "mbom_id": mbom.bom_id,
                    "change_applied": True,
                    "auto_resolved": True,
                }

        return {
            "mbom_id": mbom.bom_id,
            "change_applied": False,
            "auto_resolved": False,
            "reason": "Affected node not found in MBOM — manual resolution needed",
        }

    def _propagate_to_sbom(self, sbom: SBOM, change: EBOMChange) -> dict:
        if sbom.root_node:
            affected = sbom.root_node.find_node(change.affected_node_id) if change.affected_node_id else None
            if affected:
                self._apply_change_to_node(sbom.root_node, change)
                return {
                    "sbom_id": sbom.bom_id,
                    "change_applied": True,
                }

        return {
            "sbom_id": sbom.bom_id,
            "change_applied": False,
        }

    def _check_node_inconsistencies(self, node: BOMNode, visited: set | None = None) -> list[dict]:
        if visited is None:
            visited = set()

        issues: list[dict] = []

        if node.node_id in visited:
            issues.append({
                "type": "CircularDependency",
                "node_id": node.node_id,
                "message": f"Circular dependency detected for node {node.node_id}",
            })
            return issues

        visited.add(node.node_id)

        if not node.part_number:
            issues.append({
                "type": "MissingPartNumber",
                "node_id": node.node_id,
                "message": f"Node {node.node_id} has no part number",
            })

        if node.quantity <= 0:
            issues.append({
                "type": "InvalidQuantity",
                "node_id": node.node_id,
                "message": f"Node {node.node_id} has invalid quantity {node.quantity}",
            })

        for child in node.children:
            if child.parent_node_id != node.node_id:
                issues.append({
                    "type": "OrphanNode",
                    "node_id": child.node_id,
                    "message": f"Node {child.node_id} parent mismatch",
                })
            issues.extend(self._check_node_inconsistencies(child, visited))

        return issues