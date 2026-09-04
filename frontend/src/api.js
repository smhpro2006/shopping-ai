const BASE = '/api'

function authHeader() {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function req(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...authHeader(), ...options.headers },
    ...options,
  })
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  search: (q, { category, minPrice, maxPrice, page = 1, limit = 20 } = {}) => {
    const params = new URLSearchParams({ q, page, limit })
    if (category) params.set('category', category)
    if (minPrice != null) params.set('min_price', minPrice)
    if (maxPrice != null) params.set('max_price', maxPrice)
    return req(`/search?${params}`)
  },

  register: (email, password) =>
    req('/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }),

  login: (email, password) =>
    req('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),

  me: () => req('/auth/me'),

  products: () => req('/products'),

  createProduct: (data) =>
    req('/products', { method: 'POST', body: JSON.stringify(data) }),

  updateProduct: (id, data) =>
    req(`/products/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  deleteProduct: (id) =>
    req(`/products/${id}`, { method: 'DELETE' }),
}
