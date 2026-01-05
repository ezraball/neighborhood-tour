#!/bin/bash
# Setup Google Cloud APIs for Neighborhood Tour Generator

set -e

PROJECT="neighborhood-tour-videos"

echo "=== Neighborhood Tour - GCP Setup ==="
echo

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "ERROR: gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Create project if it doesn't exist
echo "Creating project: $PROJECT"
if gcloud projects describe "$PROJECT" &>/dev/null; then
    echo "  Project already exists"
else
    gcloud projects create "$PROJECT" --name="Neighborhood Tour Videos"
    echo "  Project created"
fi

# Set as active project
gcloud config set project "$PROJECT"
echo "  Set as active project"

# Link billing account (required for Maps APIs)
echo
echo "Linking billing account..."
BILLING_ACCOUNT=$(gcloud beta billing accounts list --format="value(name)" --limit=1 2>/dev/null)
if [ -n "$BILLING_ACCOUNT" ]; then
    gcloud beta billing projects link "$PROJECT" --billing-account="$BILLING_ACCOUNT"
    echo "  Linked to billing account: $BILLING_ACCOUNT"
else
    echo "  WARNING: No billing account found. You'll need to link one manually at:"
    echo "  https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT"
fi

echo

# Enable required APIs
echo "Enabling APIs..."

echo "  - Geocoding API"
gcloud services enable geocoding-backend.googleapis.com

echo "  - Street View Static API"
gcloud services enable street-view-image-backend.googleapis.com

echo "  - Maps Static API"
gcloud services enable static-maps-backend.googleapis.com

echo
echo "APIs enabled successfully!"
echo

# Create API key
echo "Creating API key..."
API_KEY_NAME="neighborhood-tour-key"

# Check if key already exists
EXISTING_KEY=$(gcloud alpha services api-keys list --filter="displayName=$API_KEY_NAME" --format="value(name)" 2>/dev/null || true)

if [ -n "$EXISTING_KEY" ]; then
    echo "  API key '$API_KEY_NAME' already exists"
    KEY_STRING=$(gcloud alpha services api-keys get-key-string "$EXISTING_KEY" --format="value(keyString)" 2>/dev/null)
else
    # Create new key
    gcloud alpha services api-keys create --display-name="$API_KEY_NAME" --quiet

    # Get the key name and string
    sleep 2  # Brief wait for key to propagate
    KEY_NAME=$(gcloud alpha services api-keys list --filter="displayName=$API_KEY_NAME" --format="value(name)" --limit=1)
    KEY_STRING=$(gcloud alpha services api-keys get-key-string "$KEY_NAME" --format="value(keyString)")
fi

echo
echo "=== SETUP COMPLETE ==="
echo
echo "Your API key:"
echo "  $KEY_STRING"
echo
echo "To use it, run:"
echo "  export GOOGLE_API_KEY=\"$KEY_STRING\""
echo
echo "Or add to your shell profile (~/.zshrc or ~/.bashrc):"
echo "  echo 'export GOOGLE_API_KEY=\"$KEY_STRING\"' >> ~/.zshrc"
echo
