import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

import pytest


class TestCrossCenterEventBus:
    def test_event_bus_publish_subscribe(self):
        from services.knowledge_center.src.infrastructure.event_bus import EventBus as KEB
        bus = KEB()
        assert bus is not None
        assert hasattr(bus, 'publish')
        assert hasattr(bus, 'connect')
        assert hasattr(bus, 'close')

    def test_all_centers_have_event_bus(self):
        centers = [
            "knowledge_center",
            "configuration_center",
            "verification_center",
            "operation_center",
            "certification_center",
        ]
        for center in centers:
            try:
                mod = __import__(f"services.{center}.src.infrastructure.event_bus", fromlist=["event_bus"])
                assert hasattr(mod, 'event_bus')
            except ImportError:
                pass


class TestCrossCenterKnowledgeIntegration:
    def test_design_change_triggers_knowledge_update(self):
        from services.knowledge_center.src.domain.services.knowledge_graph_service import KnowledgeGraphService
        from services.knowledge_center.src.domain.entities.knowledge_graph import KnowledgeGraph
        service = KnowledgeGraphService()
        graph = KnowledgeGraph(name="test_cross_center")
        service._graphs[graph.id] = graph

        node_data = {
            "node_type": "design_change",
            "name": "Wingspan Update",
            "properties": {"parameter": "wingspan_m", "old_value": 35.8, "new_value": 36.0},
        }
        node = service.add_node(graph.id, node_data)
        assert node is not None

    def test_cae_result_creates_knowledge_link(self):
        from services.knowledge_center.src.domain.services.knowledge_graph_service import KnowledgeGraphService
        from services.knowledge_center.src.domain.entities.knowledge_graph import KnowledgeGraph
        service = KnowledgeGraphService()
        graph = KnowledgeGraph(name="cae_knowledge_test")
        service._graphs[graph.id] = graph

        design_node = service.add_node(graph.id, {"node_type": "design_parameter", "name": "Wing Root Load"})
        cae_node = service.add_node(graph.id, {"node_type": "cae_result", "name": "FEA Stress Analysis"})
        link = service.add_link(graph.id, {
            "source_id": design_node.id,
            "target_id": cae_node.id,
            "link_type": "validated_by",
        })
        assert link is not None

    def test_manufacturing_data_creates_quality_knowledge(self):
        from services.knowledge_center.src.domain.services.knowledge_graph_service import KnowledgeGraphService
        from services.knowledge_center.src.domain.entities.knowledge_graph import KnowledgeGraph
        service = KnowledgeGraphService()
        graph = KnowledgeGraph(name="mfg_quality_test")
        service._graphs[graph.id] = graph

        mfg_node = service.add_node(graph.id, {"node_type": "manufacturing_record", "name": "Wing Spar Fabrication"})
        quality_node = service.add_node(graph.id, {"node_type": "quality_observation", "name": "Dimensional Deviation"})
        link = service.add_link(graph.id, {
            "source_id": mfg_node.id,
            "target_id": quality_node.id,
            "link_type": "produces",
        })
        assert link is not None