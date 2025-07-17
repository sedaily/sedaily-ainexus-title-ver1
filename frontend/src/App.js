import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  useLocation,
} from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "./contexts/AuthContext";
import { AppProvider } from "./contexts/AppContext";
import Header from "./components/Header";
import ProjectList from "./components/ProjectList";
import ProjectDetail from "./components/ProjectDetail";
import CreateProject from "./components/CreateProject";
import ModeSelection from "./components/ModeSelection";
import "./App.css";

function AppContent() {
  const location = useLocation();
  // Header를 숨길 경로들: 모드 선택 페이지와 프로젝트 상세 페이지
  const isHeaderHidden =
    location.pathname === "/" || location.pathname.startsWith("/projects/");

  return (
    <div className="min-h-screen bg-gray-50">
      {!isHeaderHidden && <Header />}
      <main
        className={
          isHeaderHidden ? "" : "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
        }
      >
        <Routes>
          <Route path="/" element={<ModeSelection />} />
          <Route path="/projects" element={<ProjectList />} />
          <Route path="/create" element={<CreateProject />} />
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppProvider>
        <Router>
          <AppContent />
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: "#363636",
                color: "#fff",
              },
              success: {
                duration: 3000,
                theme: {
                  primary: "green",
                  secondary: "black",
                },
              },
            }}
          />
        </Router>
      </AppProvider>
    </AuthProvider>
  );
}

export default App;
