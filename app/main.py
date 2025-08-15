# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
#from fastapi.middleware.cors import CORSMiddleware
from app.auth import router as auth_router, init_oauth, ReauthRequired
#from app.routes import 
from app.config import settings
from urllib.parse import quote
from contextlib import asynccontextmanager
from fastapi.openapi.utils import get_openapi
from app.routes import complaints_router, files_router, categories_router, departments_router

# from app.database import MariaDBBase, mariadb_engine
# MariaDBBase.metadata.create_all(bind=mariadb_engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.oauth = await init_oauth()
    yield


app = FastAPI(lifespan=lifespan)

@app.exception_handler(ReauthRequired)
async def reauth_redirect_handler(request: Request, exc: ReauthRequired):
    return RedirectResponse(url=f"/api/login?next={quote(exc.next_url)}")


# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.FRONTEND_URL,
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
#     allow_headers=["*"],
# )

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET,
    same_site="lax",
    session_cookie="minwon_session",
    https_only=False,
)

app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(complaints_router, prefix="/api/complaints", tags=["complaint"])
app.include_router(files_router, prefix="/api/files", tags=["file"])
app.include_router(categories_router,  prefix="/api/categories",  tags=["category"])
app.include_router(departments_router, prefix="/api/departments", tags=["department"])

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Minwoneasy API",
        version="1.0.0",
        description="API docs for Minwoneasy",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/")
def root():
    return {"message": "Welcome to the Minwoneasy!"}



