import axios from 'axios'

const client = axios.create({
  baseURL: 'http://localhost:8080/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const projectApi = {
  create: (data) => client.post('/projects', data),
  list: () => client.get('/projects'),
  get: (id) => client.get(`/projects/${id}`),
  startWorkflow: (id, level = 'L3') => client.post(`/projects/${id}/workflow/start`, null, { params: { level } }),
  confirm: (id, level, feedback) =>
    client.post(`/projects/${id}/workflow/confirm`, { level, feedback, approved: true }),
  reject: (id, level, feedback) =>
    client.post(`/projects/${id}/workflow/confirm`, { level, feedback, approved: false }),
}
