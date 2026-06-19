import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'services', 'plm-center'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'services', 'bom-center'))

from src.domain.entities.plm_entities import (
    DesignObject, DesignBaseline, EngineeringChangeRequest,
    EngineeringChangeOrder, EngineeringChangeNotice,
)
from src.domain.services.plm_services import (
    VersionManagementService, BaselineManagementService, ChangeManagementService,
)
from src.domain.entities.bom_entities import EBOM, MBOM, SBOM, BOMLine
from src.domain.services.bom_services import EBOMService, BOMTransformService, BOMSyncService


class TestDesignObject:
    def test_create_object(self):
        obj = DesignObject(object_number="DO-001", object_type="part", object_name="Wing Spar")
        assert obj.object_number == "DO-001"
        assert obj.current_version == 1

    def test_create_version(self):
        obj = DesignObject(object_number="DO-001", object_type="part", object_name="Wing Spar")
        v = obj.create_version(change_summary="Updated dimensions", author_id="u1")
        assert v["version_number"] == 1
        assert obj.current_version == 2

    def test_get_versions(self):
        obj = DesignObject(object_number="DO-001", object_type="part", object_name="Wing Spar")
        obj.create_version("v1")
        obj.create_version("v2")
        assert len(obj.get_versions()) == 2


class TestDesignBaseline:
    def test_create_baseline(self):
        bl = DesignBaseline(baseline_name="Product Baseline v1.0")
        assert bl.status == "open"

    def test_add_object_version(self):
        bl = DesignBaseline(baseline_name="Test")
        bl.add_object_version("obj-1", 1)
        assert len(bl.object_versions) == 1

    def test_freeze_baseline(self):
        bl = DesignBaseline(baseline_name="Test")
        bl.add_object_version("obj-1", 1)
        bl.freeze("admin")
        assert bl.status == "frozen"

    def test_freeze_empty_raises(self):
        bl = DesignBaseline(baseline_name="Test")
        with pytest.raises(ValueError, match="empty"):
            bl.freeze("admin")

    def test_add_to_frozen_raises(self):
        bl = DesignBaseline(baseline_name="Test")
        bl.add_object_version("obj-1", 1)
        bl.freeze("admin")
        with pytest.raises(ValueError, match="frozen"):
            bl.add_object_version("obj-2", 1)

    def test_unfreeze(self):
        bl = DesignBaseline(baseline_name="Test")
        bl.add_object_version("obj-1", 1)
        bl.freeze("admin")
        bl.unfreeze()
        assert bl.status == "open"


class TestECR:
    def test_create_ecr(self):
        ecr = EngineeringChangeRequest(ecr_number="ECR-001", change_type="engineering_change", title="Wing span increase", description="Increase to 2.6m")
        assert ecr.approval_status == "draft"

    def test_submit_ecr(self):
        ecr = EngineeringChangeRequest(ecr_number="ECR-001", change_type="engineering_change", title="Test", description="Test")
        ecr.submit()
        assert ecr.approval_status == "submitted"

    def test_approve_ecr(self):
        ecr = EngineeringChangeRequest(ecr_number="ECR-001", change_type="engineering_change", title="Test", description="Test")
        ecr.submit()
        ecr.review()
        ecr.approve("approver1")
        assert ecr.approval_status == "approved"

    def test_safety_critical_auto_upgrade(self):
        ecr = EngineeringChangeRequest(ecr_number="ECR-001", change_type="safety_mandated", title="Test", description="Test", safety_critical=True, priority="medium")
        ecr.submit()
        ecr.review()
        ecr.approve("approver1")
        assert ecr.priority == "high"

    def test_reject_ecr(self):
        ecr = EngineeringChangeRequest(ecr_number="ECR-001", change_type="engineering_change", title="Test", description="Test")
        ecr.submit()
        ecr.reject()
        assert ecr.approval_status == "rejected"

    def test_analyze_impact(self):
        ecr = EngineeringChangeRequest(ecr_number="ECR-001", change_type="engineering_change", title="Test", description="Test")
        result = ecr.analyze_impact([{"type": "part", "name": "Wing"}])
        assert result["bom_impact"] is True


class TestVersionManagementService:
    def test_create_and_get_object(self):
        svc = VersionManagementService()
        obj = svc.create_object("DO-001", "part", "Wing Spar")
        assert svc.get_object(obj.object_id) is not None

    def test_create_version(self):
        svc = VersionManagementService()
        obj = svc.create_object("DO-001", "part", "Wing Spar")
        v = svc.create_version(obj.object_id, "Updated")
        assert v["change_summary"] == "Updated"


class TestChangeManagementService:
    def test_full_ecr_flow(self):
        svc = ChangeManagementService()
        ecr = svc.create_ecr("ECR-001", "engineering_change", "Wing span increase", "Increase to 2.6m")
        ecr.submit()
        ecr.review()
        svc.approve_ecr(ecr.ecr_id, "approver1")
        eco = svc.create_eco(ecr.ecr_id, "ECO-001")
        ecn = svc.create_ecn(eco.eco_id, "ECN-001")
        assert ecr.approval_status == "approved"
        assert eco.eco_number == "ECO-001"
        assert ecn.ecn_number == "ECN-001"

    def test_create_eco_without_approval_raises(self):
        svc = ChangeManagementService()
        ecr = svc.create_ecr("ECR-001", "engineering_change", "Test", "Test")
        with pytest.raises(ValueError, match="approved"):
            svc.create_eco(ecr.ecr_id, "ECO-001")


class TestEBOM:
    def test_create_ebom(self):
        ebom = EBOM(bom_number="EBOM-001", product_id="prod-1")
        assert ebom.bom_number == "EBOM-001"
        assert ebom.status == "draft"

    def test_add_line(self):
        ebom = EBOM(bom_number="EBOM-001", product_id="prod-1")
        ebom.add_line(BOMLine(part_number="P-001", part_name="Wing Spar", quantity=2))
        assert len(ebom.lines) == 1

    def test_remove_line(self):
        ebom = EBOM(bom_number="EBOM-001", product_id="prod-1")
        line = BOMLine(part_number="P-001", part_name="Wing Spar")
        ebom.add_line(line)
        ebom.remove_line(line.line_id)
        assert len(ebom.lines) == 0


class TestEBOMService:
    def test_generate_ebom(self):
        svc = EBOMService()
        ebom = svc.generate_ebom("EBOM-001", "prod-1", [
            {"part_number": "P-001", "part_name": "Wing Spar", "quantity": 2},
            {"part_number": "P-002", "part_name": "Rib", "quantity": 10},
        ])
        assert ebom.bom_number == "EBOM-001"
        assert len(ebom.lines) == 2

    def test_get_ebom_tree(self):
        svc = EBOMService()
        ebom = svc.generate_ebom("EBOM-001", "prod-1", [{"part_number": "P-001", "part_name": "Wing Spar"}])
        tree = svc.get_ebom_tree(ebom.bom_id)
        assert len(tree) == 1


class TestBOMTransformService:
    def test_transform_to_mbom(self):
        ebom_svc = EBOMService()
        transform_svc = BOMTransformService(ebom_svc)
        ebom = ebom_svc.generate_ebom("EBOM-001", "prod-1", [{"part_number": "P-001", "part_name": "Wing Spar", "quantity": 2}])
        ebom.status = "released"
        mbom = transform_svc.transform_to_mbom(ebom.bom_id, "MBOM-001")
        assert mbom.ebom_ref == ebom.bom_id
        assert len(mbom.lines) == 1

    def test_transform_to_sbom(self):
        ebom_svc = EBOMService()
        transform_svc = BOMTransformService(ebom_svc)
        ebom = ebom_svc.generate_ebom("EBOM-001", "prod-1", [{"part_number": "P-001", "part_name": "Wing Spar"}])
        sbom = transform_svc.transform_to_sbom(ebom.bom_id, "SBOM-001")
        assert sbom.ebom_ref == ebom.bom_id


class TestBOMSyncService:
    def test_detect_differences(self):
        ebom_svc = EBOMService()
        transform_svc = BOMTransformService(ebom_svc)
        sync_svc = BOMSyncService(ebom_svc, transform_svc)
        ebom = ebom_svc.generate_ebom("EBOM-001", "prod-1", [{"part_number": "P-001", "part_name": "Wing Spar", "quantity": 2}])
        ebom.status = "released"
        mbom = transform_svc.transform_to_mbom(ebom.bom_id, "MBOM-001")
        ebom.add_line(BOMLine(part_number="P-002", part_name="Rib", quantity=10))
        diffs = sync_svc.detect_differences(ebom.bom_id, "mbom", mbom.bom_id)
        assert len(diffs) >= 1

    def test_sync_bom(self):
        ebom_svc = EBOMService()
        transform_svc = BOMTransformService(ebom_svc)
        sync_svc = BOMSyncService(ebom_svc, transform_svc)
        ebom = ebom_svc.generate_ebom("EBOM-001", "prod-1", [{"part_number": "P-001", "part_name": "Wing Spar"}])
        ebom.status = "released"
        mbom = transform_svc.transform_to_mbom(ebom.bom_id, "MBOM-001")
        result = sync_svc.sync_bom(ebom.bom_id, "mbom", mbom.bom_id)
        assert result["status"] == "synced"