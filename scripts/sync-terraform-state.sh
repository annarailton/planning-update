#!/bin/bash
set -e

# Sync Terraform state with existing GCP resources
# Run this once per environment to fix state, then never again

ENVIRONMENT="${1:-staging}"

if [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "prod" ]; then
    echo "Usage: $0 <staging|prod>"
    exit 1
fi

echo "🔄 Syncing Terraform state for environment: $ENVIRONMENT"

# Load from environment or prompt
PROJECT_ID="${GCP_PROJECT_ID:-}"
APP_NAME="${APP_NAME:-app}"
REGION="${REGION:-asia-southeast1}"
TFSTATE_BUCKET="${TFSTATE_BUCKET:-}"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID environment variable required"
    exit 1
fi

if [ -z "$TFSTATE_BUCKET" ]; then
    echo "Error: TFSTATE_BUCKET environment variable required"
    exit 1
fi

REPO_NAME=$(basename "$(git rev-parse --show-toplevel)")

sync_service() {
    local SERVICE_TYPE="$1"  # worker, backend, frontend
    local TF_DIR="terraform/services/$SERVICE_TYPE"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 Syncing $SERVICE_TYPE..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    cd "$TF_DIR"

    # Calculate service name
    SERVICE_NAME=$(echo "${APP_NAME}-${SERVICE_TYPE}-${ENVIRONMENT}" | tr '[:upper:]' '[:lower:]' | tr '_' '-')

    # Init terraform
    echo "🔧 Initializing Terraform..."
    terraform init \
        -backend-config="bucket=$TFSTATE_BUCKET" \
        -backend-config="prefix=$REPO_NAME/services/$SERVICE_TYPE" \
        -reconfigure > /dev/null

    # Select workspace
    terraform workspace select "$ENVIRONMENT" 2>/dev/null || terraform workspace new "$ENVIRONMENT"

    # Remove old registry module from state if present
    if terraform state list 2>/dev/null | grep -q "module.registry"; then
        echo "🗑️  Removing old registry module from state..."
        terraform state rm module.registry.google_artifact_registry_repository.repository 2>/dev/null || true
    fi

    # Import Cloud Run service
    if gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
        if ! terraform state list 2>/dev/null | grep -q "module.cloud_run.google_cloud_run_v2_service.service"; then
            echo "📥 Importing Cloud Run service: $SERVICE_NAME"
            terraform import \
                -var="project_id=$PROJECT_ID" \
                -var="environment=$ENVIRONMENT" \
                -var="app_name=$APP_NAME" \
                -var="region=$REGION" \
                -var="image_url=placeholder" \
                module.cloud_run.google_cloud_run_v2_service.service \
                "projects/$PROJECT_ID/locations/$REGION/services/$SERVICE_NAME" || true
        else
            echo "✅ Cloud Run service already in state"
        fi
    else
        echo "ℹ️  Cloud Run service doesn't exist yet (will be created on first deploy)"
    fi

    # Backend-specific imports
    if [ "$SERVICE_TYPE" = "backend" ]; then
        # Import GCS bucket
        BUCKET_HASH=$(echo -n "${PROJECT_ID}-${APP_NAME}" | md5sum | cut -c1-4)
        BUCKET_NAME="${APP_NAME}-${ENVIRONMENT}-${BUCKET_HASH}"

        if gsutil ls -b "gs://$BUCKET_NAME" &>/dev/null; then
            if ! terraform state list 2>/dev/null | grep -q "module.storage.google_storage_bucket.bucket"; then
                echo "📥 Importing GCS bucket: $BUCKET_NAME"
                terraform import \
                    -var="project_id=$PROJECT_ID" \
                    -var="environment=$ENVIRONMENT" \
                    -var="app_name=$APP_NAME" \
                    -var="region=$REGION" \
                    -var="image_url=placeholder" \
                    module.storage.google_storage_bucket.bucket \
                    "$BUCKET_NAME" || true
            else
                echo "✅ GCS bucket already in state"
            fi
        else
            echo "ℹ️  GCS bucket doesn't exist yet (will be created on first deploy)"
        fi

        # Import migration job (requires database_url to satisfy conditional)
        MIGRATION_JOB_NAME="${SERVICE_NAME}-migration"
        if gcloud run jobs describe "$MIGRATION_JOB_NAME" --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
            if ! terraform state list 2>/dev/null | grep -q "google_cloud_run_v2_job.migration"; then
                echo "📥 Importing migration job: $MIGRATION_JOB_NAME"
                terraform import \
                    -var="project_id=$PROJECT_ID" \
                    -var="environment=$ENVIRONMENT" \
                    -var="app_name=$APP_NAME" \
                    -var="region=$REGION" \
                    -var="image_url=placeholder" \
                    -var="database_url=placeholder" \
                    'google_cloud_run_v2_job.migration[0]' \
                    "projects/$PROJECT_ID/locations/$REGION/jobs/$MIGRATION_JOB_NAME" || true
            else
                echo "✅ Migration job already in state"
            fi
        else
            echo "ℹ️  Migration job doesn't exist yet (will be created on first deploy)"
        fi
    fi

    cd - > /dev/null
    echo "✅ $SERVICE_TYPE sync complete"
}

# Sync all services
cd "$(git rev-parse --show-toplevel)"

sync_service "worker"
sync_service "backend"
sync_service "frontend"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ State sync complete for $ENVIRONMENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
