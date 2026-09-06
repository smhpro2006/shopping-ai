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

const MAX_SLOTS = 3

function conditionSummary(offers) {
  if (!offers || offers.length === 0) return '—'
  const counts = {}
  for (const o of offers) {
    const c = o.condition || 'unknown'
    counts[c] = (counts[c] || 0) + 1
  }
  return Object.entries(counts)
    .map(([c, n]) => `${n} ${c}`)
    .join(' · ')
}

function cheapestOfCondition(offers, condition) {
  if (!offers || offers.length === 0) return null
  const filtered = offers.filter(o => o.condition === condition)
  if (filtered.length === 0) return null
  return filtered.reduce((a, b) => a.price < b.price ? a : b)
}

export default function ComparePage() {
  const { compareIds, toggleCompare, clearCompare } = useCompare()
  const [products, setProducts] = useState([])
  const [offersByProduct, setOffersByProduct] = useState({})
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (compareIds.length === 0) { setProducts([]); setOffersByProduct({}); return }
    setLoading(true)
    Promise.all(compareIds.map(id => api.getProduct(id)))
      .then(prods => {
        setProducts(prods)
        // Fetch offers for each product in parallel
        return Promise.all(prods.map(p => api.getProductOffers(p.id).then(o => [p.id, o || []])))
      })
      .then(pairs => {
        const map = {}
        for (const [id, offers] of pairs) map[id] = offers
        setOffersByProduct(map)
      })
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

  // Build the full list of columns: real products + placeholder slots
  const emptySlots = MAX_SLOTS - compareIds.length

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
          <div className="compare-grid" style={{ gridTemplateColumns: `repeat(${MAX_SLOTS}, 1fr)` }}>
            {/* Real product columns */}
            {products.map((product, i) => {
              const lowestPrice = product.lowest_price ?? null
              const offers = offersByProduct[product.id] || []
              const cheapestNew = cheapestOfCondition(offers, 'new')
              const cheapestUsed = cheapestOfCondition(offers, 'used')

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

                    {/* Retailers row */}
                    <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', fontSize: '0.85rem' }}>
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

                    {/* Condition breakdown row */}
                    <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', fontSize: '0.85rem' }}>
                      <div style={{
                        width: 90, flexShrink: 0, padding: '0.6rem 0.75rem',
                        fontWeight: 500, color: 'var(--text-muted)',
                        background: 'var(--bg)', borderRight: '1px solid var(--border)',
                        fontSize: '0.78rem',
                      }}>Condition</div>
                      <div style={{ flex: 1, padding: '0.6rem 0.75rem', fontSize: '0.8rem' }}>
                        {conditionSummary(offers)}
                      </div>
                    </div>

                    {/* New from row */}
                    <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', fontSize: '0.85rem' }}>
                      <div style={{
                        width: 90, flexShrink: 0, padding: '0.6rem 0.75rem',
                        fontWeight: 500, color: 'var(--text-muted)',
                        background: 'var(--bg)', borderRight: '1px solid var(--border)',
                        fontSize: '0.78rem',
                      }}>New from</div>
                      <div style={{ flex: 1, padding: '0.6rem 0.75rem', fontWeight: cheapestNew ? 600 : 400 }}>
                        {cheapestNew ? `$${cheapestNew.price.toFixed(2)}` : '—'}
                      </div>
                    </div>

                    {/* Used from row */}
                    <div style={{ display: 'flex', fontSize: '0.85rem' }}>
                      <div style={{
                        width: 90, flexShrink: 0, padding: '0.6rem 0.75rem',
                        fontWeight: 500, color: 'var(--text-muted)',
                        background: 'var(--bg)', borderRight: '1px solid var(--border)',
                        fontSize: '0.78rem',
                      }}>Used from</div>
                      <div style={{ flex: 1, padding: '0.6rem 0.75rem', fontWeight: cheapestUsed ? 600 : 400 }}>
                        {cheapestUsed ? `$${cheapestUsed.price.toFixed(2)}` : '—'}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}

            {/* Placeholder columns for empty slots */}
            {Array.from({ length: emptySlots }).map((_, i) => (
              <div key={`placeholder-${i}`} className="compare-col" style={{ opacity: 0.6 }}>
                <Link to="/" style={{ textDecoration: 'none' }}>
                  <div style={{
                    border: '2px dashed var(--border)',
                    borderRadius: 10,
                    padding: '2rem 1rem',
                    textAlign: 'center',
                    color: 'var(--text-muted)',
                    fontSize: '0.9rem',
                    cursor: 'pointer',
                    transition: 'border-color 0.15s, color 0.15s',
                    minHeight: 160,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                  }}>
                    <div style={{ fontSize: '1.5rem' }}>+</div>
                    <div>Add a product</div>
                  </div>
                </Link>
              </div>
            ))}
          </div>
        )}
    </div>
  )
}
