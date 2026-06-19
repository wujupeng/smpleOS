"""AeroForge-X v6.0 ThreeViewConfigPropagationService

Manages Design/Manufacturing/Operational three-view configuration unification:
automatic derivation, change propagation, and inconsistency detection.
REQ-CFG-007~011
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .configuration_manager_service import (
    BlockConfiguration,
    ConfigViewType,
    ConfigurationItem,
    DesignConfiguration,
    ManufacturingConfiguration,
    OperationalConfiguration,
)


@dataclass
class ManufacturingRule:
    rule_id: str
    rule_type: str
    rule_expression: str
    priority: int = 0

    def apply(self, items: list[ConfigurationItem]) -> list[ConfigurationItem]:
        result_items = []
        for item in items:
            new_item = ConfigurationItem(
                item_id=item.item_id,
                item_name=item.item_name,
                item_type=item.item_type,
                value=dict(item.value),
                version=item.version,
                source_view=ConfigViewType.MANUFACTURING,
            )
            if self.rule_type == "ProcessAssignment":
                new_item.value["assigned_process"] = self.rule_expression
            elif self.rule_type == "ToolingReference":
                new_item.value["tooling_ref"] = self.rule_expression
            elif self.rule_type == "InspectionRequirement":
                new_item.value["inspection_req"] = self.rule_expression
            result_items.append(new_item)
        return result_items


@dataclass
class OperationalRule:
    rule_id: str
    rule_type: str
    rule_expression: str
    priority: int = 0

    def apply(self, items: list[ConfigurationItem]) -> list[ConfigurationItem]:
        result_items = []
        for item in items:
            new_item = ConfigurationItem(
                item_id=item.item_id,
                item_name=item.item_name,
                item_type=item.item_type,
                value=dict(item.value),
                version=item.version,
                source_view=ConfigViewType.OPERATIONAL,
            )
            if self.rule_type == "EquipmentInstallation":
                new_item.value["equipment_install"] = self.rule_expression
            elif self.rule_type == "SoftwareLoad":
                new_item.value["software_load"] = self.rule_expression
            elif self.rule_type == "MaintenanceItem":
                new_item.value["maintenance_item"] = self.rule_expression
            result_items.append(new_item)
        return result_items


@dataclass
class DesignConfigChange:
    block_id: str
    changed_items: list[dict]
    change_reason: str
    change_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class PropagationResult:
    design_updated: bool
    manufacturing_updated: bool
    operational_updated: bool
    manual_resolution_needed: list[dict] = field(default_factory=list)
    propagation_duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "design_updated": self.design_updated,
            "manufacturing_updated": self.manufacturing_updated,
            "operational_updated": self.operational_updated,
            "manual_resolution_needed": self.manual_resolution_needed,
            "propagation_duration_ms": self.propagation_duration_ms,
        }


@dataclass
class DiscrepancyEntry:
    item_id: str
    design_value: Optional[dict]
    manufacturing_value: Optional[dict]
    operational_value: Optional[dict]
    discrepancy_type: str


@dataclass
class ReconciliationReport:
    config_id: str
    discrepancies: list[DiscrepancyEntry] = field(default_factory=list)
    reconciliation_suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "config_id": self.config_id,
            "discrepancies": [
                {
                    "item_id": d.item_id,
                    "design_value": d.design_value,
                    "manufacturing_value": d.manufacturing_value,
                    "operational_value": d.operational_value,
                    "discrepancy_type": d.discrepancy_type,
                }
                for d in self.discrepancies
            ],
            "reconciliation_suggestions": self.reconciliation_suggestions,
        }


class ThreeViewConfigPropagationService:

    def __init__(self) -> None:
        self._mfg_rules: list[ManufacturingRule] = []
        self._op_rules: list[OperationalRule] = []
        self._propagation_log: list[PropagationResult] = []

    def registerManufacturingRule(self, rule: ManufacturingRule) -> None:
        self._mfg_rules.append(rule)
        self._mfg_rules.sort(key=lambda r: r.priority, reverse=True)

    def registerOperationalRule(self, rule: OperationalRule) -> None:
        self._op_rules.append(rule)
        self._op_rules.sort(key=lambda r: r.priority, reverse=True)

    def deriveManufacturingConfig(
        self, design_config: DesignConfiguration, rules: Optional[list[ManufacturingRule]] = None
    ) -> ManufacturingConfiguration:
        applied_rules = rules if rules else self._mfg_rules
        mfg_items = list(design_config.configuration_items)

        for rule in applied_rules:
            mfg_items = rule.apply(mfg_items)

        return ManufacturingConfiguration(
            config_id=f"MC-{design_config.config_id}",
            source_design_config_id=design_config.config_id,
            manufacturing_rules_applied=[r.rule_id for r in applied_rules],
            configuration_items=mfg_items,
            version=design_config.version,
            status="Active",
        )

    def deriveOperationalConfig(
        self, mfg_config: ManufacturingConfiguration, rules: Optional[list[OperationalRule]] = None
    ) -> OperationalConfiguration:
        applied_rules = rules if rules else self._op_rules
        op_items = list(mfg_config.configuration_items)

        for rule in applied_rules:
            op_items = rule.apply(op_items)

        return OperationalConfiguration(
            config_id=f"OC-{mfg_config.config_id}",
            source_mfg_config_id=mfg_config.config_id,
            operational_rules_applied=[r.rule_id for r in applied_rules],
            configuration_items=op_items,
            version=mfg_config.version,
            status="Active",
        )

    def propagateDesignChange(
        self, block: BlockConfiguration, change: DesignConfigChange
    ) -> PropagationResult:
        start = time.monotonic()

        if not block.design_config:
            return PropagationResult(
                design_updated=False,
                manufacturing_updated=False,
                operational_updated=False,
            )

        for change_item in change.changed_items:
            item_id = change_item.get("item_id")
            new_values = change_item.get("new_values", {})
            for item in block.design_config.configuration_items:
                if item.item_id == item_id:
                    item.value.update(new_values)
                    item.version += 1
                    break

        design_updated = True
        manufacturing_updated = False
        operational_updated = False
        manual_resolution_needed = []

        if block.design_config:
            new_mfg = self.deriveManufacturingConfig(block.design_config)
            block.manufacturing_config = new_mfg
            manufacturing_updated = True

        if block.manufacturing_config:
            new_op = self.deriveOperationalConfig(block.manufacturing_config)
            block.operational_config = new_op
            operational_updated = True

        elapsed_ms = (time.monotonic() - start) * 1000.0

        result = PropagationResult(
            design_updated=design_updated,
            manufacturing_updated=manufacturing_updated,
            operational_updated=operational_updated,
            manual_resolution_needed=manual_resolution_needed,
            propagation_duration_ms=elapsed_ms,
        )
        self._propagation_log.append(result)
        return result

    def detectInconsistencies(
        self, block: BlockConfiguration
    ) -> ReconciliationReport:
        report = ReconciliationReport(config_id=block.block_id)

        if not block.design_config or not block.manufacturing_config or not block.operational_config:
            report.reconciliation_suggestions.append(
                "All three configuration views must exist for inconsistency detection"
            )
            return report

        design_items = {
            i.item_id: i for i in block.design_config.configuration_items
        }
        mfg_items = {
            i.item_id: i for i in block.manufacturing_config.configuration_items
        }
        op_items = {
            i.item_id: i for i in block.operational_config.configuration_items
        }

        all_item_ids = set(design_items.keys()) | set(mfg_items.keys()) | set(op_items.keys())

        for item_id in all_item_ids:
            d_val = design_items[item_id].value if item_id in design_items else None
            m_val = mfg_items[item_id].value if item_id in mfg_items else None
            o_val = op_items[item_id].value if item_id in op_items else None

            if d_val is None or m_val is None or o_val is None:
                report.discrepancies.append(
                    DiscrepancyEntry(
                        item_id=item_id,
                        design_value=d_val,
                        manufacturing_value=m_val,
                        operational_value=o_val,
                        discrepancy_type="MissingItem",
                    )
                )
                report.reconciliation_suggestions.append(
                    f"Item {item_id} missing in one or more views"
                )
            elif d_val != m_val or m_val != o_val:
                core_keys = set(d_val.keys()) & set(m_val.keys()) & set(o_val.keys())
                has_core_diff = any(
                    d_val.get(k) != m_val.get(k) or m_val.get(k) != o_val.get(k)
                    for k in core_keys
                )
                if has_core_diff:
                    report.discrepancies.append(
                        DiscrepancyEntry(
                            item_id=item_id,
                            design_value=d_val,
                            manufacturing_value=m_val,
                            operational_value=o_val,
                            discrepancy_type="ValueMismatch",
                        )
                    )
                    report.reconciliation_suggestions.append(
                        f"Item {item_id} has value mismatch across views"
                    )

        return report