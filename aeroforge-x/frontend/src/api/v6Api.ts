import axios from 'axios'

const v6Client = axios.create({
  baseURL: '/api/v6',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

v6Client.interceptors.response.use(
  (res) => res.data,
  (err) => {
    console.error('V6 API Error:', err)
    return Promise.reject(err)
  }
)

export const configApi = {
  listBlocks: () => v6Client.get('/aircraft-core/config/blocks'),
  getBlock: (blockId: string) => v6Client.get(`/aircraft-core/config/blocks/${blockId}`),
  createBlock: (data: { aircraft_type: string; block_name: string }) =>
    v6Client.post('/aircraft-core/config/blocks', data),
  listSNs: (blockId: string) => v6Client.get(`/aircraft-core/config/blocks/${blockId}/sns`),
  createSN: (blockId: string, data: { tail_number: string }) =>
    v6Client.post(`/aircraft-core/config/blocks/${blockId}/sns`, data),
  detectConflicts: (blockId: string, snId: string) =>
    v6Client.get(`/aircraft-core/config/conflicts?block_id=${blockId}&sn_id=${snId}`),
  listBaselines: (blockId: string) => v6Client.get(`/aircraft-core/config/baselines?block_id=${blockId}`),
  establishBaseline: (data: any) => v6Client.post('/aircraft-core/config/baselines', data),
}

export const certApi = {
  listRegulations: () => v6Client.get('/aircraft-core/cert/regulations'),
  getRegulation: (id: string) => v6Client.get(`/aircraft-core/cert/regulations/${id}`),
  listChecklists: (regulationId: string) =>
    v6Client.get(`/aircraft-core/cert/checklists?regulation_id=${regulationId}`),
  generateChecklist: (data: any) => v6Client.post('/aircraft-core/cert/checklists', data),
  getTraceMatrix: (projectId: string) =>
    v6Client.get(`/aircraft-core/cert/traceability?project_id=${projectId}`),
  createTraceLink: (data: any) => v6Client.post('/aircraft-core/cert/traceability', data),
  listEvidencePackages: () => v6Client.get('/workflow-engine/cert/evidence'),
  assemblePackage: (data: any) => v6Client.post('/workflow-engine/cert/evidence', data),
}

export const supplierApi = {
  listSuppliers: () => v6Client.get('/aircraft-core/supplier/registry'),
  getSupplier: (id: string) => v6Client.get(`/aircraft-core/supplier/registry/${id}`),
  registerSupplier: (data: any) => v6Client.post('/aircraft-core/supplier/registry', data),
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

export default v6Client