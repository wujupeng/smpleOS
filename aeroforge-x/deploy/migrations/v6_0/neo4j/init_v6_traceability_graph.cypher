// AeroForge-X v6.0 Neo4j Graph Schema
// Requirements Traceability Graph + Material Lot Traceability Graph
// REQ-CERT-001~007, REQ-SUP-007~012

// =====================================================
// V604.1~V604.5: Requirements Traceability Graph Node Constraints
// =====================================================

CREATE CONSTRAINT FOR (req:Requirement) REQUIRE req.node_id IS UNIQUE;
CREATE CONSTRAINT FOR (des:DesignElement) REQUIRE des.node_id IS UNIQUE;
CREATE CONSTRAINT FOR (tc:TestCase) REQUIRE tc.node_id IS UNIQUE;
CREATE CONSTRAINT FOR (evi:EvidenceItem) REQUIRE evi.node_id IS UNIQUE;
CREATE CONSTRAINT FOR (cert:CertificationItem) REQUIRE cert.node_id IS UNIQUE;

// =====================================================
// V604.6: Traceability Graph Relationship Types
// (:Requirement)-[:SATISFIED_BY {confidence: Float}]->(:DesignElement)
// (:DesignElement)-[:VERIFIED_BY {method: String}]->(:TestCase)
// (:TestCase)-[:PRODUCES {status: String}]->(:EvidenceItem)
// (:EvidenceItem)-[:DEMONSTRATES {compliance: String}]->(:CertificationItem)

// =====================================================
// V604.7: Forward Traceability Query
// =====================================================
// MATCH path = (req:Requirement {node_id: $requirement_id})-[:SATISFIED_BY]->(des:DesignElement)
//       -[:VERIFIED_BY]->(tc:TestCase)-[:PRODUCES]->(evi:EvidenceItem)
//       -[:DEMONSTRATES]->(cert:CertificationItem)
// RETURN path

// =====================================================
// V604.8: Backward Traceability Query
// =====================================================
// MATCH path = (cert:CertificationItem {node_id: $cert_id})<-[:DEMONSTRATES]-(evi:EvidenceItem)
//       <-[:PRODUCES]-(tc:TestCase)<-[:VERIFIED_BY]-(des:DesignElement)
//       <-[:SATISFIED_BY]-(req:Requirement)
// RETURN path

// =====================================================
// V604.9: Traceability Coverage Calculation Query
// =====================================================
// MATCH (req:Requirement)
// OPTIONAL MATCH (req)-[:SATISFIED_BY]->(des:DesignElement)-[:VERIFIED_BY]->(tc:TestCase)
//       -[:PRODUCES]->(evi:EvidenceItem)-[:DEMONSTRATES]->(cert:CertificationItem)
// WITH req, CASE WHEN cert IS NOT NULL THEN 1 ELSE 0 END AS has_full_chain
// RETURN count(req) AS total_requirements,
//        sum(has_full_chain) AS requirements_with_full_chain,
//        sum(has_full_chain) * 100.0 / count(req) AS coverage_percentage

// =====================================================
// V604.10~V604.12: Material Lot Traceability Graph Node Constraints
// =====================================================

CREATE CONSTRAINT FOR (ml:MaterialLot) REQUIRE ml.lot_id IS UNIQUE;
CREATE CONSTRAINT FOR (part:InstalledPart) REQUIRE part.part_serial_id IS UNIQUE;
CREATE CONSTRAINT FOR (ac:Aircraft) REQUIRE ac.tail_number IS UNIQUE;

// =====================================================
// V604.13: Material Traceability Graph Relationship Types
// (:MaterialLot)-[:TRANSFORMED_TO {step_type: String, parameters: Map}]->(:MaterialLot)
// (:MaterialLot)-[:INSTALLED_IN]->(:InstalledPart)
// (:InstalledPart)-[:MOUNTED_ON]->(:Aircraft)

// =====================================================
// V604.14: Forward Traceability Query (Material Lot -> Aircraft)
// =====================================================
// MATCH path = (ml:MaterialLot {lot_id: $lot_id})-[:TRANSFORMED_TO*0..]->(derived:MaterialLot)
//       -[:INSTALLED_IN]->(part:InstalledPart)-[:MOUNTED_ON]->(ac:Aircraft)
// RETURN DISTINCT ac.tail_number AS affected_aircraft, part.part_serial_id AS affected_part

// =====================================================
// V604.15: Backward Traceability Query (Aircraft -> Material Lot)
// =====================================================
// MATCH path = (ac:Aircraft {tail_number: $tail_number})<-[:MOUNTED_ON]-(part:InstalledPart)
//       <-[:INSTALLED_IN]-(ml:MaterialLot)-[:TRANSFORMED_TO*0..]->(source:MaterialLot)
// RETURN source.lot_id, source.supplier, source.heat_number