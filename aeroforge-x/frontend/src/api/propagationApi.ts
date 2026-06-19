const API_BASE = '/api/v3/workflow-engine';

async function request(url: string, options?: RequestInit) {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!response.ok) throw new Error(`API Error: ${response.status}`);
  return response.json();
}

export const propagationApi = {
  configureChain: (data: any) =>
    request('/propagation-chains', { method: 'POST', body: JSON.stringify(data) }),

  listChains: () => request('/propagation-chains'),

  getChainStatus: (chainId: string) => request(`/propagation-chains/${chainId}/status`),

  getChainAudit: (chainId: string) => request(`/propagation-chains/${chainId}/audit`),

  executeChain: (chainId: string, data?: any) =>
    request(`/propagation-chains/${chainId}/execute`, { method: 'POST', body: JSON.stringify(data || {}) }),

  listHandlers: () => request('/handlers'),

  registerHandler: (data: any) => request('/handlers', { method: 'POST', body: JSON.stringify(data) }),

  hotReloadHandler: (handlerName: string) =>
    request(`/handlers/${handlerName}/hot-reload`, { method: 'POST' }),
};