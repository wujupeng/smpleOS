import axios from 'axios'

const v6Client = axios.create({
  baseURL: '/api/v6',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

v6Client.interceptors.response.use(
  (res) => res.data,
  (err) => {
    console.error('V6 API Error:', err?.response?.status, err?.response?.data || err.message)
    return Promise.reject(err)
  }
)

export const configApi = {
  getHierarchy: (aircraftType: string) =>
    v6Client.get(`/aircraft-core/config-hierarchies/${aircraftType}`),

  getBlock: (blockId: string) =>
    v6Client.get(`/aircraft-core/block-configurations/${blockId}`),

  createBlock: (data: { aircraft_type: string; block_name: string }) =>
    v6Client.post('/aircraft-core/block-configurations', data),

  patchBlock: (blockId: string, data: Record<string, unknown>) =>
    v6Client.patch(`/aircraft-core/block-configurations/${blockId}`, data),

  inheritBlock: (blockId: string, data: { new_block_name: string; changes: Record<string, unknown> }) =>
    v6Client.post(`/aircraft-core/block-configurations/${blockId}/inherit`, data),

  createSN: (data: { block_id: string; tail_number: string }) =>
    v6Client.post('/aircraft-core/sn-configurations', data),

  inheritSN: (snId: string, data: { block_id: string; modifications: Record<string, unknown> }) =>
    v6Client.post(`/aircraft-core/sn-configurations/${snId}/inherit`, data),

  detectConflicts: (data: { block_id: string; sn_id: string }) =>
    v6Client.post('/aircraft-core/config-conflicts/detect', data),

  detectInconsistencies: (configId: string) =>
    v6Client.get(`/aircraft-core/configs/${configId}/inconsistencies`),

  propagateChange: (configId: string, data: { block_id: string; changed_items: unknown[]; reason: string }) =>
    v6Client.post(`/aircraft-core/design-configs/${configId}/propagate-change`, data),

  deriveManufacturing: (configId: string, data: { rules?: unknown[] }) =>
    v6Client.post(`/aircraft-core/design-configs/${configId}/derive-manufacturing`, data),

  deriveOperational: (configId: string, data: { rules?: unknown[] }) =>
    v6Client.post(`/aircraft-core/mfg-configs/${configId}/derive-operational`, data),
}

export const baselineApi = {
  establishFBL: (data: { block_id: string; established_by: string }) =>
    v6Client.post('/aircraft-core/baselines/fbl', data),

  establishFCL: (data: { block_id: string; established_by: string }) =>
    v6Client.post('/aircraft-core/baselines/fcl', data),

  establishFSDL: (data: { block_id: string; established_by: string }) =>
    v6Client.post('/aircraft-core/baselines/fsdl', data),

  compareBaselines: (data: { baseline_id_1: string; baseline_id_2: string }) =>
    v6Client.post('/aircraft-core/baselines/compare', data),
}

export const certApi = {
  listRegulations: () => v6Client.get('/aircraft-core/cert/regulations'),
  getRegulation: (id: string) => v6Client.get(`/aircraft-core/cert/regulations/${id}`),
  listChecklists: (regulationId: string) =>
    v6Client.get(`/aircraft-core/cert/checklists?regulation_id=${regulationId}`),
  generateChecklist: (data: unknown) => v6Client.post('/aircraft-core/cert/checklists', data),
  getTraceMatrix: (projectId: string) =>
    v6Client.get(`/aircraft-core/cert/traceability?project_id=${projectId}`),
  createTraceLink: (data: unknown) => v6Client.post('/aircraft-core/cert/traceability', data),
  listEvidencePackages: () => v6Client.get('/workflow-engine/cert/evidence'),
  assemblePackage: (data: unknown) => v6Client.post('/workflow-engine/cert/evidence', data),
}

export const supplierApi = {
  listSuppliers: () => v6Client.get('/aircraft-core/supplier/registry'),
  getSupplier: (id: string) => v6Client.get(`/aircraft-core/supplier/registry/${id}`),
  registerSupplier: (data: unknown) => v6Client.post('/aircraft-core/supplier/registry', data),
  listLots: (supplierId: string) =>
    v6Client.get(`/aircraft-core/supplier/lots?supplier_id=${supplierId}`),
}

export const factoryApi = {
  getProductionDashboard: () => v6Client.get('/aircraft-core/factory/dashboard'),
  getEquipmentOEE: (equipmentId: string) =>
    v6Client.get(`/physics-twin/factory/equipment/${equipmentId}/oee`),
  getAGVFleet: () => v6Client.get('/physics-twin/factory/agv-fleet'),
  listShopFloorEvents: (type?: string) =>
    v6Client.get(`/workflow-engine/factory/events${type ? `?type=${type}` : ''}`),
}

export const fleetApi = {
  getFleetHealth: () => v6Client.get('/physics-twin/fleet/health'),
  getRULPrediction: (componentId: string) =>
    v6Client.get(`/physics-twin/fleet/phm/predict/${componentId}`),
  getConfidenceReport: (componentId: string) =>
    v6Client.get(`/physics-twin/fleet/phm/confidence/${componentId}`),
  getClosedLoopStatus: (predictionId: string) =>
    v6Client.get(`/physics-twin/fleet/phm/closed-loop/${predictionId}`),
}

export const dtApi = {
  listMaterialLots: (limit = 100, offset = 0) =>
    v6Client.get(`/aircraft-core/dt/material-lots?limit=${limit}&offset=${offset}`),

  getMaterialLot: (lotId: string) =>
    v6Client.get(`/aircraft-core/dt/material-lots/${lotId}`),

  createMaterialLot: (data: {
    material_code: string
    material_name: string
    supplier_id: string
    manufacture_date: string
    received_date: string
    certificate_no: string
    block_id?: string
  }) => v6Client.post('/aircraft-core/dt/material-lots', data),

  getBlockMaterials: (blockId: string) =>
    v6Client.get(`/aircraft-core/dt/blocks/${blockId}/materials`),

  createNDTRecord: (data: {
    material_lot_id: string
    test_type: string
    result: string
    inspector: string
    test_date: string
    notes?: string
  }) => v6Client.post('/aircraft-core/dt/ndt-records', data),

  getNDTRecord: (ndtId: string) =>
    v6Client.get(`/aircraft-core/dt/ndt-records/${ndtId}`),

  createCAR: (data: {
    ndt_record_id: string
    description: string
    responsible_person: string
  }) => v6Client.post('/aircraft-core/dt/corrective-actions', data),

  updateCAR: (carId: string, data: { status: string; closed_by?: string }) =>
    v6Client.patch(`/aircraft-core/dt/corrective-actions/${carId}`, data),

  getQualityThread: (lotId: string) =>
    v6Client.get(`/aircraft-core/dt/material-lots/${lotId}/quality`),

  getCompliance: (requirementId: string) =>
    v6Client.get(`/aircraft-core/dt/certification/compliance/${requirementId}`),

  updateCompliance: (requirementId: string, data: {
    compliance_status: string
    responsible_person?: string
  }) =>
    v6Client.patch(`/aircraft-core/dt/certification/compliance/${requirementId}`, data),

  listComplianceRequirements: (limit = 100, offset = 0) =>
    v6Client.get(`/aircraft-core/dt/certification/compliance-requirements?limit=${limit}&offset=${offset}`),

  getEvidence: (evidenceId: string) =>
    v6Client.get(`/aircraft-core/dt/certification/evidence/${evidenceId}`),
}

export default v6Client
