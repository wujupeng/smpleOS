// AeroForge-X v3.0 Neo4j Graph Model Changes
// Program-A: Schema Definition nodes and relationships

// SchemaDefinition node constraints
CREATE CONSTRAINT schema_def_id IF NOT EXISTS
FOR (sd:SchemaDefinition) REQUIRE sd.schema_id IS UNIQUE;

CREATE CONSTRAINT schema_def_type IF NOT EXISTS
FOR (sd:SchemaDefinition) REQUIRE sd.schema_type IS NOT NULL;

CREATE CONSTRAINT schema_def_version IF NOT EXISTS
FOR (sd:SchemaDefinition) REQUIRE sd.version IS NOT NULL;

// HAS_SCHEMA relationship type
// (AircraftObject)-[:HAS_SCHEMA]->(SchemaDefinition)
// Properties: schema_type, version

// PROPAGATES_VIA relationship type
// (AircraftObject)-[:PROPAGATES_VIA]->(PropagationChain)
// Properties: chain_type

// Create sample SchemaDefinition nodes for v3.0
MERGE (sg:SchemaDefinition {schema_id: 'schema-geometry-v1'})
  SET sg.schema_type = 'AircraftGeometry',
      sg.version = 1,
      sg.status = 'Published',
      sg.fields = ['wingspan', 'chord_length', 'sweep_angle', 'taper_ratio', 'thickness_ratio', 'wing_area', 'dihedral_angle', 'incidence_angle'],
      sg.created_at = datetime()

MERGE (ss:SchemaDefinition {schema_id: 'schema-structure-v1'})
  SET ss.schema_type = 'AircraftStructure',
      ss.version = 1,
      ss.status = 'Published',
      ss.fields = ['material_id', 'material_density', 'yield_strength', 'ultimate_strength', 'elastic_modulus', 'design_weight', 'manufacturing_weight', 'weight_margin', 'skin_thickness', 'rib_spacing', 'spar_cross_section'],
      ss.created_at = datetime()

MERGE (sp:SchemaDefinition {schema_id: 'schema-propulsion-v1'})
  SET sp.schema_type = 'AircraftPropulsion',
      sp.version = 1,
      sp.status = 'Published',
      sp.fields = ['engine_type', 'max_thrust', 'sfc', 'bypass_ratio', 'battery_capacity', 'battery_voltage'],
      sp.created_at = datetime()

MERGE (sa:SchemaDefinition {schema_id: 'schema-avionics-v1'})
  SET sa.schema_type = 'AircraftAvionics',
      sa.version = 1,
      sa.status = 'Published',
      sa.fields = ['control_law_type', 'elevator_limit', 'aileron_limit', 'rudder_limit', 'sas_pitch_gain', 'sas_roll_gain', 'sas_yaw_gain'],
      sa.created_at = datetime()

MERGE (se:SchemaDefinition {schema_id: 'schema-envelope-v1'})
  SET se.schema_type = 'AircraftFlightEnvelope',
      se.version = 1,
      se.status = 'Published',
      se.fields = ['V_s', 'V_A', 'V_C', 'V_D', 'h_max', 'n_min', 'n_max', 'CG_fwd', 'CG_aft'],
      se.created_at = datetime()

MERGE (sc:SchemaDefinition {schema_id: 'schema-certification-v1'})
  SET sc.schema_type = 'AircraftCertification',
      sc.version = 1,
      sc.status = 'Published',
      sc.fields = ['clause_number', 'clause_title', 'compliance_status', 'compliance_method', 'evidence_ref'],
      sc.created_at = datetime()

// Create cross-schema reference relationships
MATCH (sg:SchemaDefinition {schema_type: 'AircraftStructure'})
MATCH (geo:SchemaDefinition {schema_type: 'AircraftGeometry'})
MERGE (sg)-[:REFERENCES {field: 'geometry_ref'}]->(geo)

MATCH (sp:SchemaDefinition {schema_type: 'AircraftPropulsion'})
MATCH (geo:SchemaDefinition {schema_type: 'AircraftGeometry'})
MERGE (sp)-[:REFERENCES {field: 'geometry_ref'}]->(geo)

MATCH (sp:SchemaDefinition {schema_type: 'AircraftPropulsion'})
MATCH (str:SchemaDefinition {schema_type: 'AircraftStructure'})
MERGE (sp)-[:REFERENCES {field: 'structure_ref'}]->(str)

MATCH (sa:SchemaDefinition {schema_type: 'AircraftAvionics'})
MATCH (sp:SchemaDefinition {schema_type: 'AircraftPropulsion'})
MERGE (sa)-[:REFERENCES {field: 'propulsion_ref'}]->(sp)

MATCH (sa:SchemaDefinition {schema_type: 'AircraftAvionics'})
MATCH (se:SchemaDefinition {schema_type: 'AircraftFlightEnvelope'})
MERGE (sa)-[:REFERENCES {field: 'envelope_ref'}]->(se)

MATCH (sc:SchemaDefinition {schema_type: 'AircraftCertification'})
MATCH (geo:SchemaDefinition {schema_type: 'AircraftGeometry'})
MERGE (sc)-[:REFERENCES {field: 'geometry_ref'}]->(geo)

MATCH (sc:SchemaDefinition {schema_type: 'AircraftCertification'})
MATCH (str:SchemaDefinition {schema_type: 'AircraftStructure'})
MERGE (sc)-[:REFERENCES {field: 'structure_ref'}]->(str)

MATCH (sc:SchemaDefinition {schema_type: 'AircraftCertification'})
MATCH (se:SchemaDefinition {schema_type: 'AircraftFlightEnvelope'})
MERGE (sc)-[:REFERENCES {field: 'envelope_ref'}]->(se)