#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
REGION="${REGION:-us-central1}"

echo "=== Agent Commerce – Cloud Run Deployment ==="
echo "Project: $PROJECT_ID  Region: $REGION"

gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com aiplatform.googleapis.com --project="$PROJECT_ID"

deploy_agent() {
  local name=$1
  local dir=$2
  echo ""
  echo ">>> Deploying $name"
  gcloud run deploy "$name" \
    --source "$dir" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --allow-unauthenticated \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION" \
    --memory 1Gi --cpu 1 \
    --min-instances 0 --max-instances 10 \
    --timeout 300 --quiet
}

deploy_agent "inventory-agent"         "../agents/inventory_agent"
deploy_agent "cart-agent"              "../agents/cart_agent"
deploy_agent "customer-agent"          "../agents/customer_agent"
deploy_agent "offers-agent"            "../agents/offers_agent"
deploy_agent "loyalty-agent"           "../agents/loyalty_agent"
deploy_agent "recommendations-agent"   "../agents/recommendations_agent"
deploy_agent "payment-agent"           "../agents/payment_agent"
deploy_agent "shipping-agent"          "../agents/shipping_agent"
deploy_agent "fulfillment-agent"       "../agents/fulfillment_agent"
deploy_agent "returns-agent"           "../agents/returns_agent"
deploy_agent "sales-partner-agent"     "../agents/sales_partner_agent"
deploy_agent "shopper-agent"           "../agents/shopper_agent"
deploy_agent "commerce-orchestrator"   "../agents/root_orchestrator"

echo ""
echo "=== Done ==="
gcloud run services list --project="$PROJECT_ID" --region="$REGION" --filter="metadata.name~agent"
