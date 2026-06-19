"""AeroForge-X v6.0 MaterialLotTrackerService

Manages material lot traceability: "ore to part" tracking,
forward/backward traceability, non-conforming lot handling,
and genealogy recording.
REQ-SUP-007~012
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LotStatus(str, Enum):
    RECEIVED = "Received"
    IN_PROCESS = "InProcess"
    INSTALLED = "Installed"
    NON_CONFORMING = "NonConforming"


class TransformationType(str, Enum):
    INGOT_TO_BILLET = "IngotToBillet"
    BILLET_TO_FORGING = "BilletToForging"
    FORGING_TO_MACHINED_PART = "ForgingToMachinedPart"
    RAW_TO_SEMI_FINISHED = "RawToSemiFinished"
    SEMI_FINISHED_TO_FINISHED = "SemiFinishedToFinished"


@dataclass
class GenealogyStep:
    step_id: str
    lot_id: str
    transformation_type: TransformationType
    process_parameters: dict = field(default_factory=dict)
    output_lot_id: str = ""
    performed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "lot_id": self.lot_id,
            "transformation_type": self.transformation_type.value,
            "process_parameters": self.process_parameters,
            "output_lot_id": self.output_lot_id,
            "performed_at": self.performed_at,
        }


@dataclass
class MaterialLot:
    lot_id: str
    supplier_id: str
    material_specification: str
    heat_number: str
    certificate_of_conformance: str = ""
    test_results: dict = field(default_factory=dict)
    processing_history: list[GenealogyStep] = field(default_factory=list)
    status: LotStatus = LotStatus.RECEIVED
    installed_parts: list[str] = field(default_factory=list)
    installed_aircraft: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lot_id": self.lot_id,
            "supplier_id": self.supplier_id,
            "material_specification": self.material_specification,
            "heat_number": self.heat_number,
            "certificate_of_conformance": self.certificate_of_conformance,
            "test_results": self.test_results,
            "status": self.status.value,
            "installed_parts": self.installed_parts,
            "installed_aircraft": self.installed_aircraft,
        }


@dataclass
class ForwardTraceResult:
    lot_id: str
    affected_parts: list[str] = field(default_factory=list)
    affected_aircraft: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lot_id": self.lot_id,
            "affected_parts": self.affected_parts,
            "affected_aircraft": self.affected_aircraft,
        }


@dataclass
class BackwardTraceResult:
    part_serial_id: str
    material_lot: Optional[MaterialLot] = None
    supplier_id: str = ""
    certification_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "part_serial_id": self.part_serial_id,
            "material_lot": self.material_lot.to_dict() if self.material_lot else None,
            "supplier_id": self.supplier_id,
            "certification_data": self.certification_data,
        }


@dataclass
class ContainmentActionResult:
    lot_id: str
    affected_parts_count: int
    affected_aircraft: list[str] = field(default_factory=list)
    containment_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lot_id": self.lot_id,
            "affected_parts_count": self.affected_parts_count,
            "affected_aircraft": self.affected_aircraft,
            "containment_actions": self.containment_actions,
        }


class MaterialLotTrackerService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._lots: dict[str, MaterialLot] = {}
        self._part_to_lot: dict[str, str] = {}
        self._genealogy: dict[str, list[GenealogyStep]] = {}

    def _persist_lot(self, lot: MaterialLot) -> None:
        if self._repo is None:
            return
        self._repo.save_lot(lot.to_dict())

    def receiveMaterialLot(self, lot_data: MaterialLot) -> MaterialLot:
        if lot_data.lot_id in self._lots:
            raise ValueError(f"Material lot already exists: {lot_data.lot_id}")

        self._lots[lot_data.lot_id] = lot_data
        self._genealogy[lot_data.lot_id] = []
        self._persist_lot(lot_data)
        return lot_data

    def forwardTraceability(self, lot_id: str) -> ForwardTraceResult:
        if lot_id not in self._lots:
            raise ValueError(f"Material lot not found: {lot_id}")

        lot = self._lots[lot_id]
        affected_parts = list(lot.installed_parts)
        affected_aircraft = list(lot.installed_aircraft)

        for step in self._genealogy.get(lot_id, []):
            if step.output_lot_id and step.output_lot_id in self._lots:
                derived = self._lots[step.output_lot_id]
                affected_parts.extend(derived.installed_parts)
                affected_aircraft.extend(derived.installed_aircraft)

        return ForwardTraceResult(
            lot_id=lot_id,
            affected_parts=list(set(affected_parts)),
            affected_aircraft=list(set(affected_aircraft)),
        )

    def backwardTraceability(self, part_serial_id: str) -> BackwardTraceResult:
        if part_serial_id not in self._part_to_lot:
            return BackwardTraceResult(part_serial_id=part_serial_id)

        lot_id = self._part_to_lot[part_serial_id]
        lot = self._lots.get(lot_id)

        source_lot_id = lot_id
        for step in self._genealogy.get(lot_id, []):
            if step.lot_id and step.lot_id in self._lots:
                source_lot_id = step.lot_id
                break

        source_lot = self._lots.get(source_lot_id, lot)

        return BackwardTraceResult(
            part_serial_id=part_serial_id,
            material_lot=source_lot,
            supplier_id=source_lot.supplier_id if source_lot else "",
            certification_data={
                "heat_number": source_lot.heat_number if source_lot else "",
                "certificate_of_conformance": source_lot.certificate_of_conformance if source_lot else "",
                "test_results": source_lot.test_results if source_lot else {},
            },
        )

    def flagNonConformingLot(self, lot_id: str) -> ContainmentActionResult:
        if lot_id not in self._lots:
            raise ValueError(f"Material lot not found: {lot_id}")

        lot = self._lots[lot_id]
        lot.status = LotStatus.NON_CONFORMING

        forward = self.forwardTraceability(lot_id)

        actions = [
            "Quarantine all affected parts",
            "Notify quality engineering",
            "Initiate containment inspection",
        ]
        if forward.affected_aircraft:
            actions.append(
                f"Assess impact on {len(forward.affected_aircraft)} affected aircraft"
            )

        return ContainmentActionResult(
            lot_id=lot_id,
            affected_parts_count=len(forward.affected_parts),
            affected_aircraft=forward.affected_aircraft,
            containment_actions=actions,
        )

    def recordGenealogyStep(self, step: GenealogyStep) -> GenealogyStep:
        if step.lot_id not in self._lots:
            raise ValueError(f"Material lot not found: {step.lot_id}")

        step.step_id = f"GEN-{uuid.uuid4().hex[:8]}"
        self._genealogy[step.lot_id].append(step)

        if step.output_lot_id and step.output_lot_id in self._lots:
            self._lots[step.output_lot_id].status = LotStatus.IN_PROCESS

        return step

    def registerPartInstallation(
        self, lot_id: str, part_serial_id: str, aircraft_tail: str
    ) -> None:
        if lot_id not in self._lots:
            raise ValueError(f"Material lot not found: {lot_id}")

        lot = self._lots[lot_id]
        if part_serial_id not in lot.installed_parts:
            lot.installed_parts.append(part_serial_id)
        if aircraft_tail not in lot.installed_aircraft:
            lot.installed_aircraft.append(aircraft_tail)
        lot.status = LotStatus.INSTALLED

        self._part_to_lot[part_serial_id] = lot_id

    def getLot(self, lot_id: str) -> Optional[MaterialLot]:
        return self._lots.get(lot_id)