#!/usr/bin/env bash
# ==============================================================================
# Deploy ShieldGemma Demo to Google Cloud Run
#
# Services deployed:
#   1. model-service  (ShieldGemma-2B, CPU-backed by default or GPU)
#   2. api            (FastAPI orchestrator, connects to model-service & PostgreSQL)
#   3. frontend       (React SPA + Nginx reverse proxy to api)
# ==============================================================================

set -euo pipefail

# Color formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Default configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-us-central1}"
REPOSITORY="${REPOSITORY:-shadowai-workloads}"
USE_GPU="${USE_GPU:-false}"
HF_TOKEN="${HF_TOKEN:-${HUGGINGFACE_TOKEN:-}}"
DATABASE_URL="${DATABASE_URL:-}"
GCS_MODEL_BUCKET="${GCS_MODEL_BUCKET:-shieldgemma-models-${PROJECT_ID}}"


# Parse optional command-line flags
while [[ $# -gt 0 ]]; do
  case $1 in
    --gpu)
      USE_GPU=true
      shift
      ;;
    --cpu)
      USE_GPU=false
      shift
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --project)
      PROJECT_ID="$2"
      shift 2
      ;;
    --repository)
      REPOSITORY="$2"
      shift 2
      ;;
    --hf-token)
      HF_TOKEN="$2"
      shift 2
      ;;
    --db-url)
      DATABASE_URL="$2"
      shift 2
      ;;
    --gcs-bucket)
      GCS_MODEL_BUCKET="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --cpu               Deploy model service on CPU (default, 4 vCPUs, 16Gi RAM)"
      echo "  --gpu               Deploy model service on NVIDIA GPU (NVIDIA L4)"
      echo "  --project ID        Google Cloud project ID (default: active gcloud project)"
      echo "  --region REGION     Deployment region (default: us-central1)"
      echo "  --repository REPO   Artifact Registry repository (default: shadowai-workloads)"
      echo "  --hf-token TOKEN    Hugging Face access token for ShieldGemma model download"
      echo "  --gcs-bucket NAME   GCS bucket containing model weights to mount"
      echo "  --db-url URL        PostgreSQL connection string for the API service"
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ -z "${PROJECT_ID}" ]]; then
  log_error "Google Cloud Project ID is not set. Run 'gcloud config set project <PROJECT_ID>' or pass --project <PROJECT_ID>."
  exit 1
fi

log_info "Deploying ShieldGemma Demo to Google Cloud Run"
log_info "Project:     ${PROJECT_ID}"
log_info "Region:      ${REGION}"
log_info "Repository:  ${REPOSITORY}"
log_info "Mode:        $([[ "${USE_GPU}" == "true" ]] && echo "GPU (NVIDIA L4)" || echo "CPU-backed instances")"

# 1. Ensure required APIs are enabled
log_info "Verifying required Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project="${PROJECT_ID}" --quiet

# 2. Ensure Artifact Registry repository exists
REPO_EXISTS=$(gcloud artifacts repositories describe "${REPOSITORY}" \
  --location="${REGION}" --project="${PROJECT_ID}" --format="value(name)" 2>/dev/null || true)

if [[ -z "${REPO_EXISTS}" ]]; then
  log_info "Creating Artifact Registry repository '${REPOSITORY}' in ${REGION}..."
  gcloud artifacts repositories create "${REPOSITORY}" \
    --repository-format=docker \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --description="Docker repository for ShieldGemma Demo" \
    --quiet
fi

REGISTRY_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}"

# 3. Build & Deploy Model Service
log_info "Step 1/3: Building and deploying model-service..."
MODEL_IMG="${REGISTRY_BASE}/model-service:latest"

gcloud builds submit model_service \
  --tag="${MODEL_IMG}" \
  --project="${PROJECT_ID}" \
  --quiet

DEPLOY_MODEL_ARGS=(
  "model-service"
  "--image=${MODEL_IMG}"
  "--project=${PROJECT_ID}"
  "--region=${REGION}"
  "--platform=managed"
  "--allow-unauthenticated"
  "--timeout=300"
  "--port=8080"
  "--no-cpu-throttling"
)

if [[ "${USE_GPU}" == "true" ]]; then
  log_info "Configuring model-service with NVIDIA L4 GPU..."
  DEPLOY_MODEL_ARGS+=(
    "--cpu=4"
    "--memory=16Gi"
    "--gpu=1"
    "--gpu-type=nvidia-l4"
    "--max-instances=2"
    "--concurrency=16"
    "--set-env-vars=COMPUTE_DEVICE=cuda,USE_VLLM=true,VLLM_USE_ASYNC_ENGINE=true,AUTO_DOWNLOAD_MODEL=true${HF_TOKEN:+,HF_TOKEN=${HF_TOKEN}}"
  )
else
  log_info "Configuring model-service with CPU-backed instance (8 vCPU, 32Gi RAM)..."
  DEPLOY_MODEL_ARGS+=(
    "--cpu=8"
    "--memory=32Gi"
    "--max-instances=2"
    "--concurrency=4"
    "--set-env-vars=COMPUTE_DEVICE=cpu,USE_VLLM=false,AUTO_DOWNLOAD_MODEL=true${HF_TOKEN:+,HF_TOKEN=${HF_TOKEN}}"
  )
fi

# Optional GCS volume mount for instant model loading
if [[ -n "${GCS_MODEL_BUCKET}" ]]; then
  log_info "Mounting GCS bucket gs://${GCS_MODEL_BUCKET} to /app/models..."
  DEPLOY_MODEL_ARGS+=(
    "--execution-environment=gen2"
    "--add-volume=name=model-weights,type=cloud-storage,bucket=${GCS_MODEL_BUCKET},readonly=true"
    "--add-volume-mount=volume=model-weights,mount-path=/app/models"
  )

fi

gcloud run deploy "${DEPLOY_MODEL_ARGS[@]}"

MODEL_SERVICE_URL=$(gcloud run services describe model-service \
  --platform=managed \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

log_success "model-service deployed at: ${MODEL_SERVICE_URL}"

# 4. Build & Deploy API Service
log_info "Step 2/3: Building and deploying api..."
API_IMG="${REGISTRY_BASE}/api:latest"

gcloud builds submit api \
  --tag="${API_IMG}" \
  --project="${PROJECT_ID}" \
  --quiet

API_ENV_VARS="MODEL_SERVICE_URL=${MODEL_SERVICE_URL},LOG_LEVEL=INFO"
if [[ -n "${DATABASE_URL}" ]]; then
  API_ENV_VARS="${API_ENV_VARS},DATABASE_URL=${DATABASE_URL}"
fi

gcloud run deploy api \
  --image="${API_IMG}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  "--port=8000" \
  --cpu=1 \
  --memory=1Gi \
  --min-instances=0 \
  --max-instances=5 \
  --set-env-vars="${API_ENV_VARS}"

API_URL=$(gcloud run services describe api \
  --platform=managed \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

log_success "api deployed at: ${API_URL}"

# 5. Build & Deploy Frontend
log_info "Step 3/3: Building and deploying frontend..."
FRONTEND_IMG="${REGISTRY_BASE}/frontend:latest"

gcloud builds submit frontend \
  --tag="${FRONTEND_IMG}" \
  --project="${PROJECT_ID}" \
  --quiet

gcloud run deploy frontend \
  --image="${FRONTEND_IMG}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  "--port=8080" \
  --cpu=1 \
  --memory=512Mi \
  --min-instances=0 \
  --max-instances=5 \
  --set-env-vars="API_URL=${API_URL}"

FRONTEND_URL=$(gcloud run services describe frontend \
  --platform=managed \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

log_success "frontend deployed at: ${FRONTEND_URL}"

# Summary
echo ""
echo "=============================================================================="
log_success "Deployment Complete!"
echo "=============================================================================="
echo -e "  Frontend UI:    ${GREEN}${FRONTEND_URL}${NC}"
echo -e "  API Docs:       ${BLUE}${API_URL}/docs${NC}"
echo -e "  Model Health:   ${BLUE}${MODEL_SERVICE_URL}/v1/health${NC}"
echo "=============================================================================="
