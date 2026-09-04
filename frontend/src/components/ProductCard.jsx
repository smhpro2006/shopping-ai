export default function ProductCard({ product }) {
  const { name, brand, model, category, price, store, image_url, match_score } = product

  return (
    <div className="product-card">
      <div className="product-img">
        {image_url
          ? <img src={image_url} alt={name} style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 8 }} />
          : '📦'}
      </div>
      <div className="product-info">
        <div className="product-name">{name}</div>
        <div className="product-meta">{brand} · {model} · {category}</div>
        <div className="product-footer">
          <span className="product-price">${price.toFixed(2)}</span>
          <span className="product-store">{store}</span>
          {match_score != null && (
            <div className="score-badge">
              <div className="score-bar">
                <div className="score-fill" style={{ width: `${match_score}%` }} />
              </div>
              {match_score}%
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
