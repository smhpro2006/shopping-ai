import { useState } from 'react'
import ProductCard from '../components/ProductCard'
import { api } from '../api'

const CATEGORIES = ['', 'Headphones', 'Earbuds', 'Speakers', 'Keyboards', 'Mice']

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [minPrice, setMinPrice] = useState('')
  const [maxPrice, setMaxPrice] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [meta, setMeta] = useState(null)
  const [aiData, setAiData] = useState(null)

  const doSearch = async (p = 1) => {
    if (query.trim().length < 2) { setError('Enter at least 2 characters.'); return }
    setError('')
    setLoading(true)
    try {
      const data = await api.search(query.trim(), {
        category: category || undefined,
        minPrice: minPrice ? Number(minPrice) : undefined,
        maxPrice: maxPrice ? Number(maxPrice) : undefined,
        page: p,
      })
      setResults(data.results)
      setMeta({ total: data.total, page: data.page, limit: data.limit })
      setPage(p)
      setAiData(data.ai_enabled ? { summary: data.ai_summary, intent: data.ai_intent } : null)
    } catch {
      setError('Search failed. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const totalPages = meta ? Math.ceil(meta.total / meta.limit) : 0

  const intentTags = aiData?.intent ? (() => {
    const tags = []
    const i = aiData.intent
    if (i.brand) tags.push({ label: `Brand: ${i.brand}`, type: 'brand' })
    if (i.category) tags.push({ label: `Category: ${i.category}`, type: 'category' })
    if (i.min_price != null && i.max_price != null) tags.push({ label: `$${i.min_price}–$${i.max_price}`, type: 'price' })
    else if (i.max_price != null) tags.push({ label: `Under $${i.max_price}`, type: 'price' })
    else if (i.min_price != null) tags.push({ label: `Over $${i.min_price}`, type: 'price' })
    if (i.model) tags.push({ label: `Model: ${i.model}`, type: 'model' })
    ;(i.features || []).forEach(f => tags.push({ label: f, type: 'feature' }))
    return tags
  })() : []

  return (
    <div className="page">
      <div className="hero">
        <h1>Find the best <span>deals</span></h1>
        <p>Search by brand, model, or product name</p>
        <div className="search-bar">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && doSearch()}
            placeholder="e.g. Sony WH-1000XM5, AirPods Pro..."
            autoFocus
          />
          <button className="btn btn-primary" onClick={() => doSearch()} disabled={loading}>
            {loading ? <span className="spinner" style={{ width: 18, height: 18 }} /> : 'Search'}
          </button>
        </div>
      </div>

      <div className="filters">
        <div className="field">
          <label>Category</label>
          <select value={category} onChange={e => setCategory(e.target.value)}>
            {CATEGORIES.map(c => <option key={c} value={c}>{c || 'All categories'}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Min price ($)</label>
          <input type="number" value={minPrice} onChange={e => setMinPrice(e.target.value)} placeholder="0" min="0" />
        </div>
        <div className="field">
          <label>Max price ($)</label>
          <input type="number" value={maxPrice} onChange={e => setMaxPrice(e.target.value)} placeholder="Any" min="0" />
        </div>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {aiData?.summary && (
        <div className="ai-summary">
          <span className="ai-badge">AI</span>
          {aiData.summary}
        </div>
      )}

      {intentTags.length > 0 && (
        <div className="ai-intent-tags">
          {intentTags.map((tag, i) => (
            <span key={i} className={`intent-tag intent-tag--${tag.type}`}>{tag.label}</span>
          ))}
        </div>
      )}

      {results !== null && (
        <>
          <div className="results-header">
            <span>{meta?.total ?? 0} result{meta?.total !== 1 ? 's' : ''} for "<strong>{query}</strong>"</span>
            {meta && <span>Page {meta.page} of {totalPages || 1}</span>}
          </div>
          <div className="results-grid">
            {results.length === 0
              ? (
                <div className="empty-state">
                  <div className="icon">🔍</div>
                  <p>No products matched your query.</p>
                  <p style={{ marginTop: '0.4rem', fontSize: '0.85rem' }}>Try searching by brand or model number.</p>
                </div>
              )
              : results.map(p => <ProductCard key={`${p.id}-${p.store}`} product={p} />)
            }
          </div>
          {totalPages > 1 && (
            <div className="pagination">
              <button className="page-btn" onClick={() => doSearch(page - 1)} disabled={page <= 1}>←</button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map(n => (
                <button key={n} className={`page-btn ${n === page ? 'active' : ''}`} onClick={() => doSearch(n)}>{n}</button>
              ))}
              <button className="page-btn" onClick={() => doSearch(page + 1)} disabled={page >= totalPages}>→</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
