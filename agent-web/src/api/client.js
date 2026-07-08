import request from './request'

export const projectApi = {
  create: (data) => request.post('/projects', data),
  list: () => request.get('/projects'),
  get: (id) => request.get(`/projects/${id}`),
  delete: (id) => request.delete(`/projects/${id}`),
  startWorkflow: (id, level = 'L3') => request.post(`/projects/${id}/workflow/start`, null, { params: { level } }),
  confirm: (id, level, feedback) =>
    request.post(`/projects/${id}/workflow/confirm`, { level, feedback, approved: true }),
  reject: (id, level, feedback) =>
    request.post(`/projects/${id}/workflow/confirm`, { level, feedback, approved: false }),
}

export const messageApi = {
  list: (projectId) => request.get(`/projects/${projectId}/messages`),
  send: (projectId, content) => request.post(`/projects/${projectId}/messages`, { content }),
}

export const thinkingApi = {
  list: (projectId) => request.get(`/projects/${projectId}/thinking-logs`),
}

export const feedbackApi = {
  list: (projectId) => request.get(`/projects/${projectId}/feedbacks`),
  create: (projectId, data) => request.post(`/projects/${projectId}/feedbacks`, data),
}

export const logApi = {
  agentApi: (lines = 200) => request.get(`/logs/agent-api?lines=${lines}`),
}

export const stageLogApi = {
  list: (projectId) => request.get(`/projects/${projectId}/stages`),
}

export const authApi = {
  sendCode: (phone) => request.post('/auth/send-code', { phone }),
  login: (phone, code) => request.post('/auth/login', { phone, code }),
  register: (phone, code) => request.post('/auth/register', { phone, code }),
}
