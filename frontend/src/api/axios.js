// Creates a single configured axios instance that every
//  React component uses to talk to the backend. Sets the base URL once so you never repeat it.
//  Automatically attaches the JWT token to every request so protected routes work.

import axios from "axios";

const api = axios.create({
  baseURL: "https://clinic-chatbot-backend-eysi.onrender.com",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.clear();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;