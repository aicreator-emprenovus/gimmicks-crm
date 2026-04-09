import { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

const AuthContext = createContext(null);
const API_URL = process.env.REACT_APP_BACKEND_URL;

// Do NOT set withCredentials globally - it forces CORS credential checks
// that break in Firefox/Edge when proxy returns Access-Control-Allow-Origin: *
// Bearer token from localStorage is the primary auth mechanism

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(() => {
    try { return localStorage.getItem("auth_token") || null; } catch { return null; }
  });

  // Sync token to axios headers and localStorage whenever it changes
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      try { localStorage.setItem("auth_token", token); } catch {}
    } else {
      delete axios.defaults.headers.common["Authorization"];
      try { localStorage.removeItem("auth_token"); } catch {}
    }
  }, [token]);

  useEffect(() => {
    const checkAuth = async () => {
      const stored = localStorage.getItem("auth_token");
      if (stored) {
        axios.defaults.headers.common["Authorization"] = `Bearer ${stored}`;
        try {
          const response = await axios.get(`${API_URL}/api/auth/me`);
          setUser(response.data);
          setToken(stored);
        } catch {
          setUser(null);
          setToken(null);
        }
      }
      setLoading(false);
    };
    checkAuth();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const login = async (email, password) => {
    const response = await axios.post(`${API_URL}/api/auth/login`, { email, password });
    const accessToken = response.data.access_token;
    setToken(accessToken);
    setUser(response.data.user);
    return response.data.user;
  };

  const register = async (email, password, name) => {
    const response = await axios.post(`${API_URL}/api/auth/register`, { email, password, name });
    const accessToken = response.data.access_token;
    if (accessToken) setToken(accessToken);
    setUser(response.data.user);
    return response.data.user;
  };

  const logout = async () => {
    try {
      await axios.post(`${API_URL}/api/auth/logout`);
    } catch { /* ignore */ }
    setUser(null);
    setToken(null);
  };

  const getAuthHeaders = () => ({});

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, getAuthHeaders }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
