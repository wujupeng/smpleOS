from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from src.domain.entities.audit_log import AuditAction, AuditDetail, AuditLog, AuditResource
from src.domain.services.audit_domain_service import AuditDomainService, AuditQueryFilter


class TestAuditLogEntity:
    def test_create_audit_log(self):
        log = AuditLog(
            tenant_id="t1",
            user_id="u1",
            action=AuditAction.CREATE,
            resource_type=AuditResource.PROJECT,
            resource_id="p1",
            resource_name="Test Project",
        )
        assert log.tenant_id == "t1"
        assert log.user_id == "u1"
        assert log.action == AuditAction.CREATE
        assert log.resource_type == AuditResource.PROJECT
        assert log.resource_id == "p1"
        assert log.signature != ""
        assert log.timestamp is not None

    def test_verify_integrity_valid(self):
        log = AuditLog(
            tenant_id="t1",
            user_id="u1",
            action=AuditAction.UPDATE,
            resource_type=AuditResource.DESIGN,
            resource_id="d1",
        )
        assert log.verify_integrity() is True

    def test_verify_integrity_tampered(self):
        log = AuditLog(
            tenant_id="t1",
            user_id="u1",
            action=AuditAction.UPDATE,
            resource_type=AuditResource.DESIGN,
            resource_id="d1",
        )
        log.user_id = "u2"
        assert log.verify_integrity() is False

    def test_audit_log_with_details(self):
        details = [
            AuditDetail(field_name="status", old_value="draft", new_value="approved"),
            AuditDetail(field_name="reviewer", old_value=None, new_value="u2"),
        ]
        log = AuditLog(
            tenant_id="t1",
            user_id="u1",
            action=AuditAction.UPDATE,
            resource_type=AuditResource.DESIGN,
            resource_id="d1",
            details=details,
        )
        assert len(log.details) == 2
        data = log.to_dict()
        assert len(data["details"]) == 2
        assert data["details"][0]["field_name"] == "status"

    def test_audit_log_to_dict(self):
        log = AuditLog(
            tenant_id="t1",
            user_id="u1",
            action=AuditAction.LOGIN,
            resource_type=AuditResource.USER,
            resource_id="u1",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        data = log.to_dict()
        assert data["tenant_id"] == "t1"
        assert data["action"] == "login"
        assert data["ip_address"] == "192.168.1.1"
        assert "chain_previous" in data
        assert "chain_hash" in data


class TestAuditDomainService:
    def setup_method(self):
        self.service = AuditDomainService()

    def test_record_audit(self):
        log = self.service.record(
            tenant_id="t1",
            user_id="u1",
            action=AuditAction.CREATE,
            resource_type=AuditResource.PROJECT,
            resource_id="p1",
        )
        assert log.tenant_id == "t1"
        assert log.chain_hash != ""
        assert log.chain_previous != "" or log.chain_previous == ""

    def test_query_by_tenant(self):
        self.service.record("t1", "u1", AuditAction.CREATE, AuditResource.PROJECT, "p1")
        self.service.record("t2", "u2", AuditAction.CREATE, AuditResource.PROJECT, "p2")

        result = self.service.query(AuditQueryFilter(tenant_id="t1"))
        assert result["total"] == 1
        assert result["logs"][0]["tenant_id"] == "t1"

    def test_query_by_action(self):
        self.service.record("t1", "u1", AuditAction.CREATE, AuditResource.PROJECT, "p1")
        self.service.record("t1", "u1", AuditAction.UPDATE, AuditResource.PROJECT, "p1")

        result = self.service.query(AuditQueryFilter(action=AuditAction.CREATE))
        assert result["total"] == 1

    def test_query_pagination(self):
        for i in range(10):
            self.service.record("t1", "u1", AuditAction.CREATE, AuditResource.PROJECT, f"p{i}")

        result = self.service.query(AuditQueryFilter(page=1, page_size=3))
        assert result["total"] == 10
        assert len(result["logs"]) == 3
        assert result["page"] == 1

    def test_verify_chain_integrity(self):
        self.service.record("t1", "u1", AuditAction.CREATE, AuditResource.PROJECT, "p1")
        self.service.record("t1", "u1", AuditAction.UPDATE, AuditResource.PROJECT, "p1")

        result = self.service.verify_chain_integrity("t1")
        assert result["verified"] is True
        assert result["total_logs"] == 2

    def test_export_csv(self):
        self.service.record("t1", "u1", AuditAction.CREATE, AuditResource.PROJECT, "p1")
        csv_content = self.service.export_csv(AuditQueryFilter(tenant_id="t1"))
        assert "tenant_id" in csv_content
        assert "t1" in csv_content

    def test_export_json(self):
        self.service.record("t1", "u1", AuditAction.CREATE, AuditResource.PROJECT, "p1")
        json_content = self.service.export_json(AuditQueryFilter(tenant_id="t1"))
        data = json.loads(json_content)
        assert data["total"] == 1

    def test_get_statistics(self):
        self.service.record("t1", "u1", AuditAction.CREATE, AuditResource.PROJECT, "p1")
        self.service.record("t1", "u1", AuditAction.UPDATE, AuditResource.PROJECT, "p1")
        self.service.record("t1", "u2", AuditAction.DELETE, AuditResource.DESIGN, "d1")

        stats = self.service.get_statistics("t1")
        assert stats["total_logs"] == 3
        assert stats["action_counts"]["create"] == 1
        assert stats["action_counts"]["update"] == 1
        assert stats["action_counts"]["delete"] == 1