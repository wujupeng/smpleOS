// AeroForge-X v4.0 Neo4j Graph Model: Airworthiness Evidence Chain
// Test Evidence Center traceability graph

// V404.1: Node constraints
CREATE CONSTRAINT test_case_id IF NOT EXISTS
FOR (tc:TestCase) REQUIRE tc.test_case_id IS UNIQUE;

CREATE CONSTRAINT test_result_id IF NOT EXISTS
FOR (tr:TestResult) REQUIRE tr.test_result_id IS UNIQUE;

CREATE CONSTRAINT verification_evidence_id IF NOT EXISTS
FOR (ve:VerificationEvidence) REQUIRE ve.evidence_id IS UNIQUE;

CREATE CONSTRAINT airworthiness_clause_id IF NOT EXISTS
FOR (ac:AirworthinessClause) REQUIRE ac.clause_number IS UNIQUE;

CREATE CONSTRAINT compliance_method_id IF NOT EXISTS
FOR (cm:ComplianceMethod) REQUIRE cm.method_code IS UNIQUE;

// V404.2: Evidence chain relationship types
// (:TestCase)-[:PRODUCES]->(:TestResult)
// (:TestResult)-[:SUPPORTS]->(:VerificationEvidence)
// (:VerificationEvidence)-[:DEMONSTRATES]->(:ComplianceMethod)
// (:ComplianceMethod)-[:SATISFIES]->(:AirworthinessClause)

// V404.3: Evidence chain completeness query
// Find airworthiness clauses with incomplete evidence chains
MATCH (ac:AirworthinessClause)
WHERE NOT EXISTS {
  MATCH (ac)<-[:SATISFIES]-(cm:ComplianceMethod)
  MATCH (cm)<-[:DEMONSTRATES]-(ve:VerificationEvidence)
  MATCH (ve)<-[:SUPPORTS]-(tr:TestResult {execution_status: 'passed'})
  MATCH (tr)<-[:PRODUCES]-(tc:TestCase)
}
RETURN ac.clause_number AS incomplete_clause,
       ac.clause_title AS title;

// Evidence chain gap analysis query
MATCH (ac:AirworthinessClause)
OPTIONAL MATCH (ac)<-[:SATISFIES]-(cm:ComplianceMethod)
OPTIONAL MATCH (cm)<-[:DEMONSTRATES]-(ve:VerificationEvidence)
OPTIONAL MATCH (ve)<-[:SUPPORTS]-(tr:TestResult)
OPTIONAL MATCH (tr)<-[:PRODUCES]-(tc:TestCase)
RETURN ac.clause_number AS clause,
       cm.method_code AS method,
       ve.evidence_id AS evidence,
       tr.execution_status AS test_status,
       CASE
         WHEN tr.execution_status = 'passed' THEN 'complete'
         WHEN tr IS NULL THEN 'missing_test'
         WHEN ve IS NULL THEN 'missing_evidence'
         WHEN cm IS NULL THEN 'missing_method'
         ELSE 'incomplete'
       END AS chain_status;