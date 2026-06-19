"""AeroForge-X V6.0/V6.1 Unit Tests - ShopFloorEventEmitterService
REQ-FACTORY-019~022, REQ-VP-020
"""

import time

import pytest

from src.domain.services.digital_factory.shop_floor_event_emitter_service import (
    ShopFloorEventEmitterService,
    ShopFloorEventType,
    ShopFloorEvent,
    EventReceipt,
    EventFilter,
)


@pytest.fixture
def service():
    return ShopFloorEventEmitterService()


class TestEmitEquipmentStatusChange:

    def test_emit_equipment_status(self, service):
        result = service.emitEquipmentStatusChange("EQ-001", "Online")
        assert isinstance(result, EventReceipt)
        assert result.published is True
        assert result.subject == "aeroforge.v6.factory.equipment.status"

    def test_emit_records_event(self, service):
        service.emitEquipmentStatusChange("EQ-001", "Online")
        assert len(service._events) == 1


class TestEmitOperationEvent:

    def test_emit_operation_start(self, service):
        result = service.emitOperationEvent("OP-001", "start")
        assert result.published is True
        assert result.subject == "aeroforge.v6.factory.operation.complete"

    def test_emit_operation_complete(self, service):
        result = service.emitOperationEvent("OP-001", "complete")
        assert result.published is True


class TestEmitQualityAlert:

    def test_emit_quality_alert(self, service):
        result = service.emitQualityAlert("EQ-001", {"defect": "Crack", "severity": "High"})
        assert result.published is True
        assert result.subject == "aeroforge.v6.factory.quality.alert"


class TestEmitDeviationAlert:

    def test_emit_deviation_alert(self, service):
        result = service.emitDeviationAlert("EQ-001", {"parameter": "temp", "deviation": 15.0})
        assert result.published is True
        assert result.subject == "aeroforge.v6.factory.deviation.alert"


class TestPlaybackEvents:

    def test_playback_all_events(self, service):
        service.emitEquipmentStatusChange("EQ-001", "Online")
        service.emitQualityAlert("EQ-001", {"defect": "Crack"})
        events = service.playbackEvents(EventFilter())
        assert len(events) == 2

    def test_playback_filter_by_type(self, service):
        service.emitEquipmentStatusChange("EQ-001", "Online")
        service.emitQualityAlert("EQ-001", {"defect": "Crack"})
        events = service.playbackEvents(EventFilter(event_type=ShopFloorEventType.QUALITY_ALERT))
        assert len(events) == 1
        assert events[0].event_type == ShopFloorEventType.QUALITY_ALERT

    def test_playback_filter_by_equipment(self, service):
        service.emitEquipmentStatusChange("EQ-001", "Online")
        service.emitEquipmentStatusChange("EQ-002", "Offline")
        events = service.playbackEvents(EventFilter(source_equipment_id="EQ-001"))
        assert len(events) == 1

    def test_playback_empty_result(self, service):
        service.emitEquipmentStatusChange("EQ-001", "Online")
        events = service.playbackEvents(EventFilter(event_type=ShopFloorEventType.DEVIATION_ALERT))
        assert len(events) == 0