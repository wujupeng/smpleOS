// Phase 3 Neo4j Initialization Script
// Supplier and PurchaseOrder node constraints and indexes

// Supplier constraints
CREATE CONSTRAINT supplier_id IF NOT EXISTS
FOR (s:Supplier) REQUIRE s.supplier_id IS UNIQUE;

CREATE CONSTRAINT supplier_code IF NOT EXISTS
FOR (s:Supplier) REQUIRE s.code IS UNIQUE;

CREATE CONSTRAINT supplier_tenant IF NOT EXISTS
FOR (s:Supplier) REQUIRE s.tenant_id IS NOT NULL;

// PurchaseOrder constraints
CREATE CONSTRAINT po_id IF NOT EXISTS
FOR (p:PurchaseOrder) REQUIRE p.po_id IS UNIQUE;

CREATE CONSTRAINT po_tenant IF NOT EXISTS
FOR (p:PurchaseOrder) REQUIRE p.tenant_id IS NOT NULL;

// Indexes for tenant-scoped queries
CREATE INDEX supplier_tenant_idx IF NOT EXISTS
FOR (s:Supplier) ON (s.tenant_id);

CREATE INDEX po_tenant_idx IF NOT EXISTS
FOR (p:PurchaseOrder) ON (p.tenant_id);

CREATE INDEX po_supplier_idx IF NOT EXISTS
FOR (p:PurchaseOrder) ON (p.supplier_id);

CREATE INDEX po_status_idx IF NOT EXISTS
FOR (p:PurchaseOrder) ON (p.status);

// Supplier-PurchaseOrder relationship
// MATCH (s:Supplier {supplier_id: $sid}), (p:PurchaseOrder {po_id: $pid})
// MERGE (s)-[:HAS_ORDER]->(p)

// Supplier-Part relationship
// MATCH (s:Supplier {supplier_id: $sid}), (p:Part {part_id: $pid})
// MERGE (s)-[:SUPPLIES]->(p)