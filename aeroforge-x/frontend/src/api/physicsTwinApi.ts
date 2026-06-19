const API_BASE = '/api/v2/physics-twin';

async function request(url: string, options?: RequestInit) {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!response.ok) throw new Error(`API Error: ${response.status}`);
  return response.json();
}

export const physicsTwinApi = {
  listModels: (aircraftObjectId?: string) =>
    request(`/models${aircraftObjectId ? `?aircraft_object_id=${aircraftObjectId}` : ''}`),

  getModel: (id: string) => request(`/models/${id}`),

  createModel: (data: any) => request('/models', { method: 'POST', body: JSON.stringify(data) }),

  updateModel: (id: string, data: any) => request(`/models/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  switchFidelity: (modelId: string, fidelityLevel: string) =>
    request(`/models/${modelId}/switch-fidelity`, { method: 'POST', body: JSON.stringify({ fidelity_level: fidelityLevel }) }),

  mapParameters: (modelId: string, parameterMappings: any[]) =>
    request(`/models/${modelId}/map-parameters`, { method: 'POST', body: JSON.stringify({ parameter_mappings: parameterMappings }) }),

  submitSimulation: (data: any) => request('/simulations', { method: 'POST', body: JSON.stringify(data) }),

  getSimulationStatus: (id: string) => request(`/simulations/${id}`),

  cancelSimulation: (id: string) => request(`/simulations/${id}/cancel`, { method: 'POST' }),

  retrySimulation: (id: string) => request(`/simulations/${id}/retry`, { method: 'POST' }),

  getSimulationResults: (id: string) => request(`/simulations/${id}/results`),

  generateROM: (data: any) => request('/reduced-models', { method: 'POST', body: JSON.stringify(data) }),

  getROM: (id: string) => request(`/reduced-models/${id}`),

  deployROM: (romId: string, runtimeId: string) =>
    request(`/reduced-models/${romId}/deploy`, { method: 'POST', body: JSON.stringify({ runtime_id: runtimeId }) }),

  hotSwapROM: (romId: string, runtimeId: string) =>
    request(`/reduced-models/${romId}/hot-swap`, { method: 'POST', body: JSON.stringify({ runtime_id: runtimeId }) }),

  listRuntimes: () => request('/runtimes'),

  createRuntime: (aircraftObjectId: string) =>
    request('/runtimes', { method: 'POST', body: JSON.stringify({ aircraft_object_id: aircraftObjectId }) }),

  getRuntimeStatus: (id: string) => request(`/runtimes/${id}`),

  pushSensorData: (runtimeId: string, sensorData: any) =>
    request(`/runtimes/${runtimeId}/sensor-data`, { method: 'POST', body: JSON.stringify({ sensor_data: sensorData }) }),

  switchRuntimeFidelity: (runtimeId: string, fidelityLevel: string) =>
    request(`/runtimes/${runtimeId}/switch-fidelity`, { method: 'POST', body: JSON.stringify({ fidelity_level: fidelityLevel }) }),

  getHealth: (runtimeId: string) => request(`/runtimes/${runtimeId}/health`),

  getRUL: (runtimeId: string, componentId: string) =>
    request(`/runtimes/${runtimeId}/rul?component_id=${componentId}`),

  diagnose: (runtimeId: string) => request(`/runtimes/${runtimeId}/diagnose`, { method: 'POST' }),

  requestCalibration: (runtimeId: string, modelId: string) =>
    request('/calibrations', { method: 'POST', body: JSON.stringify({ runtime_id: runtimeId, model_id: modelId }) }),

  getCalibration: (id: string) => request(`/calibrations/${id}`),

  validateCalibration: (id: string, holdoutError: number, threshold?: number) =>
    request(`/calibrations/${id}/validate?holdout_error=${holdoutError}&threshold=${threshold || 0.05}`, { method: 'POST' }),

  applyCalibration: (id: string, rolloutStrategy?: string) =>
    request(`/calibrations/${id}/apply`, { method: 'POST', body: JSON.stringify({ rollout_strategy: rolloutStrategy || 'immediate' }) }),
};