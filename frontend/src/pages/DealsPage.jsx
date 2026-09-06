import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function DealsPage() {
  const [deals, setDeals] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getDeals()
      .then(data => setDeals(data || []))
      .catch(() => setError('Failed to load deals.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading"><div className="spinner" /></div>

  return (
    <div className="page">
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.25rem' }}>Best Deals</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
        Products with the widest price spread across retailers — buy from the cheapest.
      </p>

      {error && <div className="error-msg">{error}</div>}

      {!error && deals.length === 0 && (
        <div className="empty-state">
          <div className="icon">🏷️</div>
          <p>No deals available yet.</p>
          <p style={{ marginTop: '0.4rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Deals appear once we have price data from multiple retailers. Check back after the next collection run.
          </p>
        </div>
      )}

      {deals.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {deals.map((deal, i) => (
            <Link
              key={deal.id}
              to={`/product/${deal.id}`}
              style={{ textDecoration: 'none', color: 'inherit' }}
            >
              <div style={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 10,
                padding: '1rem 1.25rem',
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
                transition: 'box-shadow 0.15s',
                cursor: 'pointer',
              }}
                onMouseEnter={e => e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)'}
                onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}
              >
                {/* Rank badge */}
                <div style={{
                  width: 32, height: 32, borderRadius: '50%',
                  background: i === 0 ? '#f59e0b' : i === 1 ? '#9ca3af' : i === 2 ? '#b45309' : 'var(--bg)',
                  color: i < 3 ? '#fff' : 'var(--text-muted)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontWeight: 700, fontSize: '0.85rem', flexShrink: 0,
                }}>
                  {i + 1}
                </div>

                {/* Product info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.95rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {deal.name}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                    {deal.brand} · {deal.category}
                  </div>
                </div>

                {/* Price info */}
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <div style={{ fontWeight: 700, color: 'var(--primary)', fontSize: '1.05rem' }}>
                    ${deal.lowest_price.toFixed(2)}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    up to ${deal.highest_price.toFixed(2)}
                  </div>
                </div>

                {/* Spread badge */}
                <div style={{
                  background: '#d1fae5', color: '#065f46',
                  borderRadius: 6, padding: '0.3rem 0.65rem',
                  fontSize: '0.82rem', fontWeight: 700, flexShrink: 0,
                  textAlign: 'center',
                }}>
                  <div>{deal.price_spread_pct}% spread</div>
                  <div style={{ fontWeight: 400, fontSize: '0.72rem' }}>{deal.retailer_count} retailers</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
