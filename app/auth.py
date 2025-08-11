import os
import time
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from app.config import settings
from urllib.parse import urlencode
from fastapi.exceptions import HTTPException
from app.utils.auth_utils import decode_access_token
from app.database import get_db
from sqlalchemy.orm import Session
from app.user.user_models import User
from app.user_token.token_models import UserToken
from cryptography.fernet import Fernet
import secrets

os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "1"

router = APIRouter()

def get_cipher_suite():
    return Fernet(settings.encryption_key)

# Custom exception to trigger re-authentication
class ReauthRequired(Exception):
    def __init__(self, next_url: str):
        self.next_url = next_url


# Initialize OAuth client using Keycloak metadata
async def init_oauth() -> OAuth:
    metadata_url = f"{settings.ISSUER_BASE_URL}/.well-known/openid-configuration"
    try:
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            response = await client.get(metadata_url)
            response.raise_for_status()
            metadata = response.json()

        oauth = OAuth()
        oauth.register(
            name="keycloak",
            client_id=settings.CLIENT_ID,
            client_secret=settings.CLIENT_SECRET,
            authorize_url=metadata["authorization_endpoint"],
            access_token_url=metadata["token_endpoint"],
            refresh_token_url=metadata["token_endpoint"],
            userinfo_url=metadata["userinfo_endpoint"],
            jwks_uri=metadata.get("jwks_uri"),
            client_kwargs={"scope": "openid email profile", "verify": False},
        )

        print("[DEBUG] ✅ OAuth registered successfully!")
        return oauth

    except Exception as e:
        print(f"[ERROR] init_oauth failed: {e}")
        raise


def encrypt_token(token: str) -> str:
    cipher_suite = get_cipher_suite()
    return cipher_suite.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    cipher_suite = get_cipher_suite()
    return cipher_suite.decrypt(encrypted_token.encode()).decode()


async def save_refresh_token(db: Session, user_id: int, refresh_token: str, device_info: str = None) -> None:
    try:
        db.query(UserToken).filter(
            UserToken.user_id == user_id,
            UserToken.device_info == device_info
        ).delete()

        encrypted_token = encrypt_token(refresh_token)
        expires_at = datetime.now() + timedelta(days=30)  # 30일 후 만료

        new_token = UserToken(
            user_id=user_id,
            refresh_token_encrypted=encrypted_token,
            expires_at=expires_at,
            device_info=device_info
        )

        db.add(new_token)
        db.commit()
        print(f"[DEBUG] ✅ Refresh token saved for user {user_id}")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to save refresh token: {e}")
        raise


async def get_refresh_token(db: Session, user_id: int, device_info: str = None) -> str:
    try:
        token_record = db.query(UserToken).filter(
            UserToken.user_id == user_id,
            UserToken.device_info == device_info,
            UserToken.expires_at > datetime.now()
        ).first()

        if not token_record:
            return None

        return decrypt_token(token_record.refresh_token_encrypted)

    except Exception as e:
        print(f"[ERROR] Failed to get refresh token: {e}")
        return None


async def delete_refresh_token(db: Session, user_id: int, device_info: str = None) -> None:
    try:
        db.query(UserToken).filter(
            UserToken.user_id == user_id,
            UserToken.device_info == device_info
        ).delete()
        db.commit()
        print(f"[DEBUG] ✅ Refresh token deleted for user {user_id}")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to delete refresh token: {e}")


async def get_or_create_user(db: Session, keycloak_user: dict) -> User:
    keycloak_user_id = keycloak_user.get("sub")
    email = keycloak_user.get("email")

    user = db.query(User).filter(User.keycloak_user_id == keycloak_user_id).first()

    if not user:
        family_name = keycloak_user.get("family_name", "")
        given_name = keycloak_user.get("given_name", "")
        display_name = f"{family_name}{given_name}"

        user = User(
            keycloak_user_id=keycloak_user_id,
            email=email,
            family_name=family_name,
            given_name=given_name,
            display_name=display_name
        )

        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[DEBUG] ✅ New user created: {email}")
    else:
        print(f"[DEBUG] ✅ Existing user found: {email}")

    return user


# Attempt to refresh access token using refresh_token from DB
async def refresh_access_token(request: Request, db: Session) -> bool:
    user_session = request.session.get("user")
    if not user_session:
        return False

    try:
        user = db.query(User).filter(User.email == user_session["email"]).first()
        if not user:
            return False

        device_info = request.headers.get("user-agent", "unknown")[:100]

        refresh_token = await get_refresh_token(db, user.user_id, device_info)
        if not refresh_token:
            return False

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{settings.ISSUER_BASE_URL}/protocol/openid-connect/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.CLIENT_ID,
                    "client_secret": settings.CLIENT_SECRET,
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token = response.json()

        print("[DEBUG] 🔁 Token refreshed successfully")


        new_refresh_token = token.get("refresh_token")
        if new_refresh_token:
            await save_refresh_token(db, user.user_id, new_refresh_token, device_info)

        request.session["token"] = {
            "access_token": token["access_token"],
            "expires_at": int(time.time()) + token.get("expires_in", 300),
        }
        return True

    except Exception as e:
        print(f"[ERROR] Failed to refresh token: {e}")
        request.session.clear()
        return False


# Redirects user to Keycloak login page
# @router.get("/login")
# async def login(request: Request, next: str = None):
#     oauth = request.app.state.oauth
#     redirect_uri = settings.BASE_URL + "/api/callback"

#     raw_next = next or request.headers.get("referer") or "/"
#     if raw_next.endswith("/logout") or "/logged-out" in raw_next:
#         raw_next = "/api/userinfo"

#     request.session.clear()
#     request.session["next"] = raw_next

#     print(f"[DEBUG] Login redirect_uri: {redirect_uri}, next: {raw_next}")
#     return await oauth.keycloak.authorize_redirect(request, redirect_uri)
@router.get("/login")
async def login(request: Request, next: str = None):
    oauth = request.app.state.oauth
    redirect_uri = settings.BASE_URL + "/api/callback"

    raw_next = "/api/userinfo"

    request.session.clear()
    request.session["next"] = raw_next

    print(f"[DEBUG] Login redirect_uri: {redirect_uri}, next: {raw_next}")
    return await oauth.keycloak.authorize_redirect(request, redirect_uri)


# Handles Keycloak OAuth2 callback and saves user session
@router.get("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    oauth = request.app.state.oauth
    try:
        print("[DEBUG] Callback started")
        token = await oauth.keycloak.authorize_access_token(request)

        user_info = token.get("userinfo")
        if not user_info:
            user_info = await oauth.keycloak.userinfo(token=token)

        user = await get_or_create_user(db, user_info)

        device_info = request.headers.get("user-agent", "unknown")[:100]

        refresh_token = token.get("refresh_token")
        if refresh_token:
            await save_refresh_token(db, user.user_id, refresh_token, device_info)

        next_url = request.session.get("next", settings.BASE_URL + "/api/userinfo")
        request.session.clear()
        request.session["user"] = {
            "user_id": user.user_id,
            "username": user_info.get("preferred_username"),
            "email": user.email,
            "name": user.display_name,
            "family_name": user.family_name,
            "given_name": user.given_name,
        }
        request.session["token"] = {
            "access_token": token.get("access_token"),
            "expires_at": int(time.time()) + token.get("expires_in", 300),
        }
        print(f"[DEBUG] Session saved for: {user.email}")
        response = RedirectResponse(url=next_url)
        response.set_cookie(
            "id_token", token.get("id_token"), httponly=True, secure=False, max_age=3600
        )
        return response
    except Exception as e:
        print(f"[ERROR] Callback error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url=settings.BASE_URL + "/api/logged-out")


# Redirects to Keycloak logout endpoint and clears session
@router.get("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get("user")
    id_token = request.cookies.get("id_token")
    if user_session and user_session.get("user_id"):
        device_info = request.headers.get("user-agent", "unknown")[:100]
        await delete_refresh_token(db, user_session["user_id"], device_info)

    request.session.clear()

    if id_token:
        logout_url = (
                f"{settings.ISSUER_BASE_URL}/protocol/openid-connect/logout?"
                + urlencode(
            {
                "id_token_hint": id_token,
                "post_logout_redirect_uri": settings.BASE_URL + "/api/logged-out",
            }
        )
        )
        print(f"[DEBUG] Redirecting to Keycloak logout: {logout_url}")
        response = RedirectResponse(logout_url)
    else:
        response = RedirectResponse(settings.BASE_URL + "/api/logged-out")

    response.delete_cookie("minwon_session", path="/")
    response.delete_cookie("id_token")
    return response

@router.get("/logged-out")
async def logged_out():
    return RedirectResponse(settings.BASE_URL + "/")

# Extracts current user from session or bearer token
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    token_data = request.session.get("token")

    if user and token_data:
        if token_data.get("expires_at") and time.time() >= token_data["expires_at"]:
            if not await refresh_access_token(request, db):
                raise ReauthRequired(settings.BASE_URL + "/api/userinfo")

        try:
            payload = decode_access_token(token_data["access_token"])
            roles = payload.get("realm_access", {}).get("roles", [])
        except Exception as e:
            print(f"[WARN] Failed to decode access token: {e}")
            roles = []

        # admin_role_name = settings.ADMIN_ROLE
        # is_admin = admin_role_name in roles

        return {
            "user_id": user.get("user_id"),
            "username": user.get("username"),
            "email": user.get("email"),
            "name": user.get("name"),
            "family_name": user.get("family_name", ""),
            "given_name": user.get("given_name", ""),
            "roles": roles,
        }

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = decode_access_token(token)
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

        username = (
            payload.get("preferred_username")
            or payload.get("email")
            or payload.get("sub")
        )
        email = (
            payload.get("email")
            or payload.get("preferred_username")
            or payload.get("sub")
        )

        family = payload.get("family_name", "")
        given = payload.get("given_name", "")
        name = f"{family}{given}".strip()

        if not email:
            raise HTTPException(status_code=401, detail="Email not found in token")

        roles = payload.get("realm_access", {}).get("roles", [])
        # admin_role_name = settings.ADMIN_ROLE
        # is_admin = admin_role_name in roles

        return {
            "username": username,
            "email": email,
            "name": name,
            "roles": roles,
        }

    raise HTTPException(status_code=401, detail="Authentication required")


# Returns current user info from session or token
@router.get("/userinfo")
async def userinfo(request: Request, user: dict = Depends(get_current_user)):
    return JSONResponse(content={"user": user})


# Debug helper to inspect session content
@router.get("/session-debug")
async def session_debug(request: Request):
    return {
        "session_keys": list(request.session.keys()),
        "user_in_session": "user" in request.session,
        "token_in_session": "token" in request.session,
        "has_refresh_token_in_session": False,
        "id_token": request.cookies.get("id_token"),
    }


# Get access token
@router.get("/auth/token", response_model=dict)
async def get_access_token(request: Request):
    token = request.session.get("token")
    user = request.session.get("user")

    if not token or not user:
        raise HTTPException(status_code=401, detail="Not logged in")

    return {
        "access_token": token["access_token"],
        "expires_at": token["expires_at"],
        "username": user["username"],
    }
