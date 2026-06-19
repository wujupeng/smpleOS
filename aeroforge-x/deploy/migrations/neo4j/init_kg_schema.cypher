// ============================================================
// AeroForge-X v1.0 Knowledge Graph Neo4j Schema Initialization
// 7 Node Types + 11 Relationship Types
// ============================================================

// --- Node Type Constraints ---

CREATE CONSTRAINT requirement_node_id IF NOT EXISTS
FOR (n:RequirementNode) REQUIRE n.nodeId IS UNIQUE;

CREATE CONSTRAINT design_node_id IF NOT EXISTS
FOR (n:DesignNode) REQUIRE n.nodeId IS UNIQUE;

CREATE CONSTRAINT structure_node_id IF NOT EXISTS
FOR (n:StructureNode) REQUIRE n.nodeId IS UNIQUE;

CREATE CONSTRAINT material_node_id IF NOT EXISTS
FOR (n:MaterialNode) REQUIRE n.nodeId IS UNIQUE;

CREATE CONSTRAINT manufacturing_node_id IF NOT EXISTS
FOR (n:ManufacturingNode) REQUIRE n.nodeId IS UNIQUE;

CREATE CONSTRAINT flight_node_id IF NOT EXISTS
FOR (n:FlightNode) REQUIRE n.nodeId IS UNIQUE;

CREATE CONSTRAINT maintenance_node_id IF NOT EXISTS
FOR (n:MaintenanceNode) REQUIRE n.nodeId IS UNIQUE;

// --- Composite Indexes ---

CREATE INDEX requirement_node_name IF NOT EXISTS
FOR (n:RequirementNode) ON (n.name);

CREATE INDEX design_node_name IF NOT EXISTS
FOR (n:DesignNode) ON (n.name);

CREATE INDEX structure_node_name IF NOT EXISTS
FOR (n:StructureNode) ON (n.name);

CREATE INDEX material_node_name IF NOT EXISTS
FOR (n:MaterialNode) ON (n.name);

CREATE INDEX manufacturing_node_name IF NOT EXISTS
FOR (n:ManufacturingNode) ON (n.name);

CREATE INDEX flight_node_name IF NOT EXISTS
FOR (n:FlightNode) ON (n.name);

CREATE INDEX maintenance_node_name IF NOT EXISTS
FOR (n:MaintenanceNode) ON (n.name);

// --- Full-text Search Index ---

CREATE FULLTEXT INDEX knowledge_node_search IF NOT EXISTS
FOR (n:RequirementNode|DesignNode|StructureNode|MaterialNode|ManufacturingNode|FlightNode|MaintenanceNode)
ON EACH [n.name, n.description];

// --- Node Property Indexes ---

CREATE INDEX node_confidence IF NOT EXISTS
FOR (n:RequirementNode|DesignNode|StructureNode|MaterialNode|ManufacturingNode|FlightNode|MaintenanceNode)
ON (n.confidence);

CREATE INDEX node_source IF NOT EXISTS
FOR (n:RequirementNode|DesignNode|StructureNode|MaterialNode|ManufacturingNode|FlightNode|MaintenanceNode)
ON (n.source);

CREATE INDEX node_updated_at IF NOT EXISTS
FOR (n:RequirementNode|DesignNode|StructureNode|MaterialNode|ManufacturingNode|FlightNode|MaintenanceNode)
ON (n.updatedAt);

// --- Relationship Type Documentation ---
// DERIVES_FROM:      RequirementNode -> DesignNode (需求派生设计)
// CONSTRAINS:        RequirementNode -> StructureNode (需求约束结构)
// IMPLEMENTS:        DesignNode -> StructureNode (设计实现为结构)
// USES_MATERIAL:     StructureNode -> MaterialNode (结构使用材料)
// PRODUCED_BY:       StructureNode -> ManufacturingNode (结构由制造产出)
// MONITORED_BY:      StructureNode -> FlightNode (结构由飞行监控)
// MAINTAINED_BY:     StructureNode -> MaintenanceNode (结构由维护保障)
// AFFECTS:           AnyNode -> AnyNode (影响关系，用于影响传播)
// DEPENDS_ON:        AnyNode -> AnyNode (依赖关系)
// VERIFIED_BY:       DesignNode -> FlightNode (设计由飞行验证)
// SUPERSEDES:        AnyNode -> AnyNode (替代关系，版本迭代)