# RePlate Intelligence

**Predict Waste. Redistribute Food. Create Impact.**

> An AI-powered platform that predicts food waste, connects surplus food with recipients,
> and helps organizations make smarter sustainability decisions.
> Aligned with UN **SDG 12** (Responsible Consumption) and **SDG 2** (Zero Hunger).

---

## Overview

RePlate Intelligence is a full-stack AI application consisting of:

- **FastAPI backend** with a trained RandomForestRegressor ML pipeline
- **React + TypeScript frontend** — a three-column AI workspace dashboard
- **SQLite database** for food donations, recipients, and donation plans
- **Agentic AI workflow** for recipient matching and donation planning
- **Deterministic fallback mode** — fully functional without an LLM API key

---

## Dataset

| File | Rows | Purpose |
|------|------|---------|
| `dataset/train.csv` | 911 | Model training (target: `food_waste_kg`) |
| `dataset/test.csv` | 911 | Competition held-out set (no target) |

**Target:** `food_waste_kg` (continuous regression)
**Features:** `meals_served`, `kitchen_staff`, `temperature_C`, `humidity_percent`, `day_of_week`, `special_event`, `past_waste_kg`, `staff_experience`, `waste_category`

---

## Model Performance

| Metric | Value | Split |
|--------|-------|-------|
| **MAE** | **4.794 kg** | 20% validation |
| **RMSE** | **7.027 kg** | 20% validation |
| **R²** | **0.9036** | 20% validation |

> ⚠️ Trained on synthetic/competition data. Model is labelled **prototype**. Predictions are indicative only.

---

## Requirements

- Python 3.11+ (tested on Python 3.12)
- Node.js 18+ and npm (for frontend)

---

## Installation & Startup

### Terminal 1 — Backend

```bash
cd backend

# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Configure environment (copy and edit as needed)
cp .env.example .env

# 3. Train the ML model (run once, re-use afterwards)
python -m app.ml.train

# 4. Seed demo data (run once)
python -m scripts.seed_demo_data

# 5. Start the backend API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/api/health

### Terminal 2 — Frontend

```bash
cd frontend

# 1. Install Node.js dependencies
npm install

# 2. Copy environment file (no changes needed for local dev)
cp .env.example .env

# 3. Start the development server
npm run dev
```

Frontend available at: **http://localhost:5173**

---

## Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| Overview | `/` | Dashboard — metrics, charts, recent activity |
| AI Assistant | `/assistant` | Conversational AI interface with backend integration |
| Waste Predictions | `/predictions` | ML prediction form + history |
| Food Donations | `/donations` | CRUD — register and manage surplus food |
| Recipients | `/recipients` | CRUD — manage recipient organizations |
| Matching | `/matching` | AI agent workflow — run, review, approve/reject plans |
| Analytics | `/analytics` | Recharts analytics — categories, status, trends |
| Settings | `/settings` | System info and configuration |

---

## Backend API Reference

### Health & Dataset
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Backend health and model readiness |
| `GET` | `/api/dataset/info` | Dataset info, columns, missing values |

### ML Model
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/model/train` | Train the ML model |
| `GET` | `/api/model/metrics` | Validation metrics (MAE, RMSE, R²) |
| `GET` | `/api/model/features` | Feature schema for prediction |
| `POST` | `/api/predict` | Predict food waste (kg) |

### Food Donations
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/food` | Register surplus food |
| `GET` | `/api/food` | List (paginated, filterable) |
| `GET` | `/api/food/{id}` | Get one record |
| `PATCH` | `/api/food/{id}` | Update details |
| `DELETE` | `/api/food/{id}` | Delete or withdraw |

### Recipients
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/recipients` | Create recipient |
| `GET` | `/api/recipients` | List (paginated, filterable) |
| `GET` | `/api/recipients/{id}` | Get one recipient |
| `PATCH` | `/api/recipients/{id}` | Update |
| `DELETE` | `/api/recipients/{id}` | Deactivate or delete |

### Agentic Workflow
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/agent/plan/{food_id}` | Run planning workflow |
| `GET` | `/api/agent/plan/{plan_id}` | Get a plan |
| `POST` | `/api/agent/plan/{plan_id}/approve` | Human approval |
| `POST` | `/api/agent/plan/{plan_id}/reject` | Reject plan |
| `PATCH` | `/api/agent/plan/{plan_id}/status` | Update status |

---

## Testing

### Backend (56 tests)

```bash
cd backend
python -m pytest tests/ -v
```

Expected: **56 passed, 1 warning**

### Frontend

```bash
cd frontend
npm run typecheck    # TypeScript check
npm run build        # Production build
```

---

## Environment Variables

### Backend (`backend/.env`)

```env
DATABASE_URL=sqlite:///./foodbridge.db
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
OPENAI_API_KEY=              # Optional — omit for deterministic fallback
LLM_MODEL=gpt-4o-mini
MIN_HOURS_BEFORE_EXPIRY=4
CAPACITY_SAFETY_MARGIN=0.95
```

### Frontend (`frontend/.env`)

```env
VITE_API_BASE_URL=http://localhost:8000
```

> ⚠️ Never put backend secrets (OPENAI_API_KEY, database credentials) in frontend environment variables.

---

## Safety & Ethics

- **Human approval required** — no plan is confirmed without explicit `POST /api/agent/plan/{id}/approve`
- **Expiry enforcement** — food within 4 hours of expiry is excluded from matching
- **Capacity limits** — recipient capacity is respected with a 95% safety margin
- **Demo data** — seeded recipients and food are clearly labelled `[DEMO]`
- **Prototype label** — model trained on synthetic data; not validated for production operations
- **No LLM authority** — if LLM is used, it only generates explanations; all eligibility and safety decisions are deterministic Python

---

## Project Structure

```
RePlate Intelligence/
├── backend/                    # FastAPI + ML backend
│   ├── app/
│   │   ├── main.py             # FastAPI app entry-point
│   │   ├── core/config.py      # Environment configuration
│   │   ├── db/                 # SQLAlchemy models + session
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── api/                # Route handlers
│   │   ├── services/           # Business logic
│   │   └── ml/                 # Training pipeline
│   ├── scripts/seed_demo_data.py
│   ├── models/                 # Saved pipeline artefacts
│   ├── tests/                  # 56 pytest tests
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                   # React + TypeScript + Vite frontend
│   ├── src/
│   │   ├── App.tsx             # Route definitions
│   │   ├── components/layout/  # AppLayout, Sidebar, RightSidebar
│   │   ├── components/ui/      # Shared UI components
│   │   ├── pages/              # Overview, Assistant, Predictions, etc.
│   │   ├── services/           # API client services
│   │   ├── hooks/              # useSystemStatus
│   │   ├── types/api.ts        # TypeScript interfaces
│   │   └── styles/index.css    # Tailwind + custom CSS
│   ├── package.json
│   └── .env.example
│
└── dataset/                    # Kaggle food waste dataset
    ├── train.csv               # 911 rows, includes food_waste_kg target
    └── test.csv                # 911 rows, no target
```

---

## SDG Alignment

| Goal | Contribution |
|------|-------------|
| **SDG 12** – Responsible Consumption | Predicts and quantifies food waste; supports reduction strategies |
| **SDG 2** – Zero Hunger | Facilitates redistribution of surplus food to organizations in need |
