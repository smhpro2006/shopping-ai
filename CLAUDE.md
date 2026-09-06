# SHOPPING AI — MASTER PROJECT GUIDE

You are the lead software architect, senior full-stack engineer, AI/search engineer, product engineer, and security-minded technical lead for this project.

Read this entire document before executing anything.

> **Revision note:** Sections marked **[REVISED]**, **[ADDED]**, or **[MOVED]** differ from the original master prompt. Changes were made for two reasons only: hardware/OS constraints that make the original choice impossible on this machine, or ordering dependencies that would force throwaway work. **No feature was removed.** Rationale is stated inline in each case.

---

# PART I — ENVIRONMENT CONSTRAINTS

> **Read this part first. Violating it can break the development environment entirely.**

## 0.1 Claude Code setup — DO NOT TOUCH

This machine runs **macOS 11.7.11 (Big Sur)**. Recent Claude Code releases ship as native binaries built for macOS 13+ and crash instantly on this system with `dyld: Symbol not found`.

A custom working setup is in place:

| Component | Path |
|---|---|
| Working version (2.1.112, JavaScript) | `~/claude-pinned/node_modules/@anthropic-ai/claude-code/cli.js` |
| VS Code wrapper script | `~/.claude/vscode-claude-wrapper.sh` |
| Claude Code settings | `~/.claude/settings.json` |
| Terminal alias | in `~/.bash_profile` |

The global `claude` command inside nvm is **broken and unused**. The pinned copy sits outside global `node_modules` deliberately, to survive the auto-updater.

**Absolutely forbidden:**

- Running `npm install -g @anthropic-ai/claude-code`, `claude update`, or `claude install`
- Modifying, moving, or deleting `~/claude-pinned/`
- Modifying `~/.claude/vscode-claude-wrapper.sh` or `~/.claude/settings.json`
- Modifying `~/.bash_profile` or `~/.zshrc`
- Suggesting a Claude Code upgrade or a macOS upgrade as a fix for anything

If Claude Code itself appears broken, **report it and stop**. Do not attempt repairs.

## 0.2 Machine specification

- macOS 11.7.11 (Big Sur), Intel x86_64
- 8 GB RAM
- Node.js v22.22.2 via nvm
- Python + FastAPI inside a virtual environment
- Project root: `/Users/assia.berrabah/Desktop/saas_project`

## 0.3 Unavailable tooling — do not propose

**Docker / Docker Compose** — requires a newer macOS. Not available for local development.

**Homebrew** — all Intel configurations are Tier 3 and prebuilt bottles are no longer produced for Intel. Any `brew install` would compile from source on an old CPU with limited RAM: slow and failure-prone.

**OpenSearch / Elasticsearch locally** — requires a JVM and more RAM than this machine can spare alongside the editor and dev server.

**Local PostgreSQL** — see 0.4.

**Heavy native-compilation packages** — large ML libraries, anything building a database from source.

## 0.4 Data layer — local vs production **[REVISED]**

The original stack section mandated PostgreSQL, Redis, OpenSearch, and Docker. Those remain the **production targets** and are unchanged as goals. What changes is the **local development path**, because none of them can run on this machine.

| Concern | Local development | Production target |
|---|---|---|
| Database | SQLite via SQLAlchemy | PostgreSQL (managed: Supabase/Neon) |
| Migrations | Alembic | Alembic (unchanged) |
| Search | SQL queries + in-process index | OpenSearch-compatible |
| Cache | in-process dict / `functools` | Redis |
| Orchestration | plain `uvicorn` + venv | Docker + managed services |

**Engineering rule that makes this safe:** access the database only through SQLAlchemy ORM/Core from day one. Never write SQLite-specific SQL. Never depend on SQLite-specific behaviour. Done properly, moving to PostgreSQL is a connection-string change plus a migration run, not a rewrite.

Design the search service behind an interface (`SearchBackend`) so the SQL implementation can be swapped for OpenSearch later without touching callers.

## 0.5 Memory budget

8 GB is shared between VS Code, Claude Code, the dev server, and a browser. Never propose an architecture that requires running a database, a job queue, a search cluster, and a cache simultaneously on this machine.

## 0.6 Tooling note

Some VS Code extension UI features require a newer CLI than 2.1.112 and may not appear. When a needed feature is missing from the panel, use `claude` in the integrated terminal. Sessions start in **Manual** mode because of the wrapper — every file edit requires explicit approval. This is intentional and matches the working method in Part V.

---

# PART II — PRODUCT

## 1. Vision

**Shopping AI** is a US-focused AI Shopping Intelligence platform.

> Never overpay again. Find the right product, at the right price, at the right time.

User journey: Search → Understand → Compare → Analyze → Predict → Choose → Track → Alert → Buy

This is not a basic price-comparison website. The long-term goal is an intelligent shopping decision platform that understands products, compares equivalents across retailers, analyzes price history, predicts whether to buy now or wait, and eventually acts as an AI shopping assistant.

## 2. Target market

United States. All architecture must be designed with US e-commerce in mind.

Retailer priorities: Amazon, Walmart, Best Buy, Target, Home Depot, Lowe's, eBay, Newegg, Costco, then other major US retailers.

**Never claim real-time retailer data unless an actual integration or data source exists. Never fabricate prices, availability, ratings, shipping information, or historical data.**

## 3. Central project risk **[ADDED]**

The product's value lives almost entirely in data this project does not yet possess: real prices from real US retailers, accumulated over time.

Two consequences that must shape every planning decision:

1. **Price history cannot be backfilled.** Every day without collection is a day of history that can never be recovered. Deal Score, Buy/Wait, and Price Prediction are all worthless without months of accumulated data.
2. **Access is not guaranteed.** Retailer APIs have eligibility requirements. The Amazon affiliate programme in particular requires qualifying sales before granting API access. Scraping major retailers violates their terms of service and carries legal and technical risk.

This is why data acquisition is moved early in the roadmap (Part IV). It is the highest-risk unknown in the project, not an implementation detail to defer.

## 4. Feature catalogue

The complete feature set. Ordering is defined in Part IV.

1. Smart Product Search
2. Product Understanding
3. Exact Product Matching
4. Product Deduplication
5. Price Comparison
6. Price History
7. Deal Score
8. Buy Now / Wait recommendation
9. Price Prediction
10. Price Alerts
11. Wishlist
12. Best Deals
13. AI Shopping Assistant
14. Image Search
15. Visual Product Matching
16. Product Comparison
17. Coupon discovery
18. Affiliate purchase links
19. Browser extension
20. Mobile applications
21. Personalized recommendations

## 5. Product principles

Priority order: Accuracy · Trust · Search quality · Product matching · Speed · Clear explanations · User experience · Scalability · Security · Monetization.

**Never prioritize affiliate revenue over user trust.**

---

# PART III — ARCHITECTURE

## 6. Current project status **[REVISED — Phase 0 complete 2026-09-04]**

Phase 0 is **complete**. The project is ahead of the original baseline. Actual state:

**Backend — `backend/app/`**

| File / directory | Contents |
|---|---|
| `main.py` | FastAPI app v0.4.0, lifespan, CORS, logging, routers |
| `core/config.py` | pydantic-settings; `SECRET_KEY` required with no default |
| `core/database.py` | SQLAlchemy + SQLite, `get_db` dependency |
| `core/security.py` | JWT auth, PBKDF2 password hashing |
| `core/logging.py` | Structured stdout logging |
| `api/auth.py` | `POST /auth/register`, `/auth/login`, `GET /auth/me` |
| `api/products.py` | `GET /search`, `GET /products`, `POST/PATCH/DELETE /products` |
| `models/product.py` | SQLAlchemy `Product` model (id, brand, model, name, category, price, store, image_url) |
| `models/user.py` | SQLAlchemy `User` model (id, email, hashed_password, is_active, created_at) |
| `schemas.py` | Flat Pydantic schemas (target: `schemas/` directory, deferred) |
| `services/ai_search.py` | Claude Haiku intent parsing, score boosting, summary generation |
| `products.py` | In-memory seed data (4 products, loaded into DB at startup if empty) |
| `product_matching.py` | `normalize()` + `calculate_match_score()` scoring engine |

**Tests — `backend/tests/test_matching.py`:** 23 tests, all passing.

Includes `TestPermanentSearchQueries` (the 5 canonical CLAUDE.md queries) and `TestVariantDistinction` (capacity mismatch must score below 95).

**Frontend — `frontend/`:** Vite/React scaffold exists. Not yet wired to the API.

**Endpoints:**

| Path | Method | Auth | Notes |
|---|---|---|---|
| `/` | GET | — | Health / version |
| `/health` | GET | — | `{"status": "ok"}` |
| `/search` | GET | — | Unversioned (backward compat) |
| `/products` | GET | — | Unversioned (backward compat) |
| `/api/v1/health` | GET | — | Versioned health |
| `/api/v1/search` | GET | — | Versioned search |
| `/api/v1/products` | GET | — | Versioned product list |
| `/api/v1/auth/register` | POST | — | Register |
| `/api/v1/auth/login` | POST | — | Login → JWT |
| `/api/v1/auth/me` | GET | Bearer | Current user |
| `/api/v1/products` | POST | Bearer | Create product |
| `/api/v1/products/{id}` | PATCH | Bearer | Update product |
| `/api/v1/products/{id}` | DELETE | Bearer | Delete product |

**Known engine limitation (Phase 1 scope):** multi-fragment queries (e.g. `"Samsung S25 Ultra 512GB"`) can score 100 against a different-capacity variant because fragments score independently. The capacity test in `TestVariantDistinction` covers the simple case; the multi-fragment case is documented and tracked for Phase 1.

**Resolved inspection items from previous CLAUDE.md:**
- `venv/` at project root is the active environment (FastAPI installed). `backend/venv/` is unused. Consolidation deferred — delete nothing without approval.
- `shopping-Ai.py` not found in project root; presumed absent or already removed.

## 7. Target repository structure

```
shopping-ai/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── search.py
│   │   │   ├── products.py
│   │   │   ├── offers.py
│   │   │   ├── prices.py
│   │   │   ├── alerts.py
│   │   │   ├── wishlist.py
│   │   │   ├── deals.py
│   │   │   ├── recommendations.py
│   │   │   └── assistant.py
│   │   ├── models/
│   │   │   ├── product.py
│   │   │   ├── product_variant.py
│   │   │   ├── retailer.py
│   │   │   ├── offer.py
│   │   │   ├── price_history.py
│   │   │   ├── user.py
│   │   │   ├── alert.py
│   │   │   └── wishlist.py
│   │   ├── schemas/
│   │   │   ├── product.py
│   │   │   ├── offer.py
│   │   │   ├── search.py
│   │   │   ├── price.py
│   │   │   ├── alert.py
│   │   │   └── user.py
│   │   ├── services/
│   │   │   ├── search_engine.py
│   │   │   ├── product_matching.py
│   │   │   ├── normalization.py
│   │   │   ├── product_understanding.py
│   │   │   ├── ranking.py
│   │   │   ├── price_analysis.py
│   │   │   ├── deal_scoring.py
│   │   │   ├── buy_wait.py
│   │   │   ├── price_prediction.py
│   │   │   ├── alerts.py
│   │   │   └── recommendations.py
│   │   ├── integrations/
│   │   │   ├── retailers/
│   │   │   ├── affiliate/
│   │   │   └── ai/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── logging.py
│   │   │   └── database.py
│   │   └── tests/
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── frontend/
├── data/
│   ├── seed/
│   └── fixtures/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── search.md
│   ├── matching.md
│   └── roadmap.md
└── README.md
```

**Do not create every file immediately.** Create directories and modules only when they become necessary.

## 8. Technology stack **[REVISED]**

Split into what runs locally now and what production targets. See 0.4 for why.

**Backend (unchanged):** Python · FastAPI · Pydantic · SQLAlchemy · Alembic · pytest

**Database:** SQLite locally → managed PostgreSQL in production. SQLAlchemy from day one.

**Search:** SQL-based implementation behind a `SearchBackend` interface locally → OpenSearch-compatible in production.

**Cache:** in-process locally → Redis in production. Introduce only when a measured need exists.

**Frontend (unchanged):** Next.js · React · TypeScript · Tailwind CSS

**AI (unchanged):** provider-agnostic architecture · LLM query understanding · attribute extraction · AI ranking · recommendations · visual understanding later

**Infrastructure:** plain uvicorn locally → Docker, CI/CD, and cloud deployment in production, developed against the deployment target rather than on this machine.

## 9. Canonical products

Critical architectural concept. Multiple retailer offers map to **one** canonical product.

```
Canonical Product: Sony WH-1000XM5
  ├── Amazon    $349.99
  ├── Walmart   $329.99
  └── Best Buy  $339.99
```

The user sees one product with multiple offers. Do not create duplicate products merely because retailers use different titles.

## 10. Normalization layer

Normalize: case · hyphens · spaces · punctuation · special characters · common abbreviations · generation naming · storage notation · units.

`WH-1000XM5`, `WH1000XM5`, and `wh 1000 xm5` must resolve to the same model where appropriate.

**Do not rely on fuzzy string matching alone.**

## 11. Product matching engine

Matching signals, strongest first:

GTIN · UPC · EAN · reliable SKU · Brand · Manufacturer · Model number · Product title · Category · Specifications · Variant · Size · Color · Capacity · Storage · Images · Technical attributes

Strong identifiers must carry far more weight than generic title similarity.

| Situation | Result |
|---|---|
| Same UPC | Extremely strong exact match |
| Same brand + exact model | Exact match |
| Same brand + model fragment | Strong match |
| Same title, different capacity | **NOT exact** |
| Same family, different generation | **NOT exact** |

## 12. Match score

Score 0–100:

| Range | Classification |
|---|---|
| 95–100 | Exact Match |
| 85–94 | Very Similar |
| 70–84 | Similar |
| Below 70 | Alternative |

The system must never falsely assign 100 to materially different products. `iPhone 16 128GB` is not identical to `iPhone 16 256GB` unless variant information confirms equivalence.

## 13. Search ranking

Consider: exact product match · relevance · popularity · price · price history · retailer reliability · availability · shipping · seller · rating · review count · deal score.

Ranking must be modular so it can evolve independently of retrieval.

## 14. Retailer / offer abstraction

Every retailer integration produces a normalized offer: retailer · product · URL · price · currency · availability · shipping · seller · condition · rating · timestamp · source.

**Never let retailer-specific data structures contaminate the core product model.** Define a common Offer schema and adapt inbound data to it at the integration boundary.

## 15. Database entities

User · Product · ProductVariant · Retailer · Offer · PriceHistory · Alert · Wishlist · SearchQuery · Recommendation · AffiliateClick

Relationships: Product → many Offers · Offer → many PriceHistory records · Product → many Variants · User → many Alerts · User → many Wishlist items

## 16. API design

Clean REST, versioned from the beginning:

```
GET  /api/v1/search
GET  /api/v1/products/{id}
GET  /api/v1/products/{id}/offers
GET  /api/v1/products/{id}/prices
POST /api/v1/alerts
GET  /api/v1/wishlist
POST /api/v1/wishlist
GET  /api/v1/deals
POST /api/v1/assistant
```

## 17. Performance

Design for fast responses: caching · async requests · pagination · efficient DB queries · search indexes · background jobs. Avoid unnecessary API calls.

## 18. Background jobs

Eventually needed for: price updates · retailer synchronization · price history · alerts · notifications · data normalization · product deduplication · search indexing.

Use a proper job queue when the need is real. **Never block API requests with long-running tasks.**

## 19. Security

Environment variables · secret management · input validation · authentication security · rate limiting · safe file uploads · SQL injection protection · XSS protection · CSRF where applicable · secure headers · logging without secrets.

**Never expose API keys. Never commit `.env`. Maintain `.env.example`.**

## 20. Observability

Structured logging · request IDs · error tracking · performance metrics · search latency · matching accuracy · API error rate · retailer data freshness.

## 21. Data quality

Data quality is a core product feature, not a nicety.

Every product and offer carries: source · timestamp · confidence where applicable.

Never mix stale and fresh information without telling the user. Never invent missing values — use null/unknown rather than fabricated information.

## 22. Search quality metrics

Track: search success rate · zero-result rate · exact-match accuracy · false-match rate · click-through rate · product selection rate · search latency.

Eventually build an evaluation dataset for product matching.

## 23. Deployment

Development: plain uvicorn + venv on this machine.

Production: managed PostgreSQL · managed Redis · search infrastructure · backend service · frontend service · background workers · monitoring. Containerization is developed against the deployment target, not locally.

Deployment must be reproducible.

---

# PART IV — ROADMAP **[REVISED]**

Four ordering changes from the original. Every feature is retained; only sequence changed.

| Change | Reason |
|---|---|
| Data acquisition moved to Phase 3 | Price history cannot be backfilled. Collection must start before the features that consume it. |
| Authentication moved before Alerts/Wishlist | Both are inherently per-user. Building them first means building throwaway identity handling. |
| Minimal UI added at Phase 6 | Nineteen backend phases before anything is visible means months without feedback or anything demonstrable. This is a thin search page, not the full frontend. |
| Local DB is SQLite | See 0.4. Postgres migration becomes its own phase once a deployment target exists. |

### Foundation

**Phase 0 — Project Foundation**
Inspect repository. Document current functionality. Clean architecture carefully. Establish requirements, configuration system, environment variables, logging, testing. Add `GET /health` returning `{"status": "ok"}`. Define API versioning strategy. Do not remove `GET /` or `GET /search` until replacements are fully tested.

**Phase 1 — Smart Product Search**
The first major product priority. Search quality is a primary competitive advantage. See §10 and §13. Must eventually understand: product names, brands, models, model numbers, SKU, UPC, EAN, GTIN, variants, color, size, capacity, storage, generation, compatibility, category, technical specifications.

**Phase 2 — Canonical Products + Product Matching**
Implement §9 and §11. Deduplication. Variant awareness.

### Data

**Phase 3 — Data Acquisition [MOVED EARLIER]**
Start collecting real price data for a deliberately small set of products — twenty is enough to begin. Official retailer APIs only; eBay, Best Buy, and Walmart offer programmes. Do not scrape. Document each source's eligibility requirements and rate limits. Run collection on a schedule from this phase onward so history accumulates while later phases are built.

**Phase 4 — Retailer / Offer Architecture**
Implement §14. Normalize collected data into the common Offer schema.

**Phase 5 — Persistence**
SQLAlchemy models per §15, SQLite locally, Alembic migrations. Migrate collected data into the schema.

### Visibility

**Phase 6 — Minimal UI [ADDED]**
A deliberately thin Next.js surface: search box, results list, product detail. No auth, no dashboard, no polish. Its purpose is to make search quality visible and testable by a human. The professional frontend remains Phase 17.

### Price intelligence

**Phase 7 — Price History**
Record price, timestamp, retailer, availability, shipping where available, for every offer/product pair. Compute: current, lowest, highest, average, median, 7/30/90-day trends, percentage from historical low.

**Phase 8 — Deal Score**
Score 0–100 from: current vs historical average · current vs historical low · current vs competitors · discount · trend · availability · retailer reliability. **Must be explainable** — e.g. "Great deal because the current price is 18% below the 90-day average." Never a black box.

**Phase 9 — Buy Now / Wait**
Recommendation of BUY NOW / WAIT / GOOD PRICE from: current price · historical price · volatility · historical lows · recent movement · seasonality · known shopping events · confidence. **Every recommendation must carry an explanation.**

**Phase 10 — Price Prediction**
Start statistical before ML: moving averages, exponential smoothing, trend analysis, seasonality, regression, later ML models. Output a predicted range, a confidence level, and a time horizon. **Never present predictions as certain.** Example: "Expected in 14 days: $285–$310, confidence 68%."

### Users

**Phase 11 — Authentication + User Accounts [MOVED EARLIER]**
Registration, login, secure authentication, sessions/tokens, profile, preferences. Security is mandatory. Never store secrets in source code.

**Phase 12 — Price Alerts**
Target price · percentage drop · lowest price · back-in-stock · significant deal. Lifecycle: Created → Monitoring → Triggered → Notified. Notification channels (email, push, browser, mobile) come later.

**Phase 13 — Wishlist**
Saved products showing current price, historical low, price change, deal score, Buy/Wait, alert status.

**Phase 14 — Best Deals**
Category-based deals (Electronics, Computers, Phones, Appliances, Home, Gaming, etc.) ranked by Deal Score, confidence, and price history. **Do not rank by largest advertised discount percentage.**

### Intelligence

**Phase 15 — AI Product Understanding**
Convert natural language into structured requirements. "best noise cancelling headphones under $300" becomes `{"category": "headphones", "budget_max": 300, "features": ["noise cancellation"]}`. The deterministic engine then performs retrieval and ranking. **AI must not replace deterministic filtering for critical product attributes.**

**Phase 16 — AI Shopping Assistant**
Conversational answers to "Which should I buy?", "Is this a good price?", "Should I wait?", "Compare these three." **Answers must be grounded in actual product and offer data. Never invent specifications.**

### Product surface

**Phase 17 — Professional Frontend**
Full Next.js interface. Pages: `/`, `/search`, `/product/[id]`, `/compare`, `/wishlist`, `/alerts`, `/deals`, `/account`, `/assistant`.

*Homepage:* lead with search — "Search products, paste a product link, or upload an image." Visual hierarchy prioritizes search.

*Search page:* search bar · filters · sort · product cards · retailer offers · price · match confidence · deal score · price history preview · Buy/Wait status · pagination.

*Product page:* identity · images · specifications · current offers · price comparison · price history graph · deal score · Buy/Wait · AI explanation · price alert button · wishlist button · affiliate buy buttons · similar products · alternatives.

*Product card:* image · brand · name · model · match confidence · lowest price · retailer count · price range · availability · rating · review count · deal score · price trend · Buy/Wait.

**Phase 18 — Product Comparison**
Side-by-side: price · specs · rating · reviews · warranty · retailer · price history · deal score · Buy/Wait · strengths · weaknesses. AI may provide a final recommendation.

### Visual

**Phase 19 — Visual Search**
Image → visual understanding → product identification → candidates → matching → offers → comparison → recommendation.

**Phase 20 — Image Matching**
Image embeddings and visual similarity as an additional matching signal. **Images must never override strong product identifiers.** Exact identifiers remain authoritative.

### Monetization

**Phase 21 — Coupons**
Collect and normalize: code · discount · expiration · retailer · eligibility. **Never claim a coupon works unless verified.**

**Phase 22 — Affiliate Monetization**
Affiliate links where available. Track clicks, retailer, product, timestamp, conversion where available. **Never manipulate recommendations to maximize affiliate revenue.**

### Scale

**Phase 23 — PostgreSQL Migration**
Move from SQLite to managed PostgreSQL once a deployment target exists. Should be a connection-string and migration exercise if §0.4 was respected throughout.

**Phase 24 — Production Infrastructure**
Docker, CI/CD, managed Redis, search infrastructure, background workers, monitoring.

**Phase 25 — Browser Extension**

**Phase 26 — Mobile Apps**

**Phase 27 — Advanced AI + Personalization**

---

# PART V — WORKING METHOD

## 24. Development philosophy

**Do not attempt to build the entire platform at once.**

Every phase must:

1. Inspect the current project
2. Understand existing code
3. Preserve working functionality
4. Implement one coherent feature group
5. Run tests
6. Run lint/type/static checks where applicable
7. Manually verify important endpoints and features
8. Report exactly what changed
9. **Stop and wait** before beginning the next major phase

Never destroy working code just to restructure it. Prefer small, testable changes. When replacing a file, provide a complete correct file rather than half-finished code. Do not create complexity before it is needed.

## 25. How to work with the product owner

The user is the product owner. Do not assume permission for large architectural decisions that change product direction.

For each step:

1. State what you found
2. State what you are going to change
3. Make the change
4. Test it
5. Show the result
6. Clearly state what is complete
7. Stop before starting an unrelated major phase

If something is ambiguous, explain the options and choose the safest minimal implementation unless clarification is genuinely necessary.

## 26. Engineering rules

**Never:** fabricate retailer data, prices, reviews, or specifications · claim real-time information without a real source · hard-code secrets · delete working functionality without a replacement · make huge untested changes · create unnecessary dependencies · silently change product requirements.

**Always:** inspect first · explain the plan · implement incrementally · test · verify · report changes · preserve compatibility.

Every new dependency requires explicit justification: what problem it solves and why existing tooling is insufficient.

## 27. Testing strategy

Every major feature requires tests: unit · integration · API · search · matching · normalization · database. End-to-end later.

**Critical search examples must remain permanently tested:**

- `Sony XM5` → `Sony WH-1000XM5`
- `Sony WH-1000XM5`
- `WH1000XM5`
- `AirPods Pro 2`
- `Samsung Galaxy Buds3 Pro`

Different variants must never become false exact matches.

## 28. Definition of done

A feature is not complete because the code exists. It is complete when: implementation exists · imports work · the application starts · tests pass · API behaviour is verified · errors are handled · existing functionality still works · documentation is updated where appropriate.

---

# PART VI — CURRENT EXECUTION INSTRUCTION **[REVISED — 2026-09-04]**

## Completed phases

| Phase | Status | Completed |
|---|---|---|
| Phase 0 — Project Foundation | **Done** | 2026-09-04 |

## Current position: Phase 1 — Smart Product Search

**Next up:** improve the search and matching engine. The priority is search quality — it is the primary competitive advantage.

Phase 0 is done. Do not re-inspect the foundation. Do not start Phase 2 (Canonical Products) until Phase 1 search quality milestones are met and confirmed.

## Phase 1 milestones

The engine must correctly handle all of:

- Exact model matching
- Partial model matching (model fragments ≥ 3 chars)
- Brand matching
- Multi-word queries
- Punctuation normalization (hyphens, spaces, special chars)
- Case normalization
- Common abbreviations
- Category awareness
- Variant awareness (different capacity/color = not exact)
- Confidence score (0–100, classification per §12)
- Deterministic, explainable ranking
- Tests for all of the above

**Known issue to fix in Phase 1:** multi-fragment queries can reach score 100 against different-capacity variants. The engine must not falsely assign 95+ to products with a materially different spec (e.g. 512GB vs 256GB). See §12 and `TestVariantDistinction`.

## Standing rules (always)

The `Sony XM5` → `Sony WH-1000XM5` behaviour and all 23 tests must remain passing after every change.

Do not start Phase 2 (Canonical Products), Phase 3 (Data Acquisition), or the frontend until Phase 1 is complete and confirmed.

## Compliance

**eBay Marketplace Account Deletion: EXEMPT** (filed 2026-09-05).
Reason on file: we retrieve public listing prices via the Browse API only, storing no eBay user data.

THE EXEMPTION IS CONDITIONAL. It is void the moment we store anything user-specific.
Phase 22 (affiliate tracking) is the likely trigger — click tracking and conversion data may qualify.
Before starting Phase 22, re-evaluate. If the exemption lapses, the account-deletion endpoint must
be built first. The full contract is researched and documented:
- GET challenge: SHA-256(challengeCode + verificationToken + endpoint), hex-encoded, JSON key `challengeResponse`
- POST: RSA-verify `JSON.stringify(body)` against `X-EBAY-SIGNATURE` using eBay's rotated public key (fetch by `kid`)
- Token constraints: 32–80 chars, alphanumeric/underscore/hyphen
- Return 204 on success, 412 on signature mismatch

## Collector design decisions

**Price ceiling — attempted and removed (2026-09-06):**
A median-based price ceiling (`median × 1.5` per product) was implemented to catch inflated or
bundle listings. It was removed after the first production dry-run because:
- The median was computed across all conditions (new, used, refurbished), which are different markets.
  A used XM4 at $110 and a new one at $279 both belong in the DB; a median across them is meaningless.
- With 5–20 candidates per product, splitting by condition leaves 2–6 samples per group —
  too few for a reliable median. The guard fired on correct prices and passed inflated ones.
- An inflated price reaching the DB is noise; a used-only DB for a product with new listings
  available is a broken product (systematically wrong lowest-price display).
- Outlier resistance belongs in Phase 7 price-history analysis with accumulated data, not at
  ingestion time with 2–6 samples.
Replacement: a warning-only HIGH PRICE log line fires when a passing listing exceeds 2× the
category price floor. This surfaces outliers in dry-run output without rejecting anything.
If a ceiling is revisited in Phase 7, it must operate per-condition and per-product with
sufficient historical samples (≥30 per condition group) to be statistically meaningful.

**Known outliers to watch once price history accumulates:**
- Jabra Elite 10: a $449.98 listing appeared in run 3 (11.2× the earbuds price floor,
  condition: unknown). Likely a bundle or listing error. Flag it when price history starts
  populating — if it persists as the highest stored price it will skew deal scoring.
- Sonos Era 300: 1 candidate at $689 (retail ~$449). With a single sample there is no basis
  for rejection now, but it should be a clear outlier once 30+ data points accumulate.

**Condition-group storage gap — FIXED (2026-09-06):**
Replaced `COLLECTOR_OFFERS_PER_PRODUCT=5` (cheapest 5 overall) with `COLLECTOR_OFFERS_PER_CONDITION=3`
(top 3 per condition group independently). `unknown` gets its own quota — not merged with `used`
because eBay `unknown` can be new-in-box; merging would make an unverifiable assumption.
After the fix, run 2 stored 118 offers: new=44, unknown=47, refurbished=8, used=106 (cumulative
across both runs: 205 total). New-condition data is now accumulating.

**"unknown" condition share (noted 2026-09-06):**
A large share of stored offers (roughly 23% of cumulative ebay offers) carry `condition='unknown'`
because many eBay sellers do not explicitly declare a condition. This is genuine uncertainty —
not a data quality failure. Decide in Phase 8 (Deal Score) whether `unknown` is treated as new,
used, or a separate bucket. Do not assume it maps to either. Options:
- Treat as its own tier, scored separately with a confidence penalty.
- Exclude from Deal Score computation until the condition is resolved.
- Use listing price relative to known-condition prices as a proxy signal.
The decision belongs in Phase 8 with real price history data, not now.

**Brand-only query label (noted 2026-09-06):**
Queries like "Sony" score 35 / Alternative for every result — correct behaviour from the brand
gate (score capped at 70 without model signal, then further filtered), but the "Alternative" label
may confuse users browsing by brand who expect all Sony products to be "Exact Match". Revisit the
label mapping or add a UI note for brand-only queries in Phase 17 (frontend).

**Known collector gaps (pre-existing, not yet addressed):**
- `adapter` word keyword rejects "HYPERBOOM /NO POWER ADAPTER-" — a real speaker listed without
  its charger. Distinguishing "charger for product" from "product sold without charger" requires
  positional/context logic not yet implemented.
- "BATTERY NEEDS REPAIR" titles pass the accessory filter — only `needsreplacement` is blocked,
  not `needsrepair`. These are damaged units priced below market.

## Known discrepancies — expected, do not fix prematurely

**Seed offers vs. retailer_count/lowest_price mismatch (noted 2026-09-05):**
`GET /api/v1/products` returns `lowest_price: null` and `retailer_count: 0` even when seed offers
exist in the database. This is correct behaviour: `lowest_price` and `retailer_count` are computed
from `live_offers()`, which filters for offers fresher than a staleness threshold. Seed offers are
synthetic and do not pass that filter. The frontend will therefore show offers on the product page
alongside "0 retailers" on the product card until real collector data arrives. Do not add special
casing for seed data — the discrepancy self-resolves once the collector runs in production.
