#!/bin/bash
# ============================================
# Setup GCP Secrets for Cloud Run
# ============================================

set -e

PROJECT_ID="${GCP_PROJECT_ID:-}"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Please set GCP_PROJECT_ID"
    echo "   export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

echo "Setting up secrets for project: $PROJECT_ID"
echo ""

# Function to create secret
create_secret() {
    local name=$1
    local prompt=$2
    
    if gcloud secrets describe $name --project=$PROJECT_ID &>/dev/null; then
        echo "⏭️  Secret $name already exists"
        read -p "   Update it? (y/N): " update
        if [ "$update" == "y" ]; then
            read -sp "$prompt: " value
            echo ""
            echo "$value" | gcloud secrets versions add $name --data-file=- --project=$PROJECT_ID
            echo "✅ Updated $name"
        fi
    else
        read -sp "$prompt: " value
        echo ""
        echo "$value" | gcloud secrets create $name --data-file=- --project=$PROJECT_ID
        echo "✅ Created $name"
    fi
}

echo "Enter your secret values (input is hidden):"
echo ""

create_secret "GEMINI_API_KEY" "Gemini API Key"
create_secret "SUPABASE_URL" "Supabase URL (https://xxx.supabase.co)"
create_secret "SUPABASE_KEY" "Supabase Anon Key"
create_secret "REDIS_URL" "Redis URL (rediss://...)"
create_secret "RAZORPAY_KEY_ID" "Razorpay Key ID"
create_secret "RAZORPAY_KEY_SECRET" "Razorpay Key Secret"
create_secret "RAZORPAY_WEBHOOK_SECRET" "Razorpay Webhook Secret"

echo ""
echo "✅ All secrets configured!"
echo ""
echo "Verify with: gcloud secrets list --project=$PROJECT_ID"
