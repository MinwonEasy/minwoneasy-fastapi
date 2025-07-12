# app/utils/auth_utils.py
import httpx
from jwt import decode, get_unverified_header
from jwt import algorithms
from fastapi import HTTPException
from app.config import settings


def decode_access_token(token: str) -> dict:
    try:
        jwks_url = f"{settings.ISSUER_BASE_URL}/protocol/openid-connect/certs"

        headers = get_unverified_header(token)
        kid = headers["kid"]

        with httpx.Client(verify=False) as client:
            jwks_response = client.get(jwks_url)
            jwks = jwks_response.json()

        key = next(k for k in jwks["keys"] if k["kid"] == kid)
        public_key = algorithms.RSAAlgorithm.from_jwk(key)

        payload = decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload

    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid access token: {e}")
