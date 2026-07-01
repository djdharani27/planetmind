import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { useState } from "react";
import UploadPage from "./pages/UploadPage";
import DashboardPage from "./pages/DashboardPage";
import SearchPage from "./pages/SearchPage";
import ChatPage from "./pages/ChatPage";
import DocViewer from "./pages/DocViewer";
import MaintenancePage from "./pages/MaintenancePage";
import CompliancePage from "./pages/CompliancePage";
import LessonsPage from "./pages/LessonsPage";
import GraphPage from "./pages/GraphPage";
import AdminPage from "./pages/AdminPage";

const nav = [
  { to: "/", label: "Dashboard" },
  { to: "/upload", label: "Upload" },
  { to: "/search", label: "Search" },
  { to: "/chat", label: "Chat" },
  { to: "/graph", label: "Graph" },
  { to: "/maintenance", label: "Maintenance" },
  { to: "/compliance", label: "Compliance" },
  { to: "/lessons", label: "Lessons" },
  { to: "/admin", label: "Admin" },
];

function AppRoutes() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <nav className="bg-gray-900 border-b border-gray-800 px-4 md:px-6 py-3">
        <div className="flex items-center justify-between">
          <span className="text-blue-400 font-bold text-lg">PlanetMind AI</span>
          <button
            className="md:hidden text-gray-400 hover:text-white text-sm"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? "✕" : "☰"} Menu
          </button>
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
        </div>
      </nav>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/maintenance" element={<MaintenancePage />} />
        <Route path="/compliance" element={<CompliancePage />} />
        <Route path="/lessons" element={<LessonsPage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/documents/:id" element={<DocViewer />} />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
