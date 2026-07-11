from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database import init_db
from app.routers import auth, profiles, jobs, applications

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize CockroachDB tables on startup
    try:
        await init_db()
        print("Successfully connected to CockroachDB and synchronized tables.")
    except Exception as e:
        print(f"Error initializing CockroachDB: {e}")
    yield

app = FastAPI(
    title="Recruitment Platform API",
    description="Production-grade backend API for Naukri/Indeed Clone using FastAPI and CockroachDB.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for local development and Vercel hosting
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production domains when finalized
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(jobs.router)
app.include_router(applications.router)

# --- Global Exception Handlers ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global fallback error handler to format errors cleanly as JSON."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"An internal server error occurred: {str(exc)}"},
    )

@app.get("/")
def read_root():
    """Basic health check route."""
    return {"status": "healthy", "service": "recruitment-platform-api"}
