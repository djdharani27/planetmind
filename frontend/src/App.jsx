import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import UploadPage from "./pages/UploadPage";
import DashboardPage from "./pages/DashboardPage";
import SearchPage from "./pages/SearchPage";
import ChatPage from "./pages/ChatPage";
import DocViewer from "./pages/DocViewer";

const nav = [
  { to: "/", label: "Dashboard" },
  { to: "/upload", label: "Upload" },
  { to: "/search", label: "Search" },
  { to: "/chat", label: "Chat" },
];

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-white">
        <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center gap-6">
          <span className="text-blue-400 font-bold text-lg mr-4">PlanetMind AI</span>
          {nav.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `text-sm transition-colors ${isActive ? "text-white" : "text-gray-400 hover:text-gray-200"}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/documents/:id" element={<DocViewer />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
