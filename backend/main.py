import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base

# Import all models so create_all sees them
import app.models  # noqa — registers all models with Base.metadata for create_all

from app.routers import auth, chat, dashboard, doctors, appointments, leads, superadmin, patients, visits, billing, branches, users, follow_ups, prescriptions, notes, voice


def create_tables_with_retry(retries: int = 5, delay: int = 5):
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Database tables ready")
            return
        except Exception as e:
            print(f"⚠️  DB attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError("❌ Could not connect to database after all retries")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs AFTER uvicorn starts — DB has time to wake up
    create_tables_with_retry()
    yield
    # Anything after yield runs on shutdown (nothing needed here)


app = FastAPI(
    title="Clinic Chatbot API",
    description="Multi-tenant AI chatbot platform for clinics",
    version="1.0.0",
    lifespan=lifespan      # ← key change
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(leads.router)
app.include_router(superadmin.router)
app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(billing.router)
app.include_router(branches.router)
app.include_router(users.router)
app.include_router(dashboard.router)
app.include_router(follow_ups.router)
app.include_router(prescriptions.router)
app.include_router(notes.router)
app.include_router(voice.router)


@app.get("/")
def root():
    return {"message": "Clinic Chatbot API is running", "version": "1.0.0", "docs": "/docs"}


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "healthy"}