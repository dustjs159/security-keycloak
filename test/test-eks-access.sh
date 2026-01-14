#!/bin/bash
# Keycloak 토큰을 사용하여 EKS에 접근하는 테스트 스크립트

set -e

# 설정
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-company-realm}"
CLIENT_ID="${CLIENT_ID:-eks-access-client}"
CLIENT_SECRET="${CLIENT_SECRET:-your-client-secret-here}"
EKS_CLUSTER_NAME="${EKS_CLUSTER_NAME:-your-cluster-name}"
EKS_REGION="${EKS_REGION:-us-east-1}"

echo "============================================================"
echo "Keycloak → EKS 접근 테스트"
echo "============================================================"
echo ""

# 1. Keycloak에서 토큰 발급
echo "1단계: Keycloak 토큰 발급"
TOKEN_RESPONSE=$(curl -s -X POST "${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}")

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token // empty')

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
  echo "❌ 토큰 발급 실패"
  echo "응답: $TOKEN_RESPONSE"
  exit 1
fi

echo "✅ 토큰 발급 성공"
echo "   Token: ${ACCESS_TOKEN:0:50}..."
echo ""

# 2. 토큰 정보 확인 (선택사항)
echo "2단계: 토큰 정보 확인"
TOKEN_INFO=$(echo $ACCESS_TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq . 2>/dev/null || echo "토큰 디코딩 실패")
echo "$TOKEN_INFO"
echo ""

# 3. EKS 클러스터 정보 확인
echo "3단계: EKS 클러스터 확인"
if command -v aws &> /dev/null; then
  EKS_ENDPOINT=$(aws eks describe-cluster \
    --name "${EKS_CLUSTER_NAME}" \
    --region "${EKS_REGION}" \
    --query "cluster.endpoint" \
    --output text 2>/dev/null || echo "")
  
  if [ -n "$EKS_ENDPOINT" ]; then
    echo "✅ EKS 클러스터 정보 확인"
    echo "   Cluster: ${EKS_CLUSTER_NAME}"
    echo "   Endpoint: ${EKS_ENDPOINT}"
  else
    echo "⚠️  EKS 클러스터 정보를 가져올 수 없습니다."
    echo "   AWS CLI 설정을 확인하세요."
  fi
else
  echo "⚠️  AWS CLI가 설치되지 않았습니다."
fi
echo ""

# 4. Kubernetes API 호출 테스트
echo "4단계: Kubernetes API 호출 테스트"
if command -v kubectl &> /dev/null; then
  # kubectl을 Keycloak 토큰으로 사용
  # 참고: 실제로는 kubeconfig를 설정하거나 kubectl의 --token 옵션을 사용해야 합니다.
  
  echo "⚠️  kubectl을 사용한 직접 테스트는 kubeconfig 설정이 필요합니다."
  echo ""
  echo "다음과 같이 kubeconfig를 설정할 수 있습니다:"
  echo ""
  echo "kubectl config set-credentials keycloak-user \\"
  echo "  --token=${ACCESS_TOKEN}"
  echo ""
  echo "kubectl config set-context keycloak-context \\"
  echo "  --cluster=${EKS_CLUSTER_NAME} \\"
  echo "  --user=keycloak-user"
  echo ""
  echo "kubectl config use-context keycloak-context"
  echo ""
  echo "그 후 다음 명령어로 테스트:"
  echo "  kubectl get pods"
  echo "  kubectl get nodes"
else
  echo "⚠️  kubectl이 설치되지 않았습니다."
fi

echo ""
echo "============================================================"
echo "✅ 토큰 발급 완료"
echo "============================================================"
echo ""
echo "다음 단계:"
echo "1. AWS IAM 역할에 Keycloak OIDC Provider를 설정"
echo "2. Kubernetes ServiceAccount에 IAM 역할을 연결"
echo "3. Keycloak 토큰을 사용하여 EKS API 호출"
echo ""

