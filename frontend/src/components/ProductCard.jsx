import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useCompare } from '../App'

const LABEL_CLASS = {
  'Exact Match': 'label-exact',
  'Very Similar': 'label-similar-high',
  'Similar': 'label-similar',
  'Alternative': 'label-alt',
}

export default function ProductCard({ product }) {
  const {
    id, name, brand, model, category, image_url,
    match_score, match_label,
    lowest_price, price, store,
    retailer_count = 0, offers = [],
  } = product

  const [expanded, setExpanded] = useState(false)
  const { compareIds, toggleCompare } = useCompare()
  const inCompare = compareIds.includes(id)
  const compareFull = compareIds.length >= 3 && !inCompare

  const displayPrice = lowest_price ?? price
  const labelClass = LABEL_CLASS[match_label] ?? 'label-alt'

  return (
    <div className="product-card">
      <div className="product-img">
        {image_url
          ? <img src={image_url} alt={name} style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 8 }} />
          : '📦'}
      </div>
      <div className="product-info">
        {match_label && (
          <span className={`match-label ${labelClass}`}>{match_label}</span>
        )}
        <Link to={`/product/${id}`} className="product-name" style={{ display: 'block', color: 'inherit' }}>{name}</Link>
        <div className="product-meta">{brand} · {model} · {category}</div>
        <div className="product-footer">
          {displayPrice != null
            ? <span className="product-price">${displayPrice.toFixed(2)}</span>
            : <span className="product-price no-price">No price</span>
          }
          {retailer_count > 0
            ? <span className="retailer-count">{retailer_count} retailer{retailer_count !== 1 ? 's' : ''}</span>
            : store && <span className="product-store">{store}</span>
          }
          {match_score != null && (
            <div className="score-badge">
              <div className="score-bar">
                <div className="score-fill" style={{ width: `${match_score}%` }} />
              </div>
              {match_score}%
            </div>
          )}
        </div>

        <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            className={`btn btn-sm ${inCompare ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => toggleCompare(id)}
            disabled={compareFull}
            title={compareFull ? 'Remove a product to add another' : inCompare ? 'Remove from compare' : 'Add to compare'}
          >
            {inCompare ? '✓ Comparing' : compareFull ? 'Compare full' : 'Compare'}
          </button>
        </div>

        {offers.length > 0 && (
          <button className="offers-toggle" onClick={() => setExpanded(v => !v)}>
            {expanded ? 'Hide offers ▲' : `Show ${offers.length} offer${offers.length !== 1 ? 's' : ''} ▼`}
          </button>
        )}

        {expanded && (
          <div className="offers-list">
            {offers.map((offer, i) => (
              <div key={i} className="offer-row">
                <span className="offer-retailer">{offer.retailer?.name ?? 'Unknown'}</span>
                <span className="offer-price">${offer.price.toFixed(2)}</span>
                {offer.availability && (
                  <span className="offer-avail">{offer.availability}</span>
                )}
                {offer.url && (
                  <a className="offer-link" href={offer.url} target="_blank" rel="noopener noreferrer">
                    View →
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
