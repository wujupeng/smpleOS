from __future__ import annotations

import logging
from typing import Optional

from ..entities.plm_entities import (
    DesignObject, DesignBaseline, EngineeringChangeRequest,
    EngineeringChangeOrder, EngineeringChangeNotice,
)

logger = logging.getLogger(__name__)


class ProductStructureService:
    def __init__(self) -> None:
        self._structures: dict[str, dict] = {}

    def create_structure(self, product_id: str, product_name: str) -> dict:
        from ..entities.product_tree import ProductTree, ProductNode
        tree = ProductTree(name=product_name)
        tree.set_root(ProductNode(part_id=f"{product_id}-root", name=product_name, part_type="assembly"))
        self._structures[tree.id] = tree.to_dict()
        return tree.to_dict()

    def get_product_tree(self, structure_id: str) -> dict | None:
        return self._structures.get(structure_id)

    def add_child(self, structure_id: str, parent_id: str, part_id: str, name: str, part_type: str = "part", quantity: int = 1) -> bool:
        struct = self._structures.get(structure_id)
        if not struct:
            return False
        return True


class VersionManagementService:
    def __init__(self) -> None:
        self._objects: dict[str, DesignObject] = {}

    def create_object(self, object_number: str, object_type: str, object_name: str, owner_id: str | None = None) -> DesignObject:
        obj = DesignObject(object_number=object_number, object_type=object_type, object_name=object_name, owner_id=owner_id)
        self._objects[obj.object_id] = obj
        return obj

    def get_object(self, object_id: str) -> Optional[DesignObject]:
        return self._objects.get(object_id)

    def create_version(self, object_id: str, change_summary: str = "", author_id: str | None = None) -> dict:
        obj = self._get_or_raise(object_id)
        return obj.create_version(change_summary=change_summary, author_id=author_id)

    def get_item_versions(self, object_id: str) -> list[dict]:
        obj = self._get_or_raise(object_id)
        return obj.get_versions()

    def _get_or_raise(self, object_id: str) -> DesignObject:
        obj = self._objects.get(object_id)
        if not obj:
            raise ValueError(f"Design object {object_id} not found")
        return obj


class BaselineManagementService:
    def __init__(self) -> None:
        self._baselines: dict[str, DesignBaseline] = {}

    def create_baseline(self, baseline_name: str, baseline_type: str = "development", created_by: str | None = None) -> DesignBaseline:
        bl = DesignBaseline(baseline_name=baseline_name, baseline_type=baseline_type, created_by=created_by)
        self._baselines[bl.baseline_id] = bl
        return bl

    def get_baseline(self, baseline_id: str) -> Optional[DesignBaseline]:
        return self._baselines.get(baseline_id)

    def freeze_baseline(self, baseline_id: str, frozen_by: str) -> DesignBaseline:
        bl = self._get_or_raise(baseline_id)
        bl.freeze(frozen_by)
        return bl

    def unfreeze_baseline(self, baseline_id: str) -> DesignBaseline:
        bl = self._get_or_raise(baseline_id)
        bl.unfreeze()
        return bl

    def compare_baselines(self, baseline_a_id: str, baseline_b_id: str) -> dict:
        ba = self._get_or_raise(baseline_a_id)
        bb = self._get_or_raise(baseline_b_id)
        versions_a = {(v["object_id"], v["version"]) for v in ba.object_versions}
        versions_b = {(v["object_id"], v["version"]) for v in bb.object_versions}
        added = versions_b - versions_a
        removed = versions_a - versions_b
        return {
            "baseline_a": ba.baseline_name,
            "baseline_b": bb.baseline_name,
            "added": len(added),
            "removed": len(removed),
        }

    def _get_or_raise(self, baseline_id: str) -> DesignBaseline:
        bl = self._baselines.get(baseline_id)
        if not bl:
            raise ValueError(f"Baseline {baseline_id} not found")
        return bl


class ChangeManagementService:
    def __init__(self) -> None:
        self._ecrs: dict[str, EngineeringChangeRequest] = {}
        self._ecos: dict[str, EngineeringChangeOrder] = {}
        self._ecns: dict[str, EngineeringChangeNotice] = {}

    def create_ecr(self, ecr_number: str, change_type: str, title: str, description: str, priority: str = "medium", safety_critical: bool = False, requested_by: str | None = None) -> EngineeringChangeRequest:
        ecr = EngineeringChangeRequest(
            ecr_number=ecr_number, change_type=change_type, title=title,
            description=description, priority=priority, safety_critical=safety_critical,
            requested_by=requested_by,
        )
        self._ecrs[ecr.ecr_id] = ecr
        logger.info(f"ECR created: {ecr_number}")
        return ecr

    def get_ecr(self, ecr_id: str) -> Optional[EngineeringChangeRequest]:
        return self._ecrs.get(ecr_id)

    def analyze_change_impact(self, ecr_id: str, affected_objects: list[dict]) -> dict:
        ecr = self._get_ecr_or_raise(ecr_id)
        return ecr.analyze_impact(affected_objects)

    def approve_ecr(self, ecr_id: str, approver_id: str) -> EngineeringChangeRequest:
        ecr = self._get_ecr_or_raise(ecr_id)
        ecr.approve(approver_id)
        return ecr

    def reject_ecr(self, ecr_id: str) -> EngineeringChangeRequest:
        ecr = self._get_ecr_or_raise(ecr_id)
        ecr.reject()
        return ecr

    def create_eco(self, ecr_id: str, eco_number: str, implementation_plan: str = "") -> EngineeringChangeOrder:
        ecr = self._get_ecr_or_raise(ecr_id)
        if ecr.approval_status != "approved":
            raise ValueError("ECR must be approved before creating ECO")
        eco = EngineeringChangeOrder(ecr_id=ecr_id, eco_number=eco_number, implementation_plan=implementation_plan)
        self._ecos[eco.eco_id] = eco
        return eco

    def create_ecn(self, eco_id: str, ecn_number: str, description: str = "", effective_date: str | None = None) -> EngineeringChangeNotice:
        eco = self._ecos.get(eco_id)
        if not eco:
            raise ValueError(f"ECO {eco_id} not found")
        ecn = EngineeringChangeNotice(eco_id=eco_id, ecn_number=ecn_number, description=description, effective_date=effective_date)
        self._ecns[ecn.ecn_id] = ecn
        return ecn

    def list_ecrs(self, status: str | None = None) -> list[EngineeringChangeRequest]:
        ecrs = list(self._ecrs.values())
        if status:
            ecrs = [e for e in ecrs if e.approval_status == status]
        return ecrs

    def _get_ecr_or_raise(self, ecr_id: str) -> EngineeringChangeRequest:
        ecr = self._ecrs.get(ecr_id)
        if not ecr:
            raise ValueError(f"ECR {ecr_id} not found")
        return ecr