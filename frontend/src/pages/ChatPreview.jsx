import { useEffect, useRef, useState } from "react";
import { Bot, CheckCircle2, Code2, Send, ShieldCheck, Stethoscope } from "lucide-react";
import api from "../api/axios";
import AppLayout from "../components/AppLayout";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

export default function ChatPreview() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sessionToken, setSessionToken] = useState(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const { user } = useAuth();
  const { notify } = useToast();

  useEffect(() => {
    setMessages([
      {
        role: "bot",
        text: "Hello! I am your clinic assistant. I can answer questions, collect patient details, and help book appointments.",
      },
    ]);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: userMessage }]);
    setLoading(true);

    try {
      const slug = user?.tenant_slug;
      if (!slug) {
        notify("Clinic profile is missing. Please log in again.", "error");
        return;
      }

      const response = await api.post("/chat/message", {
        message: userMessage,
        tenant_slug: slug,
        session_token: sessionToken || null,
      });

      setSessionToken(response.data.session_token);
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: response.data.reply },
      ]);
    } catch {
      notify("The chat service did not respond. Try again in a moment.", "error");
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: "Sorry, something went wrong. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const widgetUrl = `${window.location.origin}/widget.html?clinic=${user?.tenant_slug || "your-clinic"}`;

  return (
    <AppLayout
      title="Chat Preview"
      subtitle="Test the same polished experience patients see on your website."
    >
      <div className="chat-preview-grid">
        <div className="chat-phone">
          <div className="chat-phone-header">
            <div className="chat-avatar">
              <Stethoscope size={22} />
            </div>
            <div>
              <p className="chat-title">{user?.user_name || "Clinic"} Bot</p>
              <p className="chat-status">Online - ready to help patients</p>
            </div>
          </div>

          <div className="chat-messages">
            {messages.map((message, index) => (
              <div key={index} className={`chat-bubble ${message.role}`}>
                {message.text}
              </div>
            ))}
            {loading && <div className="chat-bubble bot">Typing...</div>}
            <div ref={bottomRef} />
          </div>

          <div className="chat-input-bar">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about timings, fees, or appointments..."
              disabled={loading}
            />
            <button onClick={sendMessage} disabled={loading} aria-label="Send message">
              <Send size={18} />
            </button>
          </div>
          <div className="chat-footnote">Powered by ClinicBot AI</div>
        </div>

        <aside className="preview-side">
          <div className="demo-card">
            <h2>Public widget confidence check</h2>
            <p>
              This preview now matches the embedded widget style, so clinic owners
              can trust what patients will see before they publish it.
            </p>
            <div className="demo-list">
              <span><CheckCircle2 size={17} /> Real clinic slug, no hardcoded fallback</span>
              <span><Bot size={17} /> Same WhatsApp-style chat surface</span>
              <span><ShieldCheck size={17} /> Patient data stays scoped to this clinic</span>
            </div>
          </div>

          <div className="demo-card">
            <h2>Embed link</h2>
            <p>Use this public URL while testing website embeds.</p>
            <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
              <input className="input" value={widgetUrl} readOnly style={{ flex: 1, minWidth: 0 }} />
              <button
                className="icon-btn"
                onClick={() => {
                  navigator.clipboard?.writeText(widgetUrl);
                  notify("Widget link copied.", "success");
                }}
                title="Copy widget link"
              >
                <Code2 size={17} />
              </button>
            </div>
          </div>
        </aside>
      </div>
    </AppLayout>
  );
}
