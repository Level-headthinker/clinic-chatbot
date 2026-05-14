import { createContext, useContext, useEffect, useState } from "react";
import api from "../api/axios";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadUser = async () => {
      const token = localStorage.getItem("token");
      const savedUser = localStorage.getItem("user");

      if (!token || !savedUser) {
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

      try {
        const response = await api.get("/auth/me");
        const refreshedUser = {
          email: response.data.email,
          tenant_id: response.data.tenant_id,
          tenant_slug: response.data.tenant_slug,
          user_name: response.data.full_name,
          is_superadmin: response.data.is_superadmin,
        };
        localStorage.setItem("user", JSON.stringify(refreshedUser));
        setUser(refreshedUser);
      } catch {
        localStorage.clear();
        setUser(null);
      } finally {
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
      access_token,
      tenant_id,
      tenant_slug,
      user_name,
      user_email,
      is_superadmin,
    } = response.data;

    const loggedInUser = {
      email: user_email || email,
      tenant_id,
      tenant_slug,
      user_name,
      is_superadmin,
    };

    localStorage.setItem("token", access_token);
    localStorage.setItem("user", JSON.stringify(loggedInUser));
    setUser(loggedInUser);
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
