const API_BASE = '/api/v2/aircraft-core';

async function request(url: string, options?: RequestInit) {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!response.ok) throw new Error(`API Error: ${response.status}`);
  return response.json();
}

export const aircraftCoreApi = {
  listObjects: (objectType?: string) =>
    request(`/objects${objectType ? `?object_type=${objectType}` : ''}`),

  getObject: (id: string) => request(`/objects/${id}`),

  createObject: (data: any) => request('/objects', { method: 'POST', body: JSON.stringify(data) }),

  updateObject: (id: string, data: any) => request(`/objects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  deleteObject: (id: string) => request(`/objects/${id}`, { method: 'DELETE' }),

  transitionLifecycle: (id: string, targetState: string, validationData?: any) =>
    request(`/objects/${id}/transition`, { method: 'POST', body: JSON.stringify({ target_state: targetState, validation_data: validationData }) }),

  getVersions: (objectId: string) => request(`/objects/${objectId}/versions`),

  diffVersions: (objectId: string, v1: number, v2: number) =>
    request(`/objects/${objectId}/versions/diff?v1=${v1}&v2=${v2}`),

  createFrozenBaseline: (objectId: string, versionNumbers: number[]) =>
    request(`/objects/${objectId}/baselines/frozen`, { method: 'POST', body: JSON.stringify({ version_numbers: versionNumbers }) }),

  createReleasedBaseline: (objectId: string, versionNumbers: number[], lifecycleStage: string) =>
    request(`/objects/${objectId}/baselines/released`, { method: 'POST', body: JSON.stringify({ version_numbers: versionNumbers, lifecycle_stage: lifecycleStage }) }),

  createLink: (data: any) => request('/links', { method: 'POST', body: JSON.stringify(data) }),

  getRelationships: (objectId: string, depth?: number, linkType?: string) =>
    request(`/objects/${objectId}/relationships?depth=${depth || 1}${linkType ? `&link_type=${linkType}` : ''}`),

  analyzeImpact: (objectId: string, maxDepth?: number) =>
    request(`/objects/${objectId}/impact-analysis`, { method: 'POST', body: JSON.stringify({ max_depth: maxDepth || 5 }) }),

  listPropertyDefinitions: (propertyType?: string) =>
    request(`/property-definitions${propertyType ? `?property_type=${propertyType}` : ''}`),

  createPropertyDefinition: (data: any) =>
    request('/property-definitions', { method: 'POST', body: JSON.stringify(data) }),

  setPropertyValue: (objectId: string, data: any) =>
    request(`/objects/${objectId}/properties`, { method: 'POST', body: JSON.stringify(data) }),

  getObjectProperties: (objectId: string, propertyType?: string) =>
    request(`/objects/${objectId}/properties${propertyType ? `?property_type=${propertyType}` : ''}`),

  convertUnit: (value: number, fromUnit: string, toUnit: string) =>
    request('/properties/convert-unit', { method: 'POST', body: JSON.stringify({ value, from_unit: fromUnit, to_unit: toUnit }) }),
};