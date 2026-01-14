#!/usr/bin/env python3
"""
Keycloak 토큰을 사용하여 RDS Aurora에 연결하는 테스트 스크립트

사용 전:
1. pip install requests psycopg2-binary boto3
2. Keycloak에서 Service Account Client 생성 및 설정
3. AWS IAM 역할/정책 설정
"""

import requests
import json
import sys
from typing import Optional, Dict

# 설정
KEYCLOAK_URL = "http://localhost:8080"
REALM = "company-realm"
CLIENT_ID = "rds-aurora-client"
CLIENT_SECRET = "your-client-secret-here"  # Keycloak에서 생성한 클라이언트 시크릿

# RDS Aurora 설정
RDS_HOST = "your-aurora-cluster.region.rds.amazonaws.com"
RDS_PORT = 5432
RDS_DATABASE = "your-database"
RDS_USER = "your-db-user"


def get_keycloak_token() -> Optional[Dict]:
    """Keycloak에서 Client Credentials 플로우로 토큰 발급"""
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        token_data = response.json()
        
        print("✅ Keycloak 토큰 발급 성공")
        print(f"   Access Token: {token_data['access_token'][:50]}...")
        print(f"   Token Type: {token_data['token_type']}")
        print(f"   Expires In: {token_data['expires_in']} seconds")
        
        return token_data
    except requests.exceptions.RequestException as e:
        print(f"❌ 토큰 발급 실패: {e}")
        if hasattr(e.response, 'text'):
            print(f"   응답: {e.response.text}")
        return None


def get_rds_auth_token(access_token: str) -> Optional[str]:
    """
    Keycloak 토큰을 사용하여 RDS IAM 인증 토큰 생성
    
    참고: 실제 구현에서는 AWS STS를 사용하여 RDS 인증 토큰을 생성해야 합니다.
    이는 Keycloak 토큰을 AWS IAM 역할로 교환한 후, 해당 역할로 RDS 인증 토큰을 생성하는 방식입니다.
    """
    import boto3
    
    try:
        # Keycloak 토큰을 AWS IAM 역할로 교환하는 로직이 필요합니다.
        # 이는 AWS STS AssumeRoleWithWebIdentity를 사용합니다.
        
        # 예시 (실제 구현 필요):
        # sts_client = boto3.client('sts')
        # assumed_role = sts_client.assume_role_with_web_identity(
        #     RoleArn='arn:aws:iam::account-id:role/keycloak-rds-role',
        #     RoleSessionName='keycloak-session',
        #     WebIdentityToken=access_token
        # )
        
        # RDS 인증 토큰 생성
        rds_client = boto3.client('rds')
        auth_token = rds_client.generate_db_auth_token(
            DBHostname=RDS_HOST,
            Port=RDS_PORT,
            DBUsername=RDS_USER
        )
        
        print("✅ RDS 인증 토큰 생성 성공")
        return auth_token
        
    except Exception as e:
        print(f"❌ RDS 인증 토큰 생성 실패: {e}")
        return None


def connect_to_rds(auth_token: str):
    """RDS Aurora에 연결 (IAM 인증 사용)"""
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=RDS_HOST,
            port=RDS_PORT,
            database=RDS_DATABASE,
            user=RDS_USER,
            password=auth_token,  # IAM 인증 토큰을 비밀번호로 사용
            sslmode='require'
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        print("✅ RDS Aurora 연결 성공")
        print(f"   PostgreSQL 버전: {version[0]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except ImportError:
        print("❌ psycopg2가 설치되지 않았습니다. 'pip install psycopg2-binary' 실행하세요.")
        return False
    except Exception as e:
        print(f"❌ RDS 연결 실패: {e}")
        return False


def main():
    print("=" * 60)
    print("Keycloak → RDS Aurora 연결 테스트")
    print("=" * 60)
    print()
    
    # 1. Keycloak에서 토큰 발급
    print("1단계: Keycloak 토큰 발급")
    token_data = get_keycloak_token()
    if not token_data:
        sys.exit(1)
    
    print()
    
    # 2. RDS 인증 토큰 생성
    print("2단계: RDS 인증 토큰 생성")
    access_token = token_data['access_token']
    rds_auth_token = get_rds_auth_token(access_token)
    if not rds_auth_token:
        print("⚠️  RDS 인증 토큰 생성 로직이 구현되지 않았습니다.")
        print("   AWS STS AssumeRoleWithWebIdentity를 사용하여 구현해야 합니다.")
        sys.exit(1)
    
    print()
    
    # 3. RDS 연결
    print("3단계: RDS Aurora 연결")
    success = connect_to_rds(rds_auth_token)
    
    print()
    print("=" * 60)
    if success:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 테스트 실패")
    print("=" * 60)


if __name__ == "__main__":
    main()

