# app/auth.py
import os
import time
import httpx
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from app.config import settings
from urllib.parse import urlencode
from fastapi.exceptions import HTTPException
from app.utils.auth_utils import decode_access_token

os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "1"

router = APIRouter()

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


# Attempt to refresh access token using refresh_token
async def refresh_access_token(request: Request) -> bool:
    token_data = request.session.get("token")
    if not token_data:
        return False

    expires_at = token_data.get("expires_at")
    refresh_token = token_data.get("refresh_token")

    if expires_at and expires_at > time.time():
        return True

    try:
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

        request.session["token"].update(
            {
                "access_token": token["access_token"],
                "refresh_token": token.get("refresh_token", refresh_token),
                "expires_at": int(time.time()) + token.get("expires_in", 300),
            }
        )
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
async def callback(request: Request):
    oauth = request.app.state.oauth
    try:
        print("[DEBUG] Callback started")
        token = await oauth.keycloak.authorize_access_token(request)
        print(f"[DEBUG] Token keys: {list(token.keys())}")
        user = token.get("userinfo")
        if not user:
            user = await oauth.keycloak.userinfo(token=token)

        username = user.get("preferred_username")
        email = user.get("email")
        family = user.get("family_name", "")
        given = user.get("given_name", "")
        full_name = f"{family}{given}"

        print(f"[DEBUG] family_name: '{family}', given_name: '{given}'")
        print(f"[DEBUG] Constructed full_name: '{full_name}'")
        print(f"[DEBUG] Keycloak name field: '{user.get('name')}'")

        next_url = request.session.get("next", settings.BASE_URL + "/api/userinfo")
        request.session.clear()
        request.session["user"] = {
            "username": user.get("preferred_username"),
            "email": user.get("email"),
            "name": full_name,
            "family_name": family,
            "given_name": given,
        }
        request.session["token"] = {
            "access_token": token.get("access_token"),
            "refresh_token": token.get("refresh_token"),
            "expires_at": int(time.time()) + token.get("expires_in", 300),
        }
        print(f"[DEBUG] Session saved for: {user.get('preferred_username')}")
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
async def logout(request: Request):
    id_token = request.cookies.get("id_token")
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
async def get_current_user(request: Request):
    user = request.session.get("user")
    token_data = request.session.get("token")

    if user and token_data:
        if token_data.get("expires_at") and time.time() >= token_data["expires_at"]:
            if not await refresh_access_token(request):
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
        "token": request.session.get("token"),
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
