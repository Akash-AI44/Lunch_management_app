from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import admin, auth, employee
from app.services.exceptions import ServiceError

app = FastAPI(
    title="Lunch Management System API",
    description="Internal lunch ordering API — employee opt-in/opt-out with superadmin reporting.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ServiceError)
def handle_service_error(request: Request, exc: ServiceError):
    """Translates any domain exception raised by the service layer into
    an HTTP response. This is the ONLY place service errors become HTTP
    status codes — routers just let them propagate."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.mount("/media", StaticFiles(directory=settings.MEDIA_ROOT), name="media")

app.include_router(auth.router)
app.include_router(employee.router)
app.include_router(admin.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
