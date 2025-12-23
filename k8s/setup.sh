#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting NGINX Gateway (Gateway API) setup..."

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
kubectl kustomize "https://github.com/nginx/nginx-gateway-fabric/config/crd/gateway-api/standard?ref=v2.2.2" | kubectl apply -f -

echo "✅ Gateway API CRDs installed"

# -----------------------------
# 2. Install / Upgrade NGINX Gateway Fabric
# -----------------------------
echo "📦 Installing NGINX Gateway Fabric..."

# kubectl apply --server-side -f https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.2.2/deploy/crds.yaml
# kubectl apply -f https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.2.2/deploy/default/deploy.yaml

helm upgrade --install nginx-gateway \
  oci://ghcr.io/nginx/charts/nginx-gateway-fabric \
  --version 2.2.2 \
  --namespace ${NGINX_NAMESPACE} \
  --create-namespace \
  -f platform/controllers/nginx-gateway/values.yaml
echo "✅ NGINX Gateway Fabric installed"

# -----------------------------
# 3. Create Gateway namespace
# -----------------------------
echo "📦 Creating Gateway namespace..."

kubectl create namespace ${GATEWAY_NAMESPACE} \
  --dry-run=client -o yaml | kubectl apply -f -

# -----------------------------
# 4. Install Platform Gateway (Gateway + HTTPRoutes)
# -----------------------------
echo "📦 Installing Platform Gateway..."

helm upgrade --install platform-gateway platform/gateway \
  --namespace ${GATEWAY_NAMESPACE}

helm upgrade --install platform-namespaces platform/namespaces

# -----------------------------
# 5. Install Databases
# -----------------------------
echo "📦 Installing Databases..."

helm upgrade --install platform-db platform/databases/postgres

# -----------------------------
# 6. Install Backend Applications
# -----------------------------
echo "📦 Installing Backend Applications..."

helm upgrade --install apps-backend apps/backend

# # -----------------------------
# # 7. Install Frontend Applications
# # -----------------------------
# echo "📦 Installing Frontend Applications..."

# helm upgrade --install apps-frontend apps/frontend

