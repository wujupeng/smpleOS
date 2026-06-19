-- AeroForge-X v3.0 Aircraft Core Schema Tables
-- Program-A: Aircraft Schema System

-- Schema version management
CREATE TABLE IF NOT EXISTS aircraft_core.schema_versions (
    schema_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schema_name VARCHAR(100) NOT NULL,
    schema_type VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft', 'Published', 'Deprecated')),
    field_definitions JSONB NOT NULL DEFAULT '[]',
    compatible_with INTEGER[] DEFAULT '{}',
    migration_path JSONB DEFAULT '{}',
    cross_schema_refs JSONB DEFAULT '[]',
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(schema_name, version)
);

-- Schema field definitions
CREATE TABLE IF NOT EXISTS aircraft_core.schema_field_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schema_id UUID NOT NULL REFERENCES aircraft_core.schema_versions(schema_id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(30) NOT NULL,
    unit VARCHAR(30),
    constraints JSONB DEFAULT '{}',
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    default_value JSONB,
    is_derived BOOLEAN NOT NULL DEFAULT FALSE,
    derivation_formula TEXT,
    canonical_name VARCHAR(100),
    alias_names TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(schema_id, field_name)
);

-- Attribute name registry
CREATE TABLE IF NOT EXISTS aircraft_core.attribute_name_registry (
    canonical_name VARCHAR(100) PRIMARY KEY,
    domain VARCHAR(50) NOT NULL,
    description TEXT,
    aliases TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unit conversion factors
CREATE TABLE IF NOT EXISTS aircraft_core.unit_conversion_factors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dimension VARCHAR(30) NOT NULL,
    from_unit VARCHAR(30) NOT NULL,
    to_unit VARCHAR(30) NOT NULL,
    factor DOUBLE PRECISION NOT NULL,
    offset DOUBLE PRECISION DEFAULT 0.0,
    UNIQUE(dimension, from_unit, to_unit)
);

-- Insert standard unit conversion factors
INSERT INTO aircraft_core.unit_conversion_factors (dimension, from_unit, to_unit, factor, offset) VALUES
-- Length
('length', 'm', 'ft', 3.28084, 0),
('length', 'ft', 'm', 0.3048, 0),
('length', 'm', 'in', 39.3701, 0),
('length', 'in', 'm', 0.0254, 0),
('length', 'mm', 'm', 0.001, 0),
('length', 'm', 'mm', 1000, 0),
-- Mass
('mass', 'kg', 'lb', 2.20462, 0),
('mass', 'lb', 'kg', 0.453592, 0),
-- Force
('force', 'N', 'lbf', 0.224809, 0),
('force', 'lbf', 'N', 4.44822, 0),
('force', 'kN', 'N', 1000, 0),
-- Pressure
('pressure', 'Pa', 'psi', 0.000145038, 0),
('pressure', 'psi', 'Pa', 6894.76, 0),
('pressure', 'MPa', 'Pa', 1000000, 0),
-- Temperature
('temperature', 'K', 'C', 1, -273.15),
('temperature', 'C', 'K', 1, 273.15),
('temperature', 'C', 'F', 1.8, 32),
('temperature', 'F', 'C', 0.555556, -17.7778),
-- Angle
('angle', 'rad', 'deg', 57.2958, 0),
('angle', 'deg', 'rad', 0.0174533, 0);

-- Insert core attribute name mappings
INSERT INTO aircraft_core.attribute_name_registry (canonical_name, domain, description, aliases) VALUES
('wingspan', 'geometry', 'Wing span measured tip to tip', ARRAY['span', 'wing_span', 'WingSpan']),
('chord_length', 'geometry', 'Mean aerodynamic chord length', ARRAY['chord', 'mean_chord', 'mac']),
('sweep_angle', 'geometry', 'Wing sweep angle at quarter chord', ARRAY['sweep', 'sweep_angle_deg']),
('taper_ratio', 'geometry', 'Wing tip chord / root chord ratio', ARRAY['taper', 'lambda']),
('thickness_ratio', 'geometry', 'Airfoil thickness / chord ratio', ARRAY['t_c', 'tc']),
('wing_area', 'geometry', 'Reference wing planform area', ARRAY['S', 'S_ref', 'reference_area']),
('aspect_ratio', 'geometry', 'Wingspan squared / wing area', ARRAY['AR', 'aspect']),
('material_id', 'structure', 'Material identifier reference', ARRAY['material', 'mat_id']),
('material_density', 'structure', 'Material mass per unit volume', ARRAY['density', 'rho']),
('design_weight', 'structure', 'Design weight of component', ARRAY['weight', 'mass_design']),
('engine_type', 'propulsion', 'Type of propulsion engine', ARRAY['prop_type', 'engine_category']),
('max_thrust', 'propulsion', 'Maximum engine thrust', ARRAY['thrust_max', 'T_max']),
('V_s', 'flight_envelope', 'Stall speed', ARRAY['v_stall', 'stall_speed']),
('V_C', 'flight_envelope', 'Design cruising speed', ARRAY['v_cruise', 'cruise_speed']),
('V_D', 'flight_envelope', 'Design diving speed', ARRAY['v_dive', 'dive_speed']),
('clause_number', 'certification', 'FAR-25 clause number', ARRAY['clause', 'regulation_clause']);

-- ALTER aircraft_objects table to support Schema instances
ALTER TABLE aircraft_core.aircraft_objects
ADD COLUMN IF NOT EXISTS schema_versions JSONB DEFAULT '{}';

-- ALTER property_definitions table
ALTER TABLE aircraft_core.property_definitions
ADD COLUMN IF NOT EXISTS schema_ref VARCHAR(100),
ADD COLUMN IF NOT EXISTS canonical_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS alias_names TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS unit_dimension VARCHAR(30);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_schema_versions_type ON aircraft_core.schema_versions (schema_type);
CREATE INDEX IF NOT EXISTS idx_schema_versions_status ON aircraft_core.schema_versions (status);
CREATE INDEX IF NOT EXISTS idx_schema_fields_canonical ON aircraft_core.schema_field_definitions (canonical_name);
CREATE INDEX IF NOT EXISTS idx_schema_fields_schema ON aircraft_core.schema_field_definitions (schema_id);
CREATE INDEX IF NOT EXISTS idx_attr_name_domain ON aircraft_core.attribute_name_registry (domain);
CREATE INDEX IF NOT EXISTS idx_unit_conv_dim ON aircraft_core.unit_conversion_factors (dimension);