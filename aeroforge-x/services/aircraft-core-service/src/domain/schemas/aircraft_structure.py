from __future__ import annotations

from pydantic import Field, model_validator

from src.domain.schemas.base import AircraftSchemaBase


class MaterialProperties(AircraftSchemaBase):
    density: float = Field(gt=0, description="Material density in kg/m³")
    yield_strength: float = Field(gt=0, description="Yield strength in MPa")
    ultimate_strength: float = Field(gt=0, description="Ultimate tensile strength in MPa")
    elastic_modulus: float = Field(gt=0, description="Elastic modulus (Young's) in GPa")
    poisson_ratio: float = Field(ge=0, le=0.5, description="Poisson's ratio")
    thermal_expansion_coefficient: float = Field(default=0.0, description="CTE in 1e-6/°C")

    @model_validator(mode="after")
    def validate_strength_ordering(self) -> MaterialProperties:
        if self.ultimate_strength < self.yield_strength:
            raise ValueError("ultimate_strength must be >= yield_strength")
        return self


class AircraftStructure(AircraftSchemaBase):
    material_id: str = Field(min_length=1, description="Material identifier reference")
    material_density: float = Field(gt=0, description="Material density in kg/m³")
    yield_strength: float = Field(gt=0, description="Yield strength in MPa")
    ultimate_strength: float = Field(gt=0, description="Ultimate tensile strength in MPa")
    elastic_modulus: float = Field(gt=0, description="Elastic modulus in GPa")
    design_weight: float = Field(gt=0, description="Design weight in kg")
    manufacturing_weight: float = Field(default=0.0, ge=0, description="As-manufactured weight in kg")
    weight_margin: float = Field(default=0.0, description="Weight margin (design - actual) in kg")
    spar_cross_section: str = Field(default="I-beam", description="Spar cross-section type")
    rib_spacing: float = Field(gt=0, description="Rib spacing in meters")
    skin_thickness: float = Field(gt=0, description="Skin thickness in mm")
    geometry_ref: str | None = Field(default=None, description="Reference to AircraftGeometry schema instance ID")

    material_properties: MaterialProperties | None = Field(default=None, description="Full material properties")

    @model_validator(mode="after")
    def compute_weight_margin(self) -> AircraftStructure:
        if self.manufacturing_weight > 0:
            self.weight_margin = round(self.design_weight - self.manufacturing_weight, 4)
        return self

    @model_validator(mode="after")
    def validate_material_reference(self) -> AircraftStructure:
        if self.material_properties is not None:
            if abs(self.material_properties.density - self.material_density) > 1.0:
                raise ValueError("material_density does not match material_properties.density")
            if abs(self.material_properties.yield_strength - self.yield_strength) > 1.0:
                raise ValueError("yield_strength does not match material_properties.yield_strength")
        return self

    @model_validator(mode="after")
    def check_weight_margin(self) -> AircraftStructure:
        if self.manufacturing_weight > 0 and self.weight_margin < 0:
            import warnings
            warnings.warn(f"Weight margin is negative: {self.weight_margin} kg (overweight)", stacklevel=2)
        return self