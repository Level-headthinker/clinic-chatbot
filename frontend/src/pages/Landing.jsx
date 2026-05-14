import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Bot,
  CalendarCheck,
  CheckCircle2,
  CreditCard,
  Languages,
  MessageCircle,
  ShieldCheck,
  Stethoscope,
  Users,
} from "lucide-react";

const demoMessages = [
  { role: "bot", text: "Assalam o Alaikum! City Clinic mein khush amdeed. Aap appointment book karna chahte hain?" },
  { role: "user", text: "Mujhe skin rash ke liye doctor chahiye" },
  { role: "bot", text: "Bilkul. Dr. Sana Dermatologist available hain. Apna naam aur phone number share kar dein." },
  { role: "user", text: "Ali, 03001234567" },
  { role: "bot", text: "Available slot: Friday, 15 May 2026 at 04:30 PM. Reply yes to confirm." },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="landing">
      <nav className="landing-nav">
        <div className="landing-logo">
          <span className="brand-mark">
            <Stethoscope size={22} />
          </span>
          ClinicBot
        </div>
        <div className="hero-actions" style={{ margin: 0 }}>
          <button className="btn btn-secondary" onClick={() => navigate("/login")}>
            Login
          </button>
          <button className="btn btn-primary" onClick={() => navigate("/register")}>
            Start free
            <ArrowRight size={16} />
          </button>
        </div>
      </nav>

      <section className="landing-hero">
        <div className="hero-copy">
          <h1>AI receptionist for Pakistani clinics</h1>
          <p>
            Capture patient leads, book appointments in Urdu or English, manage
            doctors, visits, and billing from one simple clinic dashboard.
          </p>
          <div className="hero-actions">
            <button className="btn btn-primary" onClick={() => navigate("/register")}>
              Register clinic
              <ArrowRight size={16} />
            </button>
            <a className="btn btn-secondary" href="#demo">
              Try chat demo
              <MessageCircle size={16} />
            </a>
          </div>
          <div className="trust-row">
            <div className="trust-pill">PKR 3,000/month after trial</div>
            <div className="trust-pill">Urdu, Roman Urdu, English</div>
            <div className="trust-pill">Built for repeat clinic work</div>
          </div>
        </div>

        <div id="demo" className="chat-phone">
          <div className="chat-phone-header">
            <div className="chat-avatar">
              <Bot size={22} />
            </div>
            <div>
              <p className="chat-title">City Clinic Bot</p>
              <p className="chat-status">Online - books appointments instantly</p>
            </div>
          </div>
          <div className="chat-messages">
            {demoMessages.map((message, index) => (
              <div key={index} className={`chat-bubble ${message.role}`}>
                {message.text}
              </div>
            ))}
          </div>
          <div className="chat-input-bar">
            <input value="Yes confirm please" readOnly />
            <button aria-label="Send demo message">
              <ArrowRight size={18} />
            </button>
          </div>
          <div className="chat-footnote">Public patient widget preview</div>
        </div>
      </section>

      <section className="landing-section">
        <div className="section-heading">
          <h2>One workflow from inquiry to invoice</h2>
          <p>
            Clinics do not need separate notebooks, WhatsApp follow-ups, and
            billing sheets. ClinicBot keeps the patient journey connected.
          </p>
        </div>
        <div className="feature-grid">
          {[
            {
              icon: <Languages size={22} />,
              title: "Bilingual patient chat",
              text: "Patients can ask in English, Urdu script, or Roman Urdu without learning a portal.",
            },
            {
              icon: <CalendarCheck size={22} />,
              title: "Real appointment flow",
              text: "Doctor timings and available slots are shown before a booking is saved.",
            },
            {
              icon: <Users size={22} />,
              title: "Lead capture",
              text: "Every name and phone number becomes a follow-up lead for clinic staff.",
            },
            {
              icon: <CreditCard size={22} />,
              title: "Clinic billing",
              text: "Record visits, fees, partial payments, and invoice status in one place.",
            },
            {
              icon: <ShieldCheck size={22} />,
              title: "Multi-tenant SaaS",
              text: "One platform can serve unlimited clinics with separated clinic data.",
            },
            {
              icon: <CheckCircle2 size={22} />,
              title: "Affordable rollout",
              text: "Designed for small and midsize Pakistani clinics, not enterprise-only hospitals.",
            },
          ].map((feature) => (
            <article className="feature-card" key={feature.title}>
              <div className="metric-icon">{feature.icon}</div>
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
