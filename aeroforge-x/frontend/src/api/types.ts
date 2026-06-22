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