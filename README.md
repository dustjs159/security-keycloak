# Keycloak 테스트 가이드

## 현재 상태
- ✅ Minikube에 Keycloak 설치 완료
- ✅ 웹 콘솔 접근 확인 (포트포워딩)

## 테스트 단계

### 1단계: 기본 인증 테스트
**목적**: Keycloak 기본 기능 확인

#### 1.1 Admin Console 접근
```bash
# 포트포워딩 확인
kubectl port-forward svc/keycloak 8080:8080

# 브라우저에서 접근
http://localhost:8080
# Admin 계정: admin / !Password1
```

#### 1.2 Realm 생성 및 테스트
1. Admin Console → Create Realm
   - Realm name: `test-realm`
   - Enabled: ON
   - Save

2. 테스트 사용자 생성
   - Users → Add user
   - Username: `testuser`
   - Email: `test@example.com`
   - Email Verified: ON
   - Save
   - Credentials 탭 → Set password
     - Password: `test1234`
     - Temporary: OFF

3. Client 생성 (테스트용)
   - Clients → Create
   - Client ID: `test-client`
   - Client Protocol: `openid-connect`
   - Access Type: `public`
   - Valid Redirect URIs: `http://localhost:3000/*`
   - Web Origins: `+`

#### 1.3 OAuth2/OIDC 플로우 테스트
```bash
# Authorization Code 플로우 테스트
# 브라우저에서 접근:
http://localhost:8080/realms/test-realm/protocol/openid-connect/auth?client_id=test-client&redirect_uri=http://localhost:3000&response_type=code&scope=openid
```

---

### 2단계: 구글 워크스페이스 연동 준비
**목적**: SAML/OIDC Identity Provider 설정

#### 2.1 Google Workspace SAML 설정 (권장)
1. **Google Workspace Admin Console 설정**
   - Admin Console → Security → Authentication → SSO with third party IdP
   - SAML 2.0 설정 활성화
   - SSO URL: `http://localhost:8080/realms/company-realm/protocol/saml`
   - Entity ID: `http://localhost:8080/realms/company-realm`
   - Certificate 다운로드

2. **Keycloak에서 Identity Provider 설정**
   - Identity Providers → Add provider → SAML v2.0
   - Alias: `google-workspace`
   - Display Name: `Google Workspace`
   - Single Sign-On Service URL: (Google에서 제공)
   - Single Logout Service URL: (Google에서 제공)
   - Validate Signature: ON
   - Validating X509 Certificate: (Google에서 다운로드한 인증서 붙여넣기)
   - Principal Type: `Subject NameID`
   - NameID Policy Format: `email`

3. **User Attribute Mapping**
   - Mappers → Create
     - Name: `email`
     - Mapper Type: `Attribute Importer`
     - User Attribute: `email`
     - SAML Attribute Name: `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress`

#### 2.2 Google Workspace OIDC 설정 (대안)
1. **Google Cloud Console에서 OAuth 2.0 클라이언트 생성**
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: Web application
   - Authorized redirect URIs: 
     - `http://localhost:8080/realms/company-realm/broker/google/endpoint`

2. **Keycloak에서 Identity Provider 설정**
   - Identity Providers → Add provider → Google
   - Client ID: (Google Cloud Console에서 생성한 값)
   - Client Secret: (Google Cloud Console에서 생성한 값)
   - Default Scopes: `openid email profile`

---

### 3단계: RDS Aurora 접근 설정
**목적**: IAM Database Authentication 또는 데이터베이스 사용자 인증

#### 3.1 IAM Database Authentication 사용 (권장)
**전제조건**: RDS Aurora가 IAM Database Authentication 활성화되어 있어야 함

1. **Keycloak에서 RDS 접근을 위한 Client 생성**
   - Realm: `company-realm`
   - Client ID: `rds-aurora-client`
   - Client Protocol: `openid-connect`
   - Access Type: `confidential`
   - Service Accounts Enabled: ON
   - Save

2. **Service Account Role 할당**
   - Service Account Roles 탭
   - Client Roles: `realm-management` → `view-users` 추가

3. **AWS IAM 역할 설정** (AWS에서)
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "rds-db:connect"
         ],
         "Resource": "arn:aws:rds-db:region:account-id:dbuser:cluster-id/db-username"
       }
     ]
   }
   ```

4. **테스트 스크립트 예시**
   ```python
   # Keycloak에서 토큰 발급
   import requests
   
   token_url = "http://localhost:8080/realms/company-realm/protocol/openid-connect/token"
   data = {
       "grant_type": "client_credentials",
       "client_id": "rds-aurora-client",
       "client_secret": "your-client-secret"
   }
   response = requests.post(token_url, data=data)
   token = response.json()["access_token"]
   
   # RDS Aurora 연결 (IAM 인증 사용)
   # psql 또는 애플리케이션에서 토큰을 사용하여 연결
   ```

#### 3.2 데이터베이스 사용자 인증 (대안)
- Keycloak에서 사용자 인증 후, RDS 접근 권한을 부여하는 방식
- 사용자 그룹/역할 기반으로 RDS 접근 제어

---

### 4단계: EKS Private Access 설정
**목적**: Kubernetes 인증을 위한 OIDC 연동

#### 4.1 EKS OIDC Identity Provider 설정
**전제조건**: EKS 클러스터에 OIDC Identity Provider가 설정되어 있어야 함

1. **EKS 클러스터 OIDC Issuer 확인**
   ```bash
   aws eks describe-cluster --name your-cluster-name --query "cluster.identity.oidc.issuer" --output text
   ```

2. **Keycloak에서 EKS 접근용 Client 생성**
   - Realm: `company-realm`
   - Client ID: `eks-access-client`
   - Client Protocol: `openid-connect`
   - Access Type: `confidential`
   - Valid Redirect URIs: `http://localhost:8080/realms/company-realm/*`
   - Standard Flow Enabled: ON
   - Direct Access Grants Enabled: ON

3. **AWS IAM 역할 설정** (AWS에서)
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Federated": "arn:aws:iam::account-id:oidc-provider/oidc.eks.region.amazonaws.com/id/oidc-id"
         },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": {
             "oidc.eks.region.amazonaws.com/id/oidc-id:sub": "system:serviceaccount:namespace:service-account-name",
             "oidc.eks.region.amazonaws.com/id/oidc-id:aud": "sts.amazonaws.com"
           }
         }
       }
     ]
   }
   ```

4. **Kubernetes ServiceAccount 설정**
   ```yaml
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: keycloak-authenticated-sa
     namespace: default
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::account-id:role/eks-keycloak-role
   ```

5. **테스트**
   ```bash
   # Keycloak에서 토큰 발급 후
   # kubectl 또는 애플리케이션에서 사용
   kubectl --token=<keycloak-token> get pods
   ```

---

## 다음 단계 체크리스트

### 즉시 테스트 가능
- [ ] 1단계: 기본 인증 테스트 완료
- [ ] 테스트 사용자로 로그인 확인
- [ ] OAuth2 Authorization Code 플로우 테스트

### 구글 워크스페이스 연동
- [ ] Google Workspace Admin Console 접근 권한 확인
- [ ] SAML 또는 OIDC 설정 준비
- [ ] Keycloak Identity Provider 설정
- [ ] 테스트 사용자로 SSO 로그인 확인

### RDS Aurora 접근
- [ ] RDS Aurora IAM Database Authentication 활성화 여부 확인
- [ ] AWS IAM 역할/정책 설정
- [ ] Keycloak Client 및 Service Account 설정
- [ ] 토큰 기반 RDS 연결 테스트

### EKS Private Access
- [ ] EKS 클러스터 OIDC Identity Provider 확인
- [ ] AWS IAM 역할 설정
- [ ] Kubernetes ServiceAccount 설정
- [ ] Keycloak 토큰으로 EKS 접근 테스트

---

## 유용한 명령어

```bash
# Keycloak Pod 로그 확인
kubectl logs -f deployment/keycloak

# Keycloak 설정 확인
kubectl exec -it deployment/keycloak -- /opt/keycloak/bin/kc.sh show-config

# Realm Export (백업)
kubectl exec -it deployment/keycloak -- /opt/keycloak/bin/kc.sh export --file /tmp/realm-export.json --realm test-realm

# Realm Import
kubectl exec -it deployment/keycloak -- /opt/keycloak/bin/kc.sh import --file /tmp/realm-export.json
```

---

## 주의사항

1. **로컬 테스트 환경**: 현재 `localhost:8080`으로 설정되어 있음. 프로덕션에서는 실제 도메인으로 변경 필요
2. **보안**: Admin 비밀번호를 프로덕션에서는 강력한 값으로 변경
3. **HTTPS**: 프로덕션에서는 반드시 HTTPS 사용
4. **네트워크**: Private RDS/EKS 접근을 위해서는 적절한 네트워크 설정 필요 (VPC, Security Groups 등)

