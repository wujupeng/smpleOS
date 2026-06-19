// AeroForge-X v2.0 Neo4j AircraftObject Graph Schema
// 关联需求：REQ-ACD-019~027, REQ-ACD-039, REQ-ACD-040

CREATE CONSTRAINT FOR (o:AircraftObject) REQUIRE o.id IS UNIQUE;

CREATE INDEX FOR (o:AircraftObject) ON (o.objectType);
CREATE INDEX FOR (o:AircraftObject) ON (o.lifecycleState);
CREATE INDEX FOR (o:AircraftObject) ON (o.name);

// Relationship Types:
// (:AircraftObject)-[:CONTAINS {quantity: Int, metadata: Map}]->(:AircraftObject)
// (:AircraftObject)-[:DEPENDS_ON {interfaceType: String, metadata: Map}]->(:AircraftObject)
// (:AircraftObject)-[:TRACE_TO {traceType: String, metadata: Map}]->(:AircraftObject)
// (:AircraftObject)-[:CHANGE_PROPAGATES_TO {propagationRule: String, confidence: Float, metadata: Map}]->(:AircraftObject)

// N-degree traversal example (3-layer change propagation analysis):
// MATCH path = (source:AircraftObject {id: $objectId})-[:CHANGE_PROPAGATES_TO*1..3]->(target:AircraftObject)
// RETURN path
// LIMIT 1000;