export interface BlockConfiguration {
  block_id: string
  aircraft_type: string
  block_name: string
  design_config: DesignConfiguration | null
  manufacturing_config: ManufacturingConfiguration | null
  operational_config: OperationalConfiguration | null
  locked: boolean
  version?: number
  created_at?: string
  updated_at?: string
}

export interface DesignConfiguration {
  config_id: string
  configuration_items: ConfigurationItem[]
  version: number
  status: string
}

export interface ManufacturingConfiguration {
  config_id: string
  source_design_config_id: string
  manufacturing_rules_applied: string[]
  configuration_items: ConfigurationItem[]
  version: number
  status: string
}

export interface OperationalConfiguration {
  config_id: string
  source_mfg_config_id: string
  operational_rules_applied: string[]
  configuration_items: ConfigurationItem[]
  version: number
  status: string
}

export interface ConfigurationItem {
  item_id: string
  item_name: string
  item_type: string
  value: Record<string, unknown>
  version: number
  source_view: string
}

export interface SerialNumberConfiguration {
  sn_id: string
  tail_number: string
  block_id: string
  design_config: DesignConfiguration | null
  manufacturing_config: ManufacturingConfiguration | null
  operational_config: OperationalConfiguration | null
  sn_modifications: SNModification[]
  service_bulletins: Record<string, unknown>[]
  repair_alterations: Record<string, unknown>[]
}

export interface SNModification {
  modification_type: string
  item_id: string
  new_values: Record<string, unknown>
  reason: string
}

export interface ConfigurationHierarchy {
  aircraft_type: string
  blocks: BlockConfiguration[]
  total_serial_numbers: number
}

export interface ConflictEntry {
  conflict_type: string
  item_id: string
  block_value: Record<string, unknown>
  sn_value: Record<string, unknown>
  resolution_suggestion: string
}

export interface ConflictResolutionReport {
  block_id: string
  sn_id: string
  conflicts: ConflictEntry[]
}

export interface ConfigurationBaseline {
  baseline_id: string
  baseline_type: string
  block_id: string
  configuration_snapshot: Record<string, unknown>
  frozen_items: string[]
  milestone: string
  established_by: string
  locked: boolean
  established_at: string
  change_history: BaselineChangeRecord[]
}

export interface BaselineChangeRecord {
  change_id: string
  baseline_id: string
  change_request_id: string
  change_type: string
  approver: string
  approved_at: string
  affected_items: string[]
}

export interface BaselineDeltaItem {
  item_id: string
  delta_type: string
  baseline1_value: Record<string, unknown> | null
  baseline2_value: Record<string, unknown> | null
}

export interface BaselineDeltaReport {
  baseline_id_1: string
  baseline_id_2: string
  added_items: string[]
  removed_items: string[]
  modified_items: BaselineDeltaItem[]
}

export interface ReconciliationSuggestion {
  item_id: string
  source_view: string
  target_view: string
  suggested_action: string
}

export interface ReconciliationReport {
  block_id: string
  reconciliation_suggestions: ReconciliationSuggestion[]
}

export interface PropagationResult {
  design_updated: boolean
  manufacturing_updated: boolean
  operational_updated: boolean
  propagation_duration_ms: number
}

export interface CreateBlockRequest {
  aircraft_type: string
  block_name: string
}

export interface CreateSNRequest {
  block_id: string
  tail_number: string
}

export interface PatchBlockRequest {
  expected_version?: number
  block_name?: string
  [key: string]: unknown
}

export interface EstablishBaselineRequest {
  block_id: string
  established_by: string
}

export interface DetectConflictsRequest {
  block_id: string
  sn_id: string
}

export interface CompareBaselinesRequest {
  baseline_id_1: string
  baseline_id_2: string
}

export interface InheritBlockRequest {
  new_block_name: string
  changes: Record<string, unknown>
}

export interface InheritSNRequest {
  block_id: string
  modifications: Record<string, unknown>
}

export interface MaterialLot {
  lot_id: string
  material_code: string
  material_name: string
  supplier_id: string
  manufacture_date: string | null
  received_date: string | null
  certificate_no: string
  status: string
  created_at: string | null
  updated_at: string | null
}

export interface NDTRecord {
  ndt_record_id: string
  material_lot_id: string
  test_type: string
  result: string
  inspector: string
  test_date: string | null
  notes: string | null
  created_at: string | null
  cars?: CorrectiveActionRequest[]
}

export interface CorrectiveActionRequest {
  car_id: string
  ndt_record_id: string
  description: string
  status: string
  responsible_person: string
  created_at: string | null
  updated_at: string | null
  closed_at: string | null
}

export interface ComplianceRequirement {
  requirement_id: string
  regulation: string
  description: string
  compliance_status: string
  responsible_person: string | null
  updated_at: string | null
  evidences?: Evidence[]
}

export interface Evidence {
  evidence_id: string
  requirement_id: string
  file_id: string
  file_name: string
  bucket: string
  content_type: string
  file_size: number
  upload_timestamp: string | null
  presigned_url?: string | null
}

export interface QualityThreadResponse {
  lot_id: string
  ndt_records: NDTRecord[]
}

export interface TraceNode {
  node_id: string
  identity_id: string | null
  node_type: string
  label: string
  properties: Record<string, unknown>
  created_at: string | null
}

export interface TraceEdge {
  edge_id: string
  source_node_id: string
  target_node_id: string
  edge_type: string
  properties: Record<string, unknown>
  created_at: string | null
}

export interface TraceQueryResult {
  nodes: TraceNode[]
  edges: TraceEdge[]
  truncated: boolean
}

export interface ImpactEntry {
  node: TraceNode
  edge_type: string
}

export interface ImpactAnalysisResult {
  direct: ImpactEntry[]
  indirect: ImpactEntry[]
}

export interface DependencyQueryResult {
  dependencies: ImpactEntry[]
}

export interface TraceStatistics {
  node_count: number
  edge_count: number
  node_types: Record<string, number>
  edge_types: Record<string, number>
  cache_nodes: number
  cache_edges: number
}

export interface ConfigurationIdentity {
  identity_id: string
  canonical_label: string
  node_type: string
  created_at: string | null
}

export interface IdentityMapping {
  mapping_id: string
  identity_id: string
  domain: string
  domain_id: string
  created_at: string | null
}

export interface EventContractInfo {
  event_type: string
  version: string
  schema: Record<string, unknown>
}

export interface TraceDashboard {
  thread_coverage: number
  total_blocks: number
  blocks_traced: number
  trace_depth: number
  open_cars: number
  total_cars: number
  compliance_progress: number
  total_requirements: number
  compliant_requirements: number
}