import { BrowserRouter, Routes, Route, NavLink, Navigate } from "react-router-dom";
import { useState } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import LoginPage from "./pages/LoginPage";
import UploadPage from "./pages/UploadPage";
import DashboardPage from "./pages/DashboardPage";
import SearchPage from "./pages/SearchPage";
import ChatPage from "./pages/ChatPage";
import DocViewer from "./pages/DocViewer";
import MaintenancePage from "./pages/MaintenancePage";
import CompliancePage from "./pages/CompliancePage";
import LessonsPage from "./pages/LessonsPage";
import GraphPage from "./pages/GraphPage";

const nav = [
  { to: "/", label: "Dashboard" },
  { to: "/upload", label: "Upload" },
  { to: "/search", label: "Search" },
  { to: "/chat", label: "Chat" },
  { to: "/graph", label: "Graph" },
  { to: "/maintenance", label: "Maintenance" },
  { to: "/compliance", label: "Compliance" },
  { to: "/lessons", label: "Lessons" },
];

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppRoutes() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <nav className="bg-gray-900 border-b border-gray-800 px-4 md:px-6 py-3">
        <div className="flex items-center justify-between">
          <span className="text-blue-400 font-bold text-lg">PlanetMind AI</span>
          <div className="flex items-center gap-4">
            {user && (
              <span className="text-gray-400 text-sm hidden md:inline">
                {user.username}
              </span>
            )}
            <button
              className="md:hidden text-gray-400 hover:text-white text-sm"
              onClick={() => setMenuOpen(!menuOpen)}
            >
              {menuOpen ? "✕" : "☰"} Menu
            </button>
          </div>
        </div>
        <div className={`flex flex-col md:flex-row md:items-center gap-1 md:gap-4 mt-2 md:mt-0 ${menuOpen ? "block" : "hidden md:flex"}`}>
          {nav.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `text-sm transition-colors py-1 md:py-0 ${isActive ? "text-white font-medium" : "text-gray-400 hover:text-gray-200"}`
              }
            >
              {label}
            </NavLink>
          ))}
          {user && (
            <button
              onClick={logout}
              className="text-sm text-gray-500 hover:text-red-400 transition-colors py-1 md:py-0 ml-auto"
            >
              Logout
            </button>
          )}
        </div>
      </nav>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
        <Route path="/search" element={<ProtectedRoute><SearchPage /></ProtectedRoute>} />
        <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
        <Route path="/maintenance" element={<ProtectedRoute><MaintenancePage /></ProtectedRoute>} />
        <Route path="/compliance" element={<ProtectedRoute><CompliancePage /></ProtectedRoute>} />
        <Route path="/lessons" element={<ProtectedRoute><LessonsPage /></ProtectedRoute>} />
        <Route path="/graph" element={<ProtectedRoute><GraphPage /></ProtectedRoute>} />
        <Route path="/documents/:id" element={<ProtectedRoute><DocViewer /></ProtectedRoute>} />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
