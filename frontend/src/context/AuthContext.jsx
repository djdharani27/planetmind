import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { apiFetch } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("planetmind_token");
    const storedUser = localStorage.getItem("planetmind_user");
    if (token && storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        localStorage.removeItem("planetmind_token");
        localStorage.removeItem("planetmind_user");
      }
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (username, password) => {
    const data = await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    localStorage.setItem("planetmind_token", data.access_token);
    const userData = { username: data.username, role: data.role };
    localStorage.setItem("planetmind_user", JSON.stringify(userData));
    setUser(userData);
    return data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("planetmind_token");
    localStorage.removeItem("planetmind_user");
    setUser(null);
  }, []);

  const getToken = useCallback(() => {
    return localStorage.getItem("planetmind_token");
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout, getToken, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
