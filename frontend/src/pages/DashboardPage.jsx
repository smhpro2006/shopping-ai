import { useState, useEffect } from 'react'
import { useAuth } from '../App'
import { api } from '../api'

const EMPTY_FORM = { brand: '', model: '', name: '', category: '', price: '', store: '', image_url: '' }

export default function DashboardPage() {
  const { user } = useAuth()
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState(EMPTY_FORM)
  const [adding, setAdding] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      const data = await api.products()
      setProducts(data.products)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleAdd = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.brand || !form.model || !form.name || !form.category || !form.price || !form.store) {
      setError('All fields except image URL are required.')
      return
    }
    setAdding(true)
    try {
      const data = await api.createProduct({ ...form, price: Number(form.price), image_url: form.image_url || null })
      if (data.detail) { setError(data.detail); return }
      setProducts(prev => [...prev, data])
      setForm(EMPTY_FORM)
      setShowForm(false)
    } catch {
      setError('Failed to add product.')
    } finally {
      setAdding(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this product?')) return
    await api.deleteProduct(id)
    setProducts(prev => prev.filter(p => p.id !== id))
  }

  const handleChange = (field) => (e) => setForm(prev => ({ ...prev, [field]: e.target.value }))

  return (
    <div className="page-wide">
      <div className="dash-header">
        <div>
          <h1>Dashboard</h1>
          <p>{user?.email}</p>
        </div>
      </div>

      <div className="section-card">
        <div className="section-card-header">
          Products
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm(v => !v)}>
            {showForm ? 'Cancel' : '+ Add product'}
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleAdd} className="add-product-form" style={{ borderBottom: '1px solid var(--border)' }}>
            {error && <div className="error-msg" style={{ gridColumn: '1 / -1' }}>{error}</div>}
            {[
              ['brand', 'Brand', 'Sony'],
              ['model', 'Model', 'WH-1000XM5'],
              ['name', 'Full name', 'Sony WH-1000XM5 Headphones'],
              ['category', 'Category', 'Headphones'],
              ['store', 'Store', 'Amazon'],
            ].map(([field, label, placeholder]) => (
              <div className="field" key={field}>
                <label>{label}</label>
                <input value={form[field]} onChange={handleChange(field)} placeholder={placeholder} />
              </div>
            ))}
            <div className="field">
              <label>Price ($)</label>
              <input type="number" value={form.price} onChange={handleChange('price')} placeholder="349.99" step="0.01" min="0" />
            </div>
            <div className="field">
              <label>Image URL (optional)</label>
              <input value={form.image_url} onChange={handleChange('image_url')} placeholder="https://..." />
            </div>
            <div className="field" style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={adding}>
                {adding ? 'Adding…' : 'Add product'}
              </button>
            </div>
          </form>
        )}

        {loading
          ? <div className="loading"><div className="spinner" /></div>
          : (
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Category</th>
                  <th>Store</th>
                  <th>Price</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {products.length === 0
                  ? <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>No products yet.</td></tr>
                  : products.map(p => (
                    <tr key={p.id}>
                      <td>
                        <div style={{ fontWeight: 500 }}>{p.name}</div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{p.brand} · {p.model}</div>
                      </td>
                      <td>{p.category}</td>
                      <td>{p.store}</td>
                      <td style={{ fontWeight: 600 }}>${p.price.toFixed(2)}</td>
                      <td>
                        <button className="btn btn-danger btn-sm" onClick={() => handleDelete(p.id)}>Delete</button>
                      </td>
                    </tr>
                  ))
                }
              </tbody>
            </table>
          )
        }
      </div>
    </div>
  )
}
