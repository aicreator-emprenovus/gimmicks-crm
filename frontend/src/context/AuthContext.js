import { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

const AuthContext = createContext(null);
const API_URL = process.env.REACT_APP_BACKEND_URL;

// Configure axios to always send cookies
axios.defaults.withCredentials = true;

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/auth/me`);
        setUser(response.data);
      } catch {
        setUser(null);
      }
      setLoading(false);
    };
    checkAuth();
  }, []);

  const login = async (email, password) => {
    const response = await axios.post(`${API_URL}/api/auth/login`, { email, password });
    setUser(response.data.user);
    return response.data.user;
  };

  const register = async (email, password, name) => {
    const response = await axios.post(`${API_URL}/api/auth/register`, { email, password, name });
    setUser(response.data.user);
    return response.data.user;
  };

  const logout = async () => {
    try {
      await axios.post(`${API_URL}/api/auth/logout`);
    } catch { /* ignore */ }
    setUser(null);
  };

  // Auth headers no longer needed - httpOnly cookies handle auth via withCredentials
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
