import pytest

from aeroforge_common.domain.base import AggregateRoot, DomainEvent, Entity, ValueObject


class TestEntity:
    def test_entity_generates_uuid_id(self) -> None:
        entity = Entity()
        assert entity.id is not None
        assert len(entity.id) == 36

    def test_entity_accepts_custom_id(self) -> None:
        entity = Entity(entity_id="custom-id")
        assert entity.id == "custom-id"

    def test_entities_with_same_id_are_equal(self) -> None:
        e1 = Entity(entity_id="same-id")
        e2 = Entity(entity_id="same-id")
        assert e1 == e2

    def test_entities_with_different_id_are_not_equal(self) -> None:
        e1 = Entity(entity_id="id-1")
        e2 = Entity(entity_id="id-2")
        assert e1 != e2

    def test_entity_hash_based_on_id(self) -> None:
        e1 = Entity(entity_id="same-id")
        e2 = Entity(entity_id="same-id")
        assert hash(e1) == hash(e2)


class TestValueObject:
    def test_value_objects_with_same_attrs_are_equal(self) -> None:
        vo1 = ValueObject()
        vo2 = ValueObject()
        assert vo1 == vo2

    def test_value_object_repr(self) -> None:
        vo = ValueObject()
        assert "ValueObject" in repr(vo)


class TestAggregateRoot:
    def test_aggregate_root_has_empty_events_initially(self) -> None:
        ar = AggregateRoot()
        assert ar.domain_events == []

    def test_add_domain_event(self) -> None:
        ar = AggregateRoot()
        event = DomainEvent(event_type="test.event", aggregate_id=ar.id)
        ar.add_domain_event(event)
        assert len(ar.domain_events) == 1
        assert ar.domain_events[0].event_type == "test.event"

    def test_clear_domain_events(self) -> None:
        ar = AggregateRoot()
        event = DomainEvent(event_type="test.event", aggregate_id=ar.id)
        ar.add_domain_event(event)
        cleared = ar.clear_domain_events()
        assert len(cleared) == 1
        assert ar.domain_events == []


class TestDomainEvent:
    def test_domain_event_creation(self) -> None:
        event = DomainEvent(
            event_type="aircraft.spec.confirmed",
            aggregate_id="spec-123",
            payload={"aircraft_type": "fixed_wing"},
        )
        assert event.event_type == "aircraft.spec.confirmed"
        assert event.aggregate_id == "spec-123"
        assert event.payload["aircraft_type"] == "fixed_wing"
        assert event.occurred_at is not None

    def test_domain_event_to_dict(self) -> None:
        event = DomainEvent(
            event_type="test.event",
            aggregate_id="agg-1",
            payload={"key": "value"},
        )
        d = event.to_dict()
        assert d["event_type"] == "test.event"
        assert d["aggregate_id"] == "agg-1"
        assert d["payload"]["key"] == "value"
        assert "occurred_at" in d