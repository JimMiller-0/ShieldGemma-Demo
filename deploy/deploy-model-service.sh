#!/usr/bin/env bash
# ==============================================================================
# Deploy Model Service to Google Cloud Run
# ==============================================================================

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-us-central1}"
REPOSITORY="${REPOSITORY:-shadowai-workloads}"
USE_GPU="${USE_GPU:-false}"
HF_TOKEN="${HF_TOKEN:-${HUGGINGFACE_TOKEN:-}}"
GCS_MODEL_BUCKET="${GCS_MODEL_BUCKET:-shieldgemma-models-${PROJECT_ID}}"


while [[ $# -gt 0 ]]; do
  case $1 in
    --gpu) USE_GPU=true; shift ;;
    --cpu) USE_GPU=false; shift ;;
    --region) REGION="$2"; shift 2 ;;
    --project) PROJECT_ID="$2"; shift 2 ;;
    --repository) REPOSITORY="$2"; shift 2 ;;
    --hf-token) HF_TOKEN="$2"; shift 2 ;;
    --gcs-bucket) GCS_MODEL_BUCKET="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

REGISTRY_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}"
MODEL_IMG="${REGISTRY_BASE}/model-service:latest"

echo "Building model-service container..."
gcloud builds submit model_service \
  --tag="${MODEL_IMG}" \
  --project="${PROJECT_ID}"

DEPLOY_ARGS=(
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
  echo "Deploying on GPU (NVIDIA L4)..."
  DEPLOY_ARGS+=(
    "--cpu=4"
    "--memory=16Gi"
    "--gpu=1"
    "--gpu-type=nvidia-l4"
    "--concurrency=16"
    "--set-env-vars=COMPUTE_DEVICE=cuda,USE_VLLM=true,VLLM_USE_ASYNC_ENGINE=true,AUTO_DOWNLOAD_MODEL=true${HF_TOKEN:+,HF_TOKEN=${HF_TOKEN}}"
  )
else
  echo "Deploying on CPU-backed instance (8 vCPU, 32Gi RAM)..."
  DEPLOY_ARGS+=(
    "--cpu=8"
    "--memory=32Gi"
    "--concurrency=4"
    "--set-env-vars=COMPUTE_DEVICE=cpu,USE_VLLM=false,AUTO_DOWNLOAD_MODEL=true${HF_TOKEN:+,HF_TOKEN=${HF_TOKEN}}"
  )
fi

if [[ -n "${GCS_MODEL_BUCKET}" ]]; then
  echo "Mounting GCS bucket gs://${GCS_MODEL_BUCKET} to /app/models..."
  DEPLOY_ARGS+=(
    "--execution-environment=gen2"
    "--add-volume=name=model-weights,type=cloud-storage,bucket=${GCS_MODEL_BUCKET},readonly=true"
    "--add-volume-mount=volume=model-weights,mount-path=/app/models"
  )
fi

gcloud run deploy "${DEPLOY_ARGS[@]}"

MODEL_URL=$(gcloud run services describe model-service \
  --platform=managed \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

echo "Model service deployed: ${MODEL_URL}"
echo "Health check: ${MODEL_URL}/v1/health"
