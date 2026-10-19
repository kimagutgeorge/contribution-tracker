const TOKEN_KEY = 'ct_admin_token'

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* storage blocked: the session just will not persist */
  }
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let res
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError('Could not reach the server. Check your connection.', 0)
  }

  if (res.status === 204) return null
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(data.error || 'Something went wrong.', res.status)
  return data
}

export const api = {
  login: (username, password) => request('/auth/login', { method: 'POST', body: { username, password } }),
  me: () => request('/auth/me'),
  list: () => request('/contributions'),
  create: (item) => request('/contributions', { method: 'POST', body: item }),
  update: (id, item) => request(`/contributions/${id}`, { method: 'PUT', body: item }),
  remove: (id) => request(`/contributions/${id}`, { method: 'DELETE' }),
  addPayment: (id, payment) => request(`/contributions/${id}/payments`, { method: 'POST', body: payment }),
  updatePayment: (id, payment) => request(`/payments/${id}`, { method: 'PUT', body: payment }),
  removePayment: (id) => request(`/payments/${id}`, { method: 'DELETE' }),
}
