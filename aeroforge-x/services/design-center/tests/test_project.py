import pytest

from services.design_center.src.domain.entities.project import (
    Project, ProjectStatus, AircraftType, ProjectMemberRole, ProjectSettings,
)
from services.design_center.src.domain.services.project_domain_service import ProjectDomainService


class TestProjectEntity:
    def test_create_project(self) -> None:
        project = Project(name="AAF-001", code="aaf-001", tenant_id="t-001", aircraft_type=AircraftType.FIXED_WING)
        assert project.name == "AAF-001"
        assert project.status == ProjectStatus.PLANNING

    def test_activate_project(self) -> None:
        project = Project(name="Test", code="test", tenant_id="t-001")
        project.activate()
        assert project.status == ProjectStatus.ACTIVE
        assert len(project.domain_events) == 1

    def test_cannot_activate_archived(self) -> None:
        project = Project(name="Test", code="test", tenant_id="t-001", status=ProjectStatus.ARCHIVED)
        with pytest.raises(ValueError):
            project.activate()

    def test_put_on_hold(self) -> None:
        project = Project(name="Test", code="test", tenant_id="t-001", status=ProjectStatus.ACTIVE)
        project.put_on_hold("testing")
        assert project.status == ProjectStatus.ON_HOLD

    def test_complete_project(self) -> None:
        project = Project(name="Test", code="test", tenant_id="t-001", status=ProjectStatus.ACTIVE)
        project.complete()
        assert project.status == ProjectStatus.COMPLETED

    def test_archive_project(self) -> None:
        project = Project(name="Test", code="test", tenant_id="t-001", status=ProjectStatus.COMPLETED)
        project.archive()
        assert project.status == ProjectStatus.ARCHIVED

    def test_cannot_archive_active(self) -> None:
        project = Project(name="Test", code="test", tenant_id="t-001", status=ProjectStatus.ACTIVE)
        with pytest.raises(ValueError, match="Cannot archive"):
            project.archive()

    def test_add_member(self) -> None:
        project = Project(name="Test", code="test", tenant_id="t-001")
        project.add_member("user-1", ProjectMemberRole.OWNER)
        assert len(project.members) == 1
        assert project.members[0].role == ProjectMemberRole.OWNER

    def test_add_duplicate_member_fails(self) -> None:
        project = Project(name="Test", code="test", tenant_id="t-001")
        project.add_member("user-1", ProjectMemberRole.MEMBER)
        with pytest.raises(ValueError, match="already a member"):
            project.add_member("user-1", ProjectMemberRole.LEAD)

    def test_remove_member(self) -> None:
        project = Project(name="Test", code="test", tenant_id="t-001")
        project.add_member("user-1", ProjectMemberRole.OWNER)
        project.add_member("user-2", ProjectMemberRole.MEMBER)
        project.remove_member("user-2")
        assert len(project.members) == 1

    def test_cannot_remove_last_owner(self) -> None:
        project = Project(name="Test", code="test", tenant_id="t-001")
        project.add_member("user-1", ProjectMemberRole.OWNER)
        with pytest.raises(ValueError, match="last owner"):
            project.remove_member("user-1")

    def test_check_access(self) -> None:
        project = Project(name="Test", code="test", tenant_id="t-001")
        project.add_member("user-1", ProjectMemberRole.OWNER)
        project.add_member("user-2", ProjectMemberRole.MEMBER)
        assert project.check_access("user-1", ProjectMemberRole.LEAD) is True
        assert project.check_access("user-2", ProjectMemberRole.LEAD) is False
        assert project.check_access("user-3") is False

    def test_update_settings(self) -> None:
        project = Project(name="Test", code="test", tenant_id="t-001")
        project.update_settings({"design_rule_set": "military", "design_margin": 2.0})
        assert project.settings.design_rule_set == "military"
        assert project.settings.design_margin == 2.0


class TestProjectDomainService:
    def test_create_project(self) -> None:
        service = ProjectDomainService()
        project = service.create_project("AAF-001", "aaf-001", "t-001", AircraftType.FIXED_WING, created_by="chief-1")
        assert project.name == "AAF-001"
        assert len(project.members) == 1
        assert project.members[0].role == ProjectMemberRole.OWNER

    def test_duplicate_code_in_tenant(self) -> None:
        service = ProjectDomainService()
        service.create_project("P1", "aaf-001", "t-001")
        with pytest.raises(ValueError, match="already exists"):
            service.create_project("P2", "aaf-001", "t-001")

    def test_same_code_different_tenant(self) -> None:
        service = ProjectDomainService()
        p1 = service.create_project("P1", "aaf-001", "t-001")
        p2 = service.create_project("P2", "aaf-001", "t-002")
        assert p1.id != p2.id

    def test_list_projects_by_tenant(self) -> None:
        service = ProjectDomainService()
        service.create_project("P1", "p1", "t-001")
        service.create_project("P2", "p2", "t-001")
        service.create_project("P3", "p3", "t-002")
        assert len(service.list_projects("t-001")) == 2
        assert len(service.list_projects("t-002")) == 1

    def test_list_projects_by_status(self) -> None:
        service = ProjectDomainService()
        p1 = service.create_project("P1", "p1", "t-001")
        service.create_project("P2", "p2", "t-001")
        service.activate_project(p1.id)
        active = service.list_projects("t-001", status=ProjectStatus.ACTIVE)
        assert len(active) == 1

    def test_add_and_remove_member(self) -> None:
        service = ProjectDomainService()
        project = service.create_project("P1", "p1", "t-001", created_by="chief-1")
        service.add_project_member(project.id, "eng-1", "member")
        assert len(service.get_project(project.id).members) == 2

        service.remove_project_member(project.id, "eng-1")
        assert len(service.get_project(project.id).members) == 1

    def test_check_project_access(self) -> None:
        service = ProjectDomainService()
        project = service.create_project("P1", "p1", "t-001", created_by="chief-1")
        assert service.check_project_access(project.id, "chief-1", "owner") is True
        assert service.check_project_access(project.id, "unknown-user") is False

    def test_update_project(self) -> None:
        service = ProjectDomainService()
        project = service.create_project("P1", "p1", "t-001")
        updated = service.update_project(project.id, name="Updated P1")
        assert updated.name == "Updated P1"

    def test_update_project_settings(self) -> None:
        service = ProjectDomainService()
        project = service.create_project("P1", "p1", "t-001")
        service.update_project_settings(project.id, {"design_margin": 2.5})
        assert service.get_project(project.id).settings.design_margin == 2.5