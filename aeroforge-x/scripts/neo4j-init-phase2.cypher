// Phase 2: mBOM/sBOM Neo4j constraints and indexes

// mBOM node constraints
CREATE CONSTRAINT mbom_item_id IF NOT EXISTS
FOR (m:MBOmItem) REQUIRE m.id IS UNIQUE;

CREATE CONSTRAINT mbom_part_number IF NOT EXISTS
FOR (m:MBOmItem) REQUIRE m.part_number IS UNIQUE;

// sBOM node constraints
CREATE CONSTRAINT sbom_item_id IF NOT EXISTS
FOR (s:SBOmItem) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT sbom_serial_number IF NOT EXISTS
FOR (s:SBOmItem) REQUIRE s.serial_number IS UNIQUE;

// MAPPED_TO relationship index
CREATE INDEX mbom_ebom_mapping IF NOT EXISTS
FOR ()-[r:MAPPED_TO]-() ON (r.mapping_rule_id, r.confidence);

// CONTAINS relationship indexes for mBOM/sBOM trees
CREATE INDEX mbom_contains IF NOT EXISTS
FOR ()-[r:CONTAINS]-() ON (r.quantity, r.reference_designator);

// Trace indexes for sBOM
CREATE INDEX sbom_supplier IF NOT EXISTS
FOR (s:SBOmItem) ON (s.supplier_code, s.batch_number);

CREATE INDEX sbom_status IF NOT EXISTS
FOR (s:SBOmItem) ON (s.status);

// Process route indexes
CREATE CONSTRAINT process_route_id IF NOT EXISTS
FOR (p:ProcessRoute) REQUIRE p.id IS UNIQUE;

CREATE INDEX process_route_name IF NOT EXISTS
FOR (p:ProcessRoute) ON (p.name, p.active);