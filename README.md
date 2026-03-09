# ShieldGemma Demo

An open-source safety moderation demo showing how custom safety policies work with Google's ShieldGemma model. This project lets you evaluate the efficacy of LLM-based content moderation with custom and predefined safety policies.

## Architecture

```
┌─────────────────────────────────────────────────┐
│            Frontend (React + MUI)                │
│        http://localhost:3000                     │
│  Analyzer Demo  │  Policy Manager               │
└────────────────────────┬────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────┐
│            API Service (FastAPI)                  │
│        http://localhost:8000                     │
│  Safety Analysis  │  Policy CRUD  │  Logs       │
└──────────┬─────────────────────────┬────────────┘
           │                         │
           ▼                         ▼
┌─────────────────────┐   ┌──────────────────────┐
│  Model Service      │   │  PostgreSQL          │
│  http://localhost:   │   │  localhost:5432      │
│  8080                │   │  safety_policies     │
│  ShieldGemma 2B     │   │  analysis_logs       │
│  (CPU/MPS/CUDA)     │   │                      │
└─────────────────────┘   └──────────────────────┘
```

## How It Works

1. **Custom Policies**: Define custom safety policies with specific rules for your use case
2. **Predefined Categories**: Toggle 4 built-in ShieldGemma categories (Dangerous Content, Harassment, Hate Speech, Sexually Explicit)
3. **Prompt Construction**: Each policy is formatted into ShieldGemma's expected prompt structure
4. **Scoring Mode**: The model performs a single forward pass per policy, extracting Yes/No token probabilities to determine violation likelihood
5. **Results**: Each category returns a violation probability (0.0-1.0); content is flagged if any score exceeds 0.5

## Prerequisites

- **Docker** and **Docker Compose** (v2)
- **~5 GB disk space** for the ShieldGemma-2B model weights
- **~8 GB RAM** minimum (model runs on CPU by default)
- **Python 3.12+** (for model download script only)
- **HuggingFace account** with access to [google/shieldgemma-2b](https://huggingface.co/google/shieldgemma-2b) (accept the model license)

## Quick Start

### 1. Download the model

```bash
# Install dependencies for the download script
pip install huggingface_hub

# Log in to HuggingFace (needed for gated model access)
huggingface-cli login

# Download ShieldGemma-2B (~5 GB)
MODEL_DIR=./models python -m model_service.scripts.download_model
```

### 2. Start all services

```bash
docker compose up --build
```

### 3. Open the demo

- **Frontend**: http://localhost:3000
- **API docs**: http://localhost:8000/docs
- **Model service health**: http://localhost:8080/v1/health

## Local Development (without Docker)

### PostgreSQL

```bash
# Start PostgreSQL (via Docker or local install)
docker run -d --name sgdemo-pg -p 5432:5432 \
  -e POSTGRES_DB=shieldgemma_demo \
  -e POSTGRES_USER=demo \
  -e POSTGRES_PASSWORD=demo \
  postgres:16-alpine
```

### Model Service

```bash
cd model_service
pip install -r requirements.txt
MODEL_DIR=../models PYTHONPATH=.. uvicorn model_service.app.main:app --port 8080
```

### API Service

```bash
cd api
pip install -r requirements.txt

# Run migrations
DATABASE_URL=postgresql://demo:demo@localhost:5432/shieldgemma_demo alembic upgrade head

# Start API
PYTHONPATH=.. uvicorn api.app.main:app --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

## GPU Support

For NVIDIA GPU acceleration, uncomment the `deploy` section in `docker-compose.yml` under the `model-service`. The engine auto-detects CUDA and uses bfloat16 for faster inference.

For Apple Silicon (MPS), set `COMPUTE_DEVICE=mps` in the model service environment. Note that float32 is used on MPS to avoid precision issues.

## API Endpoints

### Safety Analysis
- `POST /api/v1/safety/analyze` - Analyze text for safety violations
- `GET /api/v1/safety/models` - List available models
- `GET /api/v1/safety/logs` - View analysis history

### Policy Management
- `GET /api/v1/safety/policies/` - List policies
- `POST /api/v1/safety/policies/` - Create policy
- `GET /api/v1/safety/policies/{id}` - Get policy
- `PATCH /api/v1/safety/policies/{id}` - Update policy
- `DELETE /api/v1/safety/policies/{id}` - Delete policy
- `GET /api/v1/safety/policies/check_name/{name}` - Check name uniqueness
- `GET /api/v1/safety/policies/default` - Get default policy

### Model Service
- `POST /v1/inference/safety` - Run safety inference
- `GET /v1/health` - Health check

## Project Structure

```
ShieldGemma-Demo/
├── docker-compose.yml          # Orchestration for all services
├── model_service/              # ShieldGemma inference service
│   ├── app/
│   │   ├── main.py             # FastAPI app with model loading
│   │   ├── config.py           # Device detection, settings
│   │   ├── engine.py           # LocalSafetyEngine (scoring mode)
│   │   ├── models.py           # Request/response schemas
│   │   └── routes.py           # /v1/inference/safety endpoint
│   └── scripts/
│       └── download_model.py   # Model downloader
├── api/                        # API service
│   ├── app/
│   │   ├── main.py             # FastAPI app, CORS, seeding
│   │   ├── config.py           # Environment settings
│   │   ├── database.py         # Async SQLAlchemy
│   │   ├── models.py           # ORM models
│   │   ├── schemas.py          # Pydantic schemas
│   │   ├── crud.py             # Database operations
│   │   ├── service.py          # Safety analyzer logic
│   │   └── routes/             # API endpoints
│   └── alembic/                # Database migrations
├── frontend/                   # React UI
│   └── src/
│       ├── App.tsx             # Router
│       ├── api.ts              # API client
│       ├── pages/              # Analyzer & Policies pages
│       └── components/         # Reusable components
└── models/                     # Downloaded model weights (git-ignored)
```

## License

This project is open source. ShieldGemma model weights are subject to [Google's Gemma Terms of Use](https://ai.google.dev/gemma/terms).
