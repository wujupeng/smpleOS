const API_BASE = '/api/v3/physics-twin';

async function request(url: string, options?: RequestInit) {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!response.ok) throw new Error(`API Error: ${response.status}`);
  return response.json();
}

export const physicsPluginApi = {
  registerPlugin: (data: any) => request('/plugins', { method: 'POST', body: JSON.stringify(data) }),

  discoverPlugins: () => request('/plugins'),

  loadPlugin: (pluginName: string) => request(`/plugins/${pluginName}/load`, { method: 'POST' }),

  hotReloadPlugin: (pluginName: string) => request(`/plugins/${pluginName}/hot-reload`, { method: 'POST' }),

  validatePluginInterface: (pluginName: string) =>
    request(`/plugins/${pluginName}/validate`, { method: 'POST' }),

  executeModel: (data: any) => request('/models/execute', { method: 'POST', body: JSON.stringify(data) }),

  setModelParameters: (runtimeId: string, data: any) =>
    request(`/models/${runtimeId}/parameters`, { method: 'PUT', body: JSON.stringify(data) }),

  getModelState: (runtimeId: string) => request(`/models/${runtimeId}/state`),

  createCoupledSimulation: (data: any) =>
    request('/coupled-simulations', { method: 'POST', body: JSON.stringify(data) }),

  stepCoupledSimulation: (simulationId: string, dt: number) =>
    request(`/coupled-simulations/${simulationId}/step`, { method: 'POST', body: JSON.stringify({ dt }) }),

  switchRuntimeFidelity: (runtimeId: string, fidelity: string) =>
    request(`/runtimes/${runtimeId}/switch-fidelity`, { method: 'POST', body: JSON.stringify({ fidelity_level: fidelity }) }),

  configureCoupledSimulation: (simulationId: string, data: any) =>
    request(`/coupled-simulations/${simulationId}/configure`, { method: 'PUT', body: JSON.stringify(data) }),
};