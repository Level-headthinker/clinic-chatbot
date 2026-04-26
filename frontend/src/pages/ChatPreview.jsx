import { useState, useEffect, useRef } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api/axios";
import { Send } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function ChatPreview() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sessionToken, setSessionToken] = useState(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const { user } = useAuth();

  useEffect(() => {
    setMessages([
      {
        role: "assistant",
        content: "Hello! I am your clinic assistant. How can I help you today?",
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
    setMessages((prev) => [
      ...prev,
      { role: "user", content: userMessage },
    ]);
    setLoading(true);

    try {
      const res = await api.post("/chat/message", {
        message: userMessage,
        tenant_slug: "city-clinic",
        session_token: sessionToken,
      });

      setSessionToken(res.data.session_token);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.data.reply },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, something went wrong. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div style={styles.layout}>
      <Sidebar />
      <div style={styles.main}>
        <h1 style={styles.heading}>Chat Preview</h1>
        <p style={styles.subtitle}>
          Test your chatbot exactly as patients will see it
        </p>

        <div style={styles.chatContainer}>
          <div style={styles.chatHeader}>
            <div style={styles.avatar}>🏥</div>
            <div>
              <p style={styles.botName}>ClinicBot</p>
              <p style={styles.botStatus}>● Online</p>
            </div>
          </div>

          <div style={styles.messages}>
            {messages.map((msg, i) => (
              <div
                key={i}
                style={
                  msg.role === "user"
                    ? styles.userBubbleWrap
                    : styles.botBubbleWrap
                }
              >
                <div
                  style={
                    msg.role === "user"
                      ? styles.userBubble
                      : styles.botBubble
                  }
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div style={styles.botBubbleWrap}>
                <div style={styles.botBubble}>Typing...</div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div style={styles.inputArea}>
            <input
              style={styles.input}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message..."
              disabled={loading}
            />
            <button
              onClick={sendMessage}
              style={loading ? styles.sendButtonDisabled : styles.sendButton}
              disabled={loading}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  layout: { display: "flex", minHeight: "100vh", backgroundColor: "#f8fafc" },
  main: { marginLeft: "240px", padding: "32px", flex: 1 },
  heading: { fontSize: "24px", fontWeight: "700", color: "#1e293b", marginBottom: "4px" },
  subtitle: { color: "#6b7280", fontSize: "14px", marginBottom: "24px" },
  chatContainer: {
    backgroundColor: "#fff",
    borderRadius: "16px",
    boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
    maxWidth: "600px",
    display: "flex",
    flexDirection: "column",
    height: "600px",
    overflow: "hidden",
  },
  chatHeader: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "16px 20px",
    backgroundColor: "#1e3a5f",
    borderRadius: "16px 16px 0 0",
  },
  avatar: {
    fontSize: "28px",
    backgroundColor: "#fff",
    borderRadius: "50%",
    width: "44px",
    height: "44px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  botName: { color: "#fff", fontWeight: "600", margin: 0, fontSize: "15px" },
  botStatus: { color: "#86efac", fontSize: "12px", margin: 0 },
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: "20px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  botBubbleWrap: { display: "flex", justifyContent: "flex-start" },
  userBubbleWrap: { display: "flex", justifyContent: "flex-end" },
  botBubble: {
    backgroundColor: "#f1f5f9",
    color: "#1e293b",
    padding: "12px 16px",
    borderRadius: "16px 16px 16px 4px",
    maxWidth: "75%",
    fontSize: "14px",
    lineHeight: "1.5",
  },
  userBubble: {
    backgroundColor: "#2563eb",
    color: "#fff",
    padding: "12px 16px",
    borderRadius: "16px 16px 4px 16px",
    maxWidth: "75%",
    fontSize: "14px",
    lineHeight: "1.5",
  },
  inputArea: {
    display: "flex",
    gap: "8px",
    padding: "16px",
    borderTop: "1px solid #e5e7eb",
  },
  input: {
    flex: 1,
    padding: "12px 16px",
    borderRadius: "24px",
    border: "1px solid #d1d5db",
    fontSize: "14px",
    outline: "none",
  },
  sendButton: {
    backgroundColor: "#2563eb",
    color: "#fff",
    border: "none",
    borderRadius: "50%",
    width: "44px",
    height: "44px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
  },
  sendButtonDisabled: {
    backgroundColor: "#93c5fd",
    color: "#fff",
    border: "none",
    borderRadius: "50%",
    width: "44px",
    height: "44px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "not-allowed",
  },
};