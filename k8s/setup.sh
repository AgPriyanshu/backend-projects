#!/usr/bin/env bash

# set -euo pipefail

echo "🚀 Starting NGINX Gateway setup..."

# -----------------------------
# Config
# -----------------------------
GATEWAY_API_VERSION="v1.1.0"
NGINX_NAMESPACE="nginx-gateway"
GATEWAY_NAMESPACE="gateway-system"

# -----------------------------
# 1. Install Gateway API CRDs
# -----------------------------
echo "📦 Installing Gateway API CRDs (${GATEWAY_API_VERSION})..."

kubectl apply -f platform/crds/gateway-api/standard-install.yaml

echo "✅ Gateway API CRDs installed"

# -----------------------------
# 2. Install NGINX Gateway Controller
# -----------------------------
echo "📦 Installing NGINX Gateway Controller..."

helm install ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric --create-namespace -n nginx-gateway
helm repo update

helm upgrade --install nginx-gateway nginx-gateway/nginx-gateway \
  --namespace ${NGINX_NAMESPACE} \
  -f platform/controllers/nginx-gateway/values.yaml

echo "✅ NGINX Gateway Controller installed"

# -----------------------------
# 3. Create Gateway namespace
# -----------------------------
echo "📦 Creating Gateway namespace..."

kubectl create namespace ${GATEWAY_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# -----------------------------
# 4. Install Gateway + Routes (Helm)
# -----------------------------
echo "🌐 Installing Gateway and Routes..."

helm upgrade --install platform-gateway platform/gateway \
  --namespace ${GATEWAY_NAMESPACE}

echo "✅ Gateway and Routes installed"

# -----------------------------
# 5. Verify installation
# -----------------------------
echo "🔍 Verifying Gateway resources..."

kubectl get gatewayclass
kubectl get gateway -n ${GATEWAY_NAMESPACE}
kubectl get httproute -A

echo "🎉 NGINX Gateway setup completed successfully!"
