import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useCompare } from '../App'

const LABEL_CLASS = {
  'Exact Match': 'label-exact',
  'Very Similar': 'label-similar-high',
  'Similar': 'label-similar',
  'Alternative': 'label-alt',
}

const ROWS = [
  { label: 'Brand',    key: 'brand' },
  { label: 'Model',    key: 'model' },
  { label: 'Category', key: 'category' },
]

export default function ComparePage() {
  const { compareIds, toggleCompare, clearCompare } = useCompare()
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (compareIds.length === 0) { setProducts([]); return }
    setLoading(true)
    Promise.all(compareIds.map(id => api.getProduct(id)))
      .then(setProducts)
      .finally(() => setLoading(false))
  }, [compareIds])

  if (compareIds.length === 0) {
    return (
      <div className="page">
        <div className="empty-state">
          <div className="icon">⚖️</div>
          <p>No products selected for comparison.</p>
          <p style={{ marginTop: '0.4rem', fontSize: '0.85rem' }}>
            Use the Compare button on any product card to add up to 3 products.
          </p>
          <Link to="/" className="btn btn-primary" style={{ marginTop: '1rem', display: 'inline-flex' }}>
            Browse products
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page-wide">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Compare products</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            {compareIds.length} of 3 selected
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link to="/" className="btn btn-ghost btn-sm">← Add more</Link>
          <button className="btn btn-ghost btn-sm" onClick={clearCompare}>Clear all</button>
        </div>
      </div>

      {loading
        ? <div className="loading"><div className="spinner" /></div>
        : (
          <div className="compare-grid">
            {products.map((product, i) => {
              const lowestPrice = product.lowest_price ?? null
              return (
                <div key={product.id} className="compare-col">
                  <div className="compare-col-header">
                    <div className="product-img compare-col-header .product-img" style={{
                      width: 80, height: 80, margin: '0 auto 0.75rem',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '2rem', background: 'var(--bg)',
                      border: '1px solid var(--border)', borderRadius: 8,
                    }}>
                      {product.image_url
                        ? <img src={product.image_url} alt={product.name} style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 8 }} />
                        : '📦'}
                    </div>
                    <Link to={`/product/${product.id}`} className="compare-col-name" style={{ display: 'block', color: 'inherit' }}>
                      {product.name}
                    </Link>
                    <div className="compare-col-meta">{product.brand}</div>
                    {lowestPrice != null
                      ? <div className="compare-col-price">${lowestPrice.toFixed(2)}</div>
                      : <div style={{ marginTop: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>No price</div>
                    }
                    <button
                      className="btn btn-ghost btn-sm"
                      style={{ marginTop: '0.75rem' }}
                      onClick={() => toggleCompare(product.id)}
                    >
                      Remove
                    </button>
                  </div>

                  <div>
                    {ROWS.map(({ label, key }) => (
                      <div key={key} style={{ display: 'flex', borderBottom: '1px solid var(--border)', fontSize: '0.85rem' }}>
                        <div style={{
                          width: 90, flexShrink: 0, padding: '0.6rem 0.75rem',
                          fontWeight: 500, color: 'var(--text-muted)',
                          background: 'var(--bg)', borderRight: '1px solid var(--border)',
                          fontSize: '0.78rem',
                        }}>{label}</div>
                        <div style={{ flex: 1, padding: '0.6rem 0.75rem' }}>{product[key] ?? '—'}</div>
                      </div>
                    ))}
                    <div style={{ display: 'flex', fontSize: '0.85rem' }}>
                      <div style={{
                        width: 90, flexShrink: 0, padding: '0.6rem 0.75rem',
                        fontWeight: 500, color: 'var(--text-muted)',
                        background: 'var(--bg)', borderRight: '1px solid var(--border)',
                        fontSize: '0.78rem',
                      }}>Retailers</div>
                      <div style={{ flex: 1, padding: '0.6rem 0.75rem' }}>
                        {product.retailer_count > 0 ? `${product.retailer_count} retailer${product.retailer_count !== 1 ? 's' : ''}` : '—'}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
    </div>
  )
}
