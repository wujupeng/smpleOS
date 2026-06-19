const API_BASE = '/api/v3/aircraft-core';

async function request(url: string, options?: RequestInit) {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!response.ok) throw new Error(`API Error: ${response.status}`);
  return response.json();
}

export const schemaApi = {
  listSchemas: () => request('/schemas'),

  getSchema: (schemaType: string) => request(`/schemas/${schemaType}`),

  registerSchema: (data: any) => request('/schemas', { method: 'POST', body: JSON.stringify(data) }),

  publishSchemaVersion: (schemaType: string, version: number) =>
    request(`/schemas/${schemaType}/publish`, { method: 'POST', body: JSON.stringify({ version }) }),

  deprecateSchemaVersion: (schemaType: string, version: number) =>
    request(`/schemas/${schemaType}/deprecate`, { method: 'POST', body: JSON.stringify({ version }) }),

  validateCompatibility: (schemaType: string, fromVersion: number, toVersion: number) =>
    request(`/schemas/${schemaType}/compatibility?from=${fromVersion}&to=${toVersion}`),

  generateMigrationPath: (schemaType: string, fromVersion: number, toVersion: number) =>
    request(`/schemas/${schemaType}/migration-path?from=${fromVersion}&to=${toVersion}`),

  executeMigration: (schemaType: string, data: any) =>
    request(`/schemas/${schemaType}/migrate`, { method: 'POST', body: JSON.stringify(data) }),

  batchMigrate: (data: any) => request('/schemas/migrate/batch', { method: 'POST', body: JSON.stringify(data) }),

  validateCrossSchemaRef: (schemaType: string, refField: string, refValue: string) =>
    request(`/schemas/${schemaType}/cross-ref?field=${refField}&value=${refValue}`),

  convertUnit: (value: number, fromUnit: string, toUnit: string) =>
    request('/unit-system/convert', { method: 'POST', body: JSON.stringify({ value, from_unit: fromUnit, to_unit: toUnit }) }),

  getSupportedUnits: (dimension?: string) =>
    request(`/unit-system/supported-units${dimension ? `?dimension=${dimension}` : ''}`),

  validateDimensionalCompatibility: (fromUnit: string, toUnit: string) =>
    request(`/unit-system/validate-dimension?from=${fromUnit}&to=${toUnit}`),

  resolveAttributeName: (name: string) =>
    request(`/unit-system/resolve-attribute-name?name=${encodeURIComponent(name)}`),

  registerCanonicalName: (data: any) =>
    request('/unit-system/attribute-names', { method: 'POST', body: JSON.stringify(data) }),

  addAlias: (canonicalName: string, alias: string) =>
    request(`/unit-system/attribute-names/${encodeURIComponent(canonicalName)}/aliases`, { method: 'POST', body: JSON.stringify({ alias }) }),

  getSchemaInstance: (objectId: string) =>
    request(`/objects/${objectId}/schema-instance`),
};