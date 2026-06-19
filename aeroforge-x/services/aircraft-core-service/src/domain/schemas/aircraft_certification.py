from __future__ import annotations

import re

from pydantic import Field, model_validator

from src.domain.schemas.base import AircraftSchemaBase
from src.domain.schemas.enums import ComplianceStatus, ComplianceMethod


class AircraftCertification(AircraftSchemaBase):
    clause_number: str = Field(min_length=1, description="FAR-25 clause number (e.g., 25.341)")
    clause_title: str = Field(min_length=1, description="Clause title/description")
    applicability: str = Field(default="", description="Applicability statement")
    compliance_status: ComplianceStatus = Field(default=ComplianceStatus.NotAssessed, description="Current compliance status")
    compliance_method: ComplianceMethod | None = Field(default=None, description="Means of compliance (MOC)")
    evidence_ref: str | None = Field(default=None, description="Reference to verification evidence document")
    finding_date: str | None = Field(default=None, description="Date of compliance finding (ISO 8601)")
    geometry_ref: str | None = Field(default=None, description="Reference to AircraftGeometry schema instance ID")
    structure_ref: str | None = Field(default=None, description="Reference to AircraftStructure schema instance ID")
    envelope_ref: str | None = Field(default=None, description="Reference to AircraftFlightEnvelope schema instance ID")

    compliance_change_triggered: bool = Field(default=False, description="Whether compliance change triggered review workflow")

    @model_validator(mode="after")
    def validate_clause_format(self) -> AircraftCertification:
        pattern = r"^25\.\d+([a-z]?\d?)*$"
        if not re.match(pattern, self.clause_number):
            raise ValueError(f"Clause number '{self.clause_number}' does not match FAR-25 format (e.g., 25.341)")
        return self

    @model_validator(mode="after")
    def validate_evidence_references(self) -> AircraftCertification:
        if self.compliance_status == ComplianceStatus.Compliant:
            if self.evidence_ref is None or self.evidence_ref == "":
                import warnings
                warnings.warn(f"Clause {self.clause_number} is Compliant but has no evidence reference", stacklevel=2)
        return self

    @model_validator(mode="after")
    def check_compliance_change(self) -> AircraftCertification:
        if self.compliance_status == ComplianceStatus.NonCompliant:
            self.compliance_change_triggered = True
        return self

    @model_validator(mode="after")
    def validate_moc_evidence_association(self) -> AircraftCertification:
        if self.compliance_method == ComplianceMethod.MOC4:
            if self.evidence_ref is None or "flight_test" not in (self.evidence_ref or "").lower():
                import warnings
                warnings.warn(f"MOC4 (Flight Test) for clause {self.clause_number} should reference flight test report", stacklevel=2)
        return self