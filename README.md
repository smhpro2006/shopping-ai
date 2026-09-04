# Shopping AI

US-focused AI shopping intelligence platform.

> Never overpay again. Find the right product, at the right price, at the right time.

**Status:** early development — smart product search and matching foundation.

---

## What this is

Shopping AI understands product queries, matches equivalent products across US retailers, tracks price history, and tells the user whether to buy now or wait.

It is not a price-comparison listing site. The differentiator is search and matching quality: `Sony XM5`, `WH1000XM5`, and `wh 1000 xm5` all resolve to the same canonical product, while `iPhone 16 128GB` and `iPhone 16 256GB` do not.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python · FastAPI · Pydantic |
| Database | PostgreSQL · SQLAlchemy · Alembic |
| Frontend | Next.js · React · TypeScript · Tailwind |
| Hosting | Railway (auto-deploy from `main`) |
| Tests | pytest |

---

## Local development

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in DATABASE_URL
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

Run tests:

```bash
pytest
```

---

## Project layout

```
backend/app/
├── api/            route handlers
├── models/         SQLAlchemy models
├── schemas/        Pydantic schemas
├── services/       search, matching, pricing logic
├── integrations/   retailer, affiliate, AI adapters
├── core/           config, security, logging, database
└── tests/
```

---

## Contributing

Read `CLAUDE.md` first — it defines the architecture, the phase roadmap, and the working rules.

Branch per phase, commit after each tested step, merge to `main` only when tests pass. `main` auto-deploys.

Never commit `.env` or any credential.

---

## Data policy

Prices, availability, ratings, and history are never fabricated. Every product and offer records its source and timestamp. Missing values are null, not invented. Retailer data comes from official APIs only.
