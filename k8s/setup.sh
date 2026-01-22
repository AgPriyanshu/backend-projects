#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting full Kubernetes deployment..."

# -----------------------------
# 1. Install Gateway API CRDs
# -----------------------------
echo "📦 Installing Gateway API CRDs..."

kubectl apply -f platform/crds/gateway-api/standard-install.yaml
kubectl kustomize "https://github.com/nginx/nginx-gateway-fabric/config/crd/gateway-api/standard?ref=v2.2.2" | kubectl apply -f -

echo "✅ Gateway API CRDs installed"

# -----------------------------
# 2. Create Gateway namespace
# -----------------------------
echo "📦 Creating Gateway namespace..."

kubectl create namespace gateway-ns \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✅ Gateway namespace created"

# -----------------------------
# 3. Install / Upgrade NGINX Gateway Fabric
# -----------------------------
echo "📦 Installing NGINX Gateway Fabric..."

helm upgrade --install nginx-gateway \
  oci://ghcr.io/nginx/charts/nginx-gateway-fabric \
  --version 2.2.1 \
  --namespace gateway-ns \
  -f platform/controllers/nginx-gateway/values.yaml

echo "✅ NGINX Gateway Fabric installed"

# -----------------------------
# 4. Install Platform Namespaces
# -----------------------------
echo "📦 Installing Platform Namespaces..."

helm upgrade --install platform-namespaces platform/namespaces

echo "✅ Platform Namespaces installed"

# -----------------------------
# 5. Install Platform Gateway (Gateway + HTTPRoutes)
# -----------------------------
echo "📦 Installing Platform Gateway..."

helm upgrade --install platform-gateway platform/gateway \
  --namespace gateway-ns

echo "✅ Platform Gateway installed"

# -----------------------------
# 6. Install Databases
# -----------------------------
echo "📦 Installing Databases..."

helm upgrade --install platform-db platform/databases/postgres

echo "✅ Databases installed"

# -----------------------------
# 7. Install Cache (Redis)
# -----------------------------
echo "📦 Installing Redis Cache..."

helm upgrade --install platform-cache platform/cache

echo "✅ Redis Cache installed"

# -----------------------------
# 8. Install MinIO Object Storage
# -----------------------------
echo "📦 Installing MinIO Object Storage..."

helm upgrade --install  object-storage platform/storage/object \
  --namespace default

echo "✅ MinIO Object Storage installed"

helm upgrade --install platform-registry platform/registry \
  --namespace default

# -----------------------------
# 6. Install Shared Application Components
# -----------------------------
helm upgrade --install apps-shared apps/shared \
  --namespace default

# -----------------------------
# 7. Install Backend Application
# -----------------------------
echo "📦 Installing Backend Application..."

helm upgrade --install backend apps/backend \
  --namespace default

echo "✅ Backend Application installed"

# -----------------------------
# 8. Install Frontend Application
# -----------------------------
echo "📦 Installing Frontend Application..."

helm upgrade --install frontend apps/frontend \
  --namespace default

echo "✅ Frontend Application installed"

# -----------------------------
# 9. Install Cloudflare Tunnel
# -----------------------------
echo "📦 Installing Cloudflare Tunnel (cloudflared)..."

helm upgrade --install cloudflared platform/cloudflare \
  --namespace gateway-ns \
  --create-namespace

echo "✅ Cloudflare Tunnel installed"

# -----------------------------
# Summary
# -----------------------------
echo ""
echo "=========================================="
echo "🎉 Full deployment completed successfully!"
echo "=========================================="
echo ""
echo "Deployed components:"
echo "  ✅ Gateway API CRDs"
echo "  ✅ NGINX Gateway Fabric"
echo "  ✅ Platform Gateway (gateway-ns)"
echo "  ✅ Platform Namespaces"
echo "  ✅ PostgreSQL Database"
echo "  ✅ Redis Cache"
echo "  ✅ MinIO Object Storage"
echo "  ✅ Backend Application (default)"
echo "  ✅ Frontend Application (default)"
echo "  ✅ Cloudflare Tunnel"
echo ""
echo "To check status:"
echo "  kubectl get pods -A"
echo "  kubectl get gateway -n gateway-ns"
echo "  kubectl get httproute -n gateway-ns"
