from __future__ import annotations

import pytest

from src.domain.services.process_route_domain_service import (
    Operation,
    OperationType,
    ProcessRoute,
    ProcessRouteDomainService,
    PROCESS_TEMPLATES,
)


@pytest.fixture
def sample_mbom_data() -> dict:
    return {
        "id": "mbom-001",
        "mbom_code": "AAF-MBOM-001",
        "root_item": {
            "item_code": "MBOM-ROOT",
            "name": "飞行器制造总装",
            "children": [
                {
                    "item_code": "MBOM-WING",
                    "name": "左翼装配组件",
                    "is_virtual": True,
                    "children": [
                        {"item_code": "AAF-SPAR-001", "name": "翼梁", "part_type": "structural", "attributes": {"material": "CFRP"}},
                        {"item_code": "AAF-RIB-001", "name": "肋板", "part_type": "structural"},
                    ],
                },
                {
                    "item_code": "MBOM-FUSE",
                    "name": "机身前段装配组件",
                    "is_virtual": True,
                    "children": [
                        {"item_code": "AAF-FRAME-001", "name": "加强框", "part_type": "structural"},
                    ],
                },
                {
                    "item_code": "MBOM-TAIL",
                    "name": "尾翼装配组件",
                    "is_virtual": True,
                    "children": [
                        {"item_code": "AAF-H-SPAR-001", "name": "水平尾翼梁", "part_type": "structural"},
                    ],
                },
            ],
        },
    }


class TestProcessRouteGeneration:
    def test_generate_from_mbom(self, sample_mbom_data):
        service = ProcessRouteDomainService()
        route = service.generate_from_mbom(sample_mbom_data)

        assert isinstance(route, ProcessRoute)
        assert route.mbom_id == "mbom-001"
        assert len(route.operations) > 0

    def test_operations_have_sequences(self, sample_mbom_data):
        service = ProcessRouteDomainService()
        route = service.generate_from_mbom(sample_mbom_data)

        sequences = [op.sequence for op in route.operations]
        assert sequences == sorted(sequences)

    def test_quality_checkpoints_inserted(self, sample_mbom_data):
        service = ProcessRouteDomainService()
        route = service.generate_from_mbom(sample_mbom_data)

        qc_ops = [op for op in route.operations if op.is_quality_checkpoint]
        assert len(qc_ops) > 0

    def test_equipment_assigned(self, sample_mbom_data):
        service = ProcessRouteDomainService()
        route = service.generate_from_mbom(sample_mbom_data)

        for op in route.operations:
            if op.operation_type in (OperationType.INSPECTION, OperationType.QUALITY_GATE):
                assert op.equipment

    def test_total_hours_calculated(self, sample_mbom_data):
        service = ProcessRouteDomainService()
        route = service.generate_from_mbom(sample_mbom_data)

        expected = sum(op.estimated_hours for op in route.operations)
        assert route.total_estimated_hours == expected

    def test_material_factor_applied(self):
        service = ProcessRouteDomainService()
        mbom_data = {
            "id": "mbom-cfrp",
            "root_item": {
                "item_code": "ROOT",
                "name": "总装",
                "attributes": {"material": "CFRP"},
                "children": [
                    {"item_code": "WING-01", "name": "机翼组件", "children": []},
                ],
            },
        }
        route = service.generate_from_mbom(mbom_data)
        assert route.total_estimated_hours > 0

    def test_empty_mbom_generates_empty_route(self):
        service = ProcessRouteDomainService()
        route = service.generate_from_mbom({"id": "empty", "root_item": {}})
        assert len(route.operations) == 0


class TestProcessRouteOperations:
    def test_add_operation(self):
        route = ProcessRoute(mbom_id="mbom-001")
        op = Operation(
            operation_id="OP-001",
            operation_name="Test Op",
            operation_type=OperationType.ASSEMBLY,
            sequence=1,
            estimated_hours=2.0,
        )
        route.add_operation(op)
        assert len(route.operations) == 1
        assert route.total_estimated_hours == 2.0

    def test_remove_operation(self):
        route = ProcessRoute(mbom_id="mbom-001")
        op = Operation(operation_id="OP-001", operation_name="Test", operation_type=OperationType.ASSEMBLY, sequence=1, estimated_hours=2.0)
        route.add_operation(op)
        assert route.remove_operation("OP-001") is True
        assert len(route.operations) == 0

    def test_publish_route(self):
        route = ProcessRoute(mbom_id="mbom-001")
        op = Operation(operation_id="OP-001", operation_name="Test", operation_type=OperationType.ASSEMBLY, sequence=1)
        route.add_operation(op)
        route.publish()
        assert route.status == "published"

    def test_cannot_publish_empty_route(self):
        route = ProcessRoute(mbom_id="mbom-001")
        with pytest.raises(ValueError, match="Cannot publish empty process route"):
            route.publish()


class TestProcessTemplates:
    def test_all_templates_have_operations(self):
        for key, tmpl in PROCESS_TEMPLATES.items():
            assert len(tmpl["operations"]) > 0, f"Template {key} has no operations"

    def test_template_operations_have_required_fields(self):
        for key, tmpl in PROCESS_TEMPLATES.items():
            for op in tmpl["operations"]:
                assert "name" in op
                assert "type" in op
                assert "hours" in op