// AeroForge-X v5.0 Neo4j Graph Model: FRACAS Causal Graph
// Failure Reporting, Analysis, and Corrective Action System
// REQ-MFG-017~022

// =====================================================
// V504.1: Symptom node constraint
// =====================================================
CREATE CONSTRAINT symptom_id_unique IF NOT EXISTS
FOR (s:Symptom) REQUIRE s.symptom_id IS UNIQUE;

// =====================================================
// V504.2: FailureMode node constraint
// =====================================================
CREATE CONSTRAINT failure_mode_id_unique IF NOT EXISTS
FOR (fm:FailureMode) REQUIRE fm.failure_mode_id IS UNIQUE;

// =====================================================
// V504.3: RootCause node constraint
// =====================================================
CREATE CONSTRAINT root_cause_id_unique IF NOT EXISTS
FOR (rc:RootCause) REQUIRE rc.root_cause_id IS UNIQUE;

// =====================================================
// V504.4: DesignParameter/ManufacturingProcess/MaterialLot constraints
// =====================================================
CREATE CONSTRAINT design_parameter_id_unique IF NOT EXISTS
FOR (dp:DesignParameter) REQUIRE dp.parameter_id IS UNIQUE;

CREATE CONSTRAINT manufacturing_process_id_unique IF NOT EXISTS
FOR (mp:ManufacturingProcess) REQUIRE mp.process_id IS UNIQUE;

CREATE CONSTRAINT material_lot_id_unique IF NOT EXISTS
FOR (ml:MaterialLot) REQUIRE ml.lot_id IS UNIQUE;

// =====================================================
// V504.5: FailureReport node constraint
// =====================================================
CREATE CONSTRAINT failure_report_id_unique IF NOT EXISTS
FOR (fr:FailureReport) REQUIRE fr.report_id IS UNIQUE;

// =====================================================
// V504.6: Causal graph relationship types
// =====================================================
// (:Symptom)-[:INDICATES {weight: Float, confidence: Float}]->(:FailureMode)
// (:FailureMode)-[:CAUSED_BY {probability: Float}]->(:RootCause)
// (:RootCause)-[:RELATED_TO {correlation: Float}]->(:DesignParameter)
// (:RootCause)-[:RELATED_TO {correlation: Float}]->(:ManufacturingProcess)
// (:RootCause)-[:RELATED_TO {correlation: Float}]->(:MaterialLot)
// (:FailureReport)-[:EXHIBITS]->(:Symptom)
// (:FailureReport)-[:CLASSIFIED_AS]->(:FailureMode)

// =====================================================
// V504.7: Root cause analysis query
// =====================================================
// Find top root causes for a given failure report
// MATCH path = (fr:FailureReport {report_id: $report_id})-[:EXHIBITS]->(s:Symptom)
//       -[:INDICATES]->(fm:FailureMode)-[:CAUSED_BY]->(rc:RootCause)
// RETURN rc.name, rc.category, rc.probability_prior,
//        length(path) AS path_length
// ORDER BY rc.probability_prior DESC
// LIMIT 10

// Bayesian posterior probability update
// MATCH (rc:RootCause)-[r:CAUSED_BY]-(fm:FailureMode)
// WHERE fm.failure_mode_id = $failure_mode_id
// SET rc.probability_posterior = r.probability * rc.probability_prior / $normalization_constant

// =====================================================
// V504.8: Failure trend analysis query
// =====================================================
// MATCH (fr:FailureReport)-[:CLASSIFIED_AS]->(fm:FailureMode {severity: 'Critical'})
// WHERE fr.failure_date >= datetime() - duration({days: 90})
// WITH fm.name AS failure_name, count(fr) AS occurrence_count
// ORDER BY occurrence_count DESC
// RETURN failure_name, occurrence_count