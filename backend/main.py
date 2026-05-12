from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, chat, doctors, appointments, leads, superadmin, patients, visits, billing

app = FastAPI(
    title="Clinic Chatbot API",
    description="Multi-tenant AI chatbot platform for clinics",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(leads.router)
app.include_router(superadmin.router)
app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(billing.router)

@app.get("/")
def root():
    return {
        "message": "Clinic Chatbot API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "healthy"}