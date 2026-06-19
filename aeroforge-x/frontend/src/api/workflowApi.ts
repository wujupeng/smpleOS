const API_BASE = '/api/v2/workflow-engine';

async function request(url: string, options?: RequestInit) {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!response.ok) throw new Error(`API Error: ${response.status}`);
  return response.json();
}

export const workflowApi = {
  listDefinitions: (status?: string) =>
    request(`/definitions${status ? `?status=${status}` : ''}`),

  getDefinition: (id: string) => request(`/definitions/${id}`),

  createDefinition: (data: any) => request('/definitions', { method: 'POST', body: JSON.stringify(data) }),

  updateDefinition: (id: string, data: any) => request(`/definitions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  publishDefinition: (id: string) => request(`/definitions/${id}/publish`, { method: 'POST' }),

  deprecateDefinition: (id: string) => request(`/definitions/${id}/deprecate`, { method: 'POST' }),

  listTemplates: () => request('/definitions'),

  startInstance: (definitionId: string, inputParameters?: any) =>
    request('/instances', { method: 'POST', body: JSON.stringify({ definition_id: definitionId, input_parameters: inputParameters }) }),

  getInstanceStatus: (instanceId: string) => request(`/instances/${instanceId}`),

  suspendInstance: (instanceId: string) => request(`/instances/${instanceId}/suspend`, { method: 'POST' }),

  resumeInstance: (instanceId: string) => request(`/instances/${instanceId}/resume`, { method: 'POST' }),

  cancelInstance: (instanceId: string) => request(`/instances/${instanceId}/cancel`, { method: 'POST' }),

  retryNode: (instanceId: string, nodeId: string) =>
    request(`/instances/${instanceId}/nodes/${nodeId}/retry`, { method: 'POST' }),

  createTrigger: (data: any) => request('/triggers', { method: 'POST', body: JSON.stringify(data) }),

  listTriggers: (definitionId?: string) =>
    request(`/triggers${definitionId ? `?definition_id=${definitionId}` : ''}`),

  testTrigger: (triggerId: string) => request(`/triggers/${triggerId}/test`, { method: 'POST' }),

  listPendingTasks: (assignee?: string) =>
    request(`/human-tasks${assignee ? `?assignee=${assignee}` : ''}`),

  approveTask: (taskId: string, comments?: string) =>
    request(`/human-tasks/${taskId}/approve`, { method: 'POST', body: JSON.stringify({ comments }) }),

  rejectTask: (taskId: string, comments?: string) =>
    request(`/human-tasks/${taskId}/reject`, { method: 'POST', body: JSON.stringify({ comments }) }),

  decideTask: (taskId: string, decision: string, comments?: string) =>
    request(`/human-tasks/${taskId}/decide`, { method: 'POST', body: JSON.stringify({ decision, comments }) }),
};