// Manages login state for the entire app. Stores who is logged in,
// their token, and their clinic info. Any component can check if user is logged
// in or get user info without passing props everywhere.

import { createContext, useContext, useState, useEffect } from "react";
import api from "../api/axios";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    const savedUser = localStorage.getItem("user");
    if (token && savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    const formData = new FormData();
    formData.append("username", email);
    formData.append("password", password);

    const response = await api.post("/auth/login", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    const { access_token, tenant_id, tenant_slug, user_name } = response.data;

localStorage.setItem("token", access_token);
localStorage.setItem(
  "user",
  JSON.stringify({ email, tenant_id, tenant_slug, user_name })
);
setUser({ email, tenant_id, tenant_slug, user_name });
    return response.data;
  };

  const logout = () => {
    localStorage.clear();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);