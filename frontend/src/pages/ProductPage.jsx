import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'

const CONDITION_BADGE = {
  new:         { background: '#d1fae5', color: '#065f46' },
  used:        { background: '#fef3c7', color: '#92400e' },
  refurbished: { background: '#dbeafe', color: '#1e40af' },
  unknown:     { background: '#f3f4f6', color: '#6b7280' },
}

const BADGE_BASE = {
  display: 'inline-block',
  padding: '2px 8px',
  borderRadius: 4,
  fontSize: '0.75rem',
  fontWeight: 600,
  textTransform: 'capitalize',
}

function ConditionBadge({ condition }) {
  const key = (condition || 'unknown').toLowerCase()
  const style = CONDITION_BADGE[key] || CONDITION_BADGE.unknown
  return (
    <span style={{ ...BADGE_BASE, ...style }}>{key}</span>
  )
}

export default function ProductPage() {
  const { id } = useParams()
  const [product, setProduct] = useState(null)
  const [offers, setOffers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.getProduct(id), api.getProductOffers(id)])
      .then(([p, o]) => { setProduct(p); setOffers(o || []) })
      .catch(() => setError('Product not found.'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="loading"><div className="spinner" /></div>

  if (error || !product) return (
    <div className="page">
      <div className="error-msg">{error || 'Product not found.'}</div>
      <Link to="/" className="nav-link" style={{ marginTop: '1rem', display: 'inline-block' }}>← Back to search</Link>
    </div>
  )

  const lowestOffer = offers.length > 0
    ? offers.reduce((a, b) => a.price < b.price ? a : b)
    : null

  return (
    <div className="page">
      <Link to="/" className="nav-link" style={{ display: 'inline-block', marginBottom: '1.25rem' }}>← Back to search</Link>

      <div className="product-detail-header">
        <div className="product-img product-img-lg">
          {product.image_url
            ? <img src={product.image_url} alt={product.name} style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 8 }} />
            : '📦'}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="product-meta" style={{ marginBottom: '0.4rem' }}>
            {product.brand} · {product.category}
          </div>
          <h1 className="product-detail-name">{product.name}</h1>
          <div className="product-meta" style={{ marginTop: '0.25rem' }}>Model: {product.model}</div>
          {lowestOffer && (
            <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'baseline', gap: '0.75rem' }}>
              <span className="product-price" style={{ fontSize: '1.6rem' }}>
                ${lowestOffer.price.toFixed(2)}
              </span>
              <span style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>
                lowest — {lowestOffer.retailer?.name}
              </span>
            </div>
          )}
          {!lowestOffer && (
            <div style={{ marginTop: '1rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              No current price data available.
            </div>
          )}
        </div>
      </div>

      <div className="section-card">
        <div className="section-card-header">
          Price comparison{offers.length > 0 ? ` · ${offers.length} retailer${offers.length !== 1 ? 's' : ''}` : ''}
        </div>

        {offers.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', padding: '1rem 0' }}>
            No current offers. Check back later — we refresh prices every 12 hours.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Retailer</th>
                <th>Price</th>
                <th>Condition</th>
                <th>Availability</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {offers
                .slice()
                .sort((a, b) => a.price - b.price)
                .map((offer, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500 }}>{offer.retailer?.name ?? 'Unknown'}</td>
                    <td style={{ fontWeight: 700, color: 'var(--primary)' }}>${offer.price.toFixed(2)}</td>
                    <td>
                      <ConditionBadge condition={offer.condition} />
                    </td>
                    <td style={{ color: 'var(--text-muted)' }}>{offer.availability ?? '—'}</td>
                    <td>
                      {offer.url && (
                        <a href={offer.url} target="_blank" rel="noopener noreferrer" className="offer-link">
                          Buy →
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
