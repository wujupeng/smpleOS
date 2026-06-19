from __future__ import annotations

from typing import Any


class AttributeNameService:

    _canonical_names: dict[str, dict[str, Any]] = {}
    _alias_map: dict[str, str] = {}

    @classmethod
    def register_canonical_name(cls, canonical_name: str, domain: str, description: str = "") -> dict[str, Any]:
        if canonical_name in cls._canonical_names:
            raise ValueError(f"Canonical name '{canonical_name}' already registered")
        if canonical_name in cls._alias_map:
            raise ValueError(f"Canonical name '{canonical_name}' conflicts with existing alias")
        entry = {"canonical_name": canonical_name, "domain": domain, "description": description, "aliases": []}
        cls._canonical_names[canonical_name] = entry
        return entry

    @classmethod
    def add_alias(cls, canonical_name: str, alias: str) -> dict[str, Any]:
        entry = cls._canonical_names.get(canonical_name)
        if entry is None:
            raise ValueError(f"Canonical name '{canonical_name}' not found")
        if alias in cls._alias_map:
            existing = cls._alias_map[alias]
            if existing != canonical_name:
                raise ValueError(f"Alias '{alias}' already mapped to '{existing}'")
            return entry
        if alias in cls._canonical_names:
            raise ValueError(f"Alias '{alias}' conflicts with existing canonical name")
        entry["aliases"].append(alias)
        cls._alias_map[alias] = canonical_name
        return entry

    @classmethod
    def resolve_name(cls, name: str) -> dict[str, Any]:
        if name in cls._canonical_names:
            return {"canonical_name": name, "is_alias": False, "updated": False}
        if name in cls._alias_map:
            canonical = cls._alias_map[name]
            return {"canonical_name": canonical, "is_alias": True, "updated": True, "original": name}
        return {"canonical_name": name, "is_alias": False, "updated": False, "unknown": True}

    @classmethod
    def validate_no_conflict(cls, name: str) -> bool:
        if name in cls._canonical_names:
            return False
        if name in cls._alias_map:
            return False
        return True

    @classmethod
    def get_all_mappings(cls) -> dict[str, list[str]]:
        return {k: v["aliases"] for k, v in cls._canonical_names.items()}


# Pre-register core attribute names
_CORE_REGISTRATIONS = [
    ("wingspan", "geometry", "Wing span measured tip to tip", ["span", "wing_span", "WingSpan"]),
    ("chord_length", "geometry", "Mean aerodynamic chord length", ["chord", "mean_chord", "mac"]),
    ("sweep_angle", "geometry", "Wing sweep angle at quarter chord", ["sweep", "sweep_angle_deg"]),
    ("taper_ratio", "geometry", "Wing tip chord / root chord ratio", ["taper", "lambda"]),
    ("thickness_ratio", "geometry", "Airfoil thickness / chord ratio", ["t_c", "tc"]),
    ("wing_area", "geometry", "Reference wing planform area", ["S", "S_ref", "reference_area"]),
    ("aspect_ratio", "geometry", "Wingspan squared / wing area", ["AR", "aspect"]),
    ("material_id", "structure", "Material identifier reference", ["material", "mat_id"]),
    ("material_density", "structure", "Material mass per unit volume", ["density", "rho"]),
    ("design_weight", "structure", "Design weight of component", ["weight", "mass_design"]),
    ("engine_type", "propulsion", "Type of propulsion engine", ["prop_type", "engine_category"]),
    ("max_thrust", "propulsion", "Maximum engine thrust", ["thrust_max", "T_max"]),
    ("V_s", "flight_envelope", "Stall speed", ["v_stall", "stall_speed"]),
    ("V_C", "flight_envelope", "Design cruising speed", ["v_cruise", "cruise_speed"]),
    ("V_D", "flight_envelope", "Design diving speed", ["v_dive", "dive_speed"]),
    ("clause_number", "certification", "FAR-25 clause number", ["clause", "regulation_clause"]),
]

for canonical, domain, desc, aliases in _CORE_REGISTRATIONS:
    try:
        AttributeNameService.register_canonical_name(canonical, domain, desc)
        for alias in aliases:
            AttributeNameService.add_alias(canonical, alias)
    except ValueError:
        pass