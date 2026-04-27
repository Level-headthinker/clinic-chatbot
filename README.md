# ClinicBot — AI Chatbot Platform for Clinics

A multi-tenant AI chatbot SaaS platform built for clinics and healthcare providers.
Allows patients to book appointments, ask questions, and get instant responses
in both English and Urdu through an intelligent conversational interface.

---

## Live Demo

- Admin Dashboard: http://localhost:3000
- API Documentation: http://localhost:8000/docs

Demo credentials:
- Email: admin@cityclinic.com
- Password: admin123

---

## What It Does

- Patients chat with an AI assistant on the clinic website
- Bot understands English and Urdu (Roman + script)
- Automatically collects patient name, phone, and concern
- Books appointments with available doctors
- Detects medical emergencies and responds with emergency numbers
- Admin dashboard to manage doctors, appointments, and leads
- Multi-tenant — each clinic has its own isolated bot and data

---

## Tech Stack

| Layer       | Technology                        |
|-------------|-----------------------------------|
| Backend     | FastAPI (Python)                  |
| Frontend    | React.js                          |
| Database    | PostgreSQL                        |
| AI / LLM    | Groq API (Llama 3.1 70B — free)   |
| Auth        | JWT Tokens                        |
| Styling     | Inline React styles               |

---

## Project Structure
```
clinic-chatbot/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── tenant.py
│   │   │   ├── user.py
│   │   │   ├── doctor.py
│   │   │   ├── appointment.py
│   │   │   └── chat.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   │   │   ├── doctors.py
│   │   │   ├── appointments.py
│   │   │   └── leads.py
│   │   ├── services/
│   │   │   ├── auth.py
│   │   │   └── llm.py
│   │   ├── config.py
│   │   └── database.py
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── api/
│       │   └── axios.js
│       ├── context/
│       │   └── AuthContext.jsx
│       ├── pages/
│       │   ├── Login.jsx
│       │   ├── Dashboard.jsx
│       │   ├── Doctors.jsx
│       │   ├── Appointments.jsx
│       │   ├── Leads.jsx
│       │   └── ChatPreview.jsx
│       ├── components/
│       │   └── Sidebar.jsx
│       └── App.js
└── README.md
```
---

## Features

### Chatbot
- Natural language understanding via Llama 3.1 70B
- English and Urdu language support
- Emergency detection — bypasses AI for critical keywords
- Session-based memory — bot remembers conversation context
- Auto lead capture when name and phone are collected
- Intent detection — booking, enquiry, fees, timings

### Admin Dashboard
- Secure login with JWT authentication
- Doctor management — add, update, remove doctors
- Appointment tracking — view, confirm, cancel, complete
- Lead management — track follow-up status
- Stats overview — total leads, conversion rate
- Live chat preview — test bot as a patient

### Multi-Tenant Architecture
- Each clinic has completely isolated data
- Unique clinic slug for identification
- Per-tenant bot name and welcome message
- Subscription plan field ready for billing

---

## API Endpoints

### Auth
| Method | Endpoint         | Description          | Auth |
|--------|-----------------|----------------------|------|
| POST   | /auth/register  | Register new clinic  | No   |
| POST   | /auth/login     | Admin login          | No   |

### Chat
| Method | Endpoint                      | Description           | Auth |
|--------|------------------------------|-----------------------|------|
| POST   | /chat/message                | Send message to bot   | No   |
| GET    | /chat/session/{token}        | Get chat history      | No   |

### Doctors
| Method | Endpoint           | Description        | Auth |
|--------|-------------------|--------------------|------|
| GET    | /doctors/          | List all doctors   | Yes  |
| POST   | /doctors/          | Add a doctor       | Yes  |
| PUT    | /doctors/{id}      | Update doctor      | Yes  |
| DELETE | /doctors/{id}      | Remove doctor      | Yes  |

### Appointments
| Method | Endpoint                  | Description           | Auth |
|--------|--------------------------|------------------------|------|
| POST   | /appointments/book        | Book appointment       | No   |
| GET    | /appointments/            | List appointments      | Yes  |
| PUT    | /appointments/{id}        | Update status          | Yes  |
| DELETE | /appointments/{id}        | Cancel appointment     | Yes  |

### Leads
| Method | Endpoint         | Description        | Auth |
|--------|-----------------|---------------------|------|
| GET    | /leads/          | List all leads      | Yes  |
| PUT    | /leads/{id}      | Update lead status  | Yes  |
| DELETE | /leads/{id}      | Remove lead         | Yes  |
| GET    | /leads/stats     | Lead statistics     | Yes  |

---

## Getting Started

### Prerequisites

- Python 3.11
- Node.js 18+
- PostgreSQL 14+
- Groq API key — free at console.groq.com

### Backend Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/clinic-chatbot.git
cd clinic-chatbot/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your PostgreSQL password and Groq API key

# Start the server
uvicorn main:app --reload
```

Backend runs at: http://127.0.0.1:8000
API docs at: http://127.0.0.1:8000/docs

### Frontend Setup

```bash
cd clinic-chatbot/frontend

# Install dependencies
npm install

# Start React app
npm start
```

Frontend runs at: http://localhost:3000

### Database Setup

1. Open pgAdmin
2. Create a new database called `clinic_chatbot`
3. Tables are created automatically when backend starts

### Register Your First Clinic

Send a POST request to `/auth/register`:

```json
{
  "clinic_name": "Your Clinic Name",
  "clinic_slug": "your-clinic",
  "admin_email": "admin@yourclinic.com",
  "admin_password": "yourpassword",
  "admin_full_name": "Your Name"
}
```

---

## Environment Variables

Create a `.env` file in the backend folder:
