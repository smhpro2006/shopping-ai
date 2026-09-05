import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'

const LABEL_CLASS = {
  'Exact Match': 'label-exact',
  'Very Similar': 'label-similar-high',
  'Similar': 'label-similar',
  'Alternative': 'label-alt',
}

export default function ProductPage() {
  const { id } = useParams()
  const [product, setProduct] = useState(null)
  const [offers, setOffers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.getProduct(id), api.getProductOffers(id)])
      .then(([p, o]) => { setProduct(p); setOffers(o) })
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
            <div style={{ marginTop: '1rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>No offers available</div>
          )}
        </div>
      </div>

      {offers.length > 0 && (
        <div className="section-card">
          <div className="section-card-header">
            Price comparison · {offers.length} retailer{offers.length !== 1 ? 's' : ''}
          </div>
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
                    <td style={{ textTransform: 'capitalize', color: 'var(--text-muted)' }}>
                      {offer.condition ?? '—'}
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
        </div>
      )}
    </div>
  )
}
