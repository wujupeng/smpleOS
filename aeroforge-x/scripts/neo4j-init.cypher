CREATE CONSTRAINT bom_item_code IF NOT EXISTS
FOR (b:BOMItem) REQUIRE b.itemCode IS UNIQUE;

CREATE CONSTRAINT part_code IF NOT EXISTS
FOR (p:Part) REQUIRE p.partCode IS UNIQUE;

CREATE CONSTRAINT supplier_code IF NOT EXISTS
FOR (s:Supplier) REQUIRE s.supplierCode IS UNIQUE;

CREATE CONSTRAINT batch_number IF NOT EXISTS
FOR (b:Batch) REQUIRE b.batchNumber IS UNIQUE;

CREATE CONSTRAINT serial_number IF NOT EXISTS
FOR (s:SerialNumber) REQUIRE s.serialNumber IS UNIQUE;

CREATE CONSTRAINT inspection_code IF NOT EXISTS
FOR (i:Inspection) REQUIRE i.recordCode IS UNIQUE;

CREATE CONSTRAINT work_order_code IF NOT EXISTS
FOR (w:WorkOrder) REQUIRE w.orderCode IS UNIQUE;

CREATE CONSTRAINT aircraft_code IF NOT EXISTS
FOR (a:Aircraft) REQUIRE a.aircraftCode IS UNIQUE;

CREATE INDEX bom_item_type_idx IF NOT EXISTS
FOR (b:BOMItem) ON (b.bomType);

CREATE INDEX part_category_idx IF NOT EXISTS
FOR (p:Part) ON (p.category);

CREATE INDEX batch_supplier_idx IF NOT EXISTS
FOR (b:Batch) ON (b.supplierCode);