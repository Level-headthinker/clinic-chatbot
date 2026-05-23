import { createContext, useContext, useEffect, useState } from "react";
import api from "../api/axios";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    const loadUser = async () => {
      const savedUser = localStorage.getItem("user");

      if (!savedUser) {
        setLoading(false);
        return;
      }

      let parsedUser;
      try {
        parsedUser = JSON.parse(savedUser);
      } catch {
        localStorage.clear();
        setUser(null);
        setLoading(false);
        return;
      }
      setUser(parsedUser);

      // Show "waking up" message if server takes more than 5 seconds
      const wakingTimer = setTimeout(() => setWaking(true), 5000);

      try {
        const response = await api.get("/auth/me");
        const refreshedUser = {
          email: response.data.email,
          tenant_id: response.data.tenant_id,
          tenant_slug: response.data.tenant_slug,
          branch_slug: response.data.branch_slug,
          user_name: response.data.full_name,
          is_superadmin: response.data.is_superadmin,
          role: response.data.role,
          doctor_id: response.data.doctor_id || null,
        };
        localStorage.setItem("user", JSON.stringify(refreshedUser));
        setUser(refreshedUser);
      } catch (err) {
        if (err.response) {
          // Server replied with an error (e.g. 401 invalid token) → log out
          localStorage.clear();
          setUser(null);
        }
        // No response = network error / Render cold start timeout → keep cached user
      } finally {
        clearTimeout(wakingTimer);
        setWaking(false);
        setLoading(false);
      }
    };

    loadUser();
  }, []);

  const login = async (email, password) => {
    const formData = new FormData();
    formData.append("username", email);
    formData.append("password", password);

    const response = await api.post("/auth/login", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    const {
      tenant_id,
      tenant_slug,
      branch_slug,
      user_name,
      user_email,
      is_superadmin,
    } = response.data;

    const loggedInUser = {
      email: user_email || email,
      tenant_id,
      tenant_slug,
      branch_slug,
      user_name,
      is_superadmin,
      role: response.data.role || "admin",
      doctor_id: response.data.doctor_id || null,
    };

    localStorage.setItem("access_token", response.data.access_token);
    localStorage.setItem("user", JSON.stringify(loggedInUser));
    setUser(loggedInUser);
    return response.data;
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      localStorage.clear();
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, waking }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
