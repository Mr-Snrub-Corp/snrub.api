import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference
from starlette.middleware.sessions import SessionMiddleware

from .core.config import settings
from .routes.admin import router as admin_router
from .routes.auth.google import router as google_auth_router
from .routes.auth.local import router as local_auth_router
from .routes.incident_category import router as incident_category_router
from .routes.incident_report import router as incident_report_router
from .routes.incident_report_subject import router as incident_report_subject_router
from .routes.incident_type import router as incident_type_router
from .routes.telemetry import router as telemetry_router
from .routes.user import router as user_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Disable default Swagger UI docs, we'll use Scalar instead
app = FastAPI(docs_url=None, redoc_url=None)

# Add session middleware - required for OAuth flows - reusing the JWT secret balances security and simplicity
app.add_middleware(SessionMiddleware, secret_key=settings.JWT_SECRET)

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/")
def hello_world():
    return {"message": "OK"}


# Tags are already defined in each router, don't duplicate them here
app.include_router(user_router, prefix="/api")
app.include_router(incident_category_router, prefix="/api")
app.include_router(incident_type_router, prefix="/api")
app.include_router(incident_report_router, prefix="/api")
app.include_router(incident_report_subject_router, prefix="/api")
app.include_router(local_auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(google_auth_router, prefix="/api")
app.include_router(telemetry_router, prefix="/api")


@app.get("/docs", include_in_schema=False)
async def scalar_docs():
    """Serve Scalar API documentation."""
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )
