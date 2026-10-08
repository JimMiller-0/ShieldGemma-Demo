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

## Deploying to Google Cloud Run

This project can be deployed to **Google Cloud Run** using either **CPU-backed instances** (recommended when GPU quota is unavailable) or **NVIDIA GPU instances** (e.g. NVIDIA L4).

### Architecture on Cloud Run

```
┌────────────────────────────────┐
│       Frontend (Cloud Run)     │
│   https://frontend-...run.app  │ (Port 8080, Nginx reverse proxy)
└───────────────┬────────────────┘
                │ /api/*
                ▼
┌────────────────────────────────┐
│          API (Cloud Run)       │
│     https://api-...run.app     │ (Port 8000, FastAPI + PostgreSQL)
└───────────────┬────────────────┘
                │ /v1/inference/safety
                ▼
┌────────────────────────────────┐
│    Model Service (Cloud Run)   │
│ https://model-service-...run.app│ (Port 8080, ShieldGemma-2B)
└────────────────────────────────┘
```

### Option A: One-Command Deployment Script

The included [`deploy/deploy-all.sh`](file:///usr/local/google/home/jimmymiller/ShieldGemma-Demo/deploy/deploy-all.sh) builds all three services, pushes them to Artifact Registry, deploys them to Cloud Run, and automatically wires service URLs:

```bash
# 1. Ensure gcloud is configured with your project
gcloud config set project shadowai-customer-trials-5

# 2. Deploy all services using CPU-backed instances
./deploy/deploy-all.sh --cpu

# Or deploy with NVIDIA L4 GPU acceleration (if quota is available):
# ./deploy/deploy-all.sh --gpu
```

Optional flags:
- `--hf-token <TOKEN>`: Hugging Face token to auto-download gated ShieldGemma-2B weights on first startup.
- `--gcs-bucket <BUCKET>`: Cloud Storage bucket containing `./models/` to mount directly via Cloud Run GCS volume mount.
- `--db-url <POSTGRES_URL>`: Managed PostgreSQL connection string (Cloud SQL / Neon / Supabase).

---

### Option B: Continuous Deployment with Cloud Build

Submit the continuous deployment pipeline to Google Cloud Build:

```bash
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_REPOSITORY=shadowai-workloads,_USE_GPU=false
```

To set up automatic git triggers on every push to `main`:
1. Navigate to **Cloud Build > Triggers** in the Google Cloud Console.
2. Connect your repository.
3. Select **Cloud Build configuration file** and set the path to `cloudbuild.yaml`.

A GitHub Actions workflow is also provided at [`.github/workflows/deploy.yml`](file:///usr/local/google/home/jimmymiller/ShieldGemma-Demo/.github/workflows/deploy.yml).

---

### Option C: Manual Step-by-Step Deployment

If you prefer deploying each service manually using `gcloud`, follow these steps:

#### 1. Setup Environment Variables

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION="us-central1"
export REPOSITORY="shadowai-workloads"
export REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}"

# Enable required Google Cloud APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
```

#### 2. Deploy `model-service`

##### CPU-Backed Deployment (Default / No GPU Quota)
CPU-backed instances run ShieldGemma in scoring mode using PyTorch (`float32`):

```bash
# Build and push model service
gcloud builds submit model_service --tag="${REGISTRY}/model-service:latest"

# Deploy to Cloud Run (4 vCPUs, 16Gi RAM, CPU mode)
gcloud run deploy model-service \
  --image="${REGISTRY}/model-service:latest" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --cpu=4 \
  --memory=16Gi \
  --concurrency=2 \
  --timeout=300 \
  --no-cpu-throttling \
  --set-env-vars="COMPUTE_DEVICE=cpu,USE_VLLM=false,AUTO_DOWNLOAD_MODEL=true"
```

##### GPU-Backed Deployment (NVIDIA L4)
If your project has GPU quota on Cloud Run:

```bash
gcloud run deploy model-service \
  --image="${REGISTRY}/model-service:latest" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --cpu=4 \
  --memory=16Gi \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --concurrency=16 \
  --timeout=300 \
  --no-cpu-throttling \
  --set-env-vars="COMPUTE_DEVICE=cuda,USE_VLLM=true,AUTO_DOWNLOAD_MODEL=true"
```

Capture the deployed model service URL:
```bash
export MODEL_SERVICE_URL=$(gcloud run services describe model-service \
  --region="${REGION}" --format="value(status.url)")
echo "Model Service URL: ${MODEL_SERVICE_URL}"
```

#### 3. Deploy `api`

```bash
# Build and push API service
gcloud builds submit api --tag="${REGISTRY}/api:latest"

# Deploy API service pointing to model-service
gcloud run deploy api \
  --image="${REGISTRY}/api:latest" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8000 \
  --cpu=1 \
  --memory=1Gi \
  --set-env-vars="MODEL_SERVICE_URL=${MODEL_SERVICE_URL},LOG_LEVEL=INFO"
```

Capture the deployed API service URL:
```bash
export API_URL=$(gcloud run services describe api \
  --region="${REGION}" --format="value(status.url)")
echo "API URL: ${API_URL}"
```

#### 4. Deploy `frontend`

The frontend container automatically proxies `/api/*` requests to `${API_URL}` over HTTPS:

```bash
# Build and push frontend service
gcloud builds submit frontend --tag="${REGISTRY}/frontend:latest"

# Deploy frontend pointing to the API service
gcloud run deploy frontend \
  --image="${REGISTRY}/frontend:latest" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --cpu=1 \
  --memory=512Mi \
  --set-env-vars="API_URL=${API_URL}"

export FRONTEND_URL=$(gcloud run services describe frontend \
  --region="${REGION}" --format="value(status.url)")
echo "Frontend UI: ${FRONTEND_URL}"
```

---

### Cloud Run Configuration Summary

| Setting | CPU-Backed Instance (Default) | GPU-Backed Instance |
|---|---|---|
| **Engine** | `LocalSafetyEngine` (PyTorch CausalLM) | `VLLMSafetyEngine` (vLLM continuous batching) |
| **`USE_VLLM`** | `false` | `true` |
| **`COMPUTE_DEVICE`** | `cpu` | `cuda` |
| **vCPUs** | `4` | `4` |
| **Memory** | `16Gi` | `16Gi` |
| **GPU Flag** | *(none)* | `--gpu 1 --gpu-type nvidia-l4` |
| **Concurrency** | `2` | `16` |
| **CPU Throttling** | `--no-cpu-throttling` | `--no-cpu-throttling` |
| **Timeout** | `300s` | `300s` |


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
