import React, { Suspense } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  useLocation,
} from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "./contexts/AuthContext";
import { AppProvider } from "./contexts/AppContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import Header from "./components/Header";
import "./App.css";

// 코드 스플리팅 - 필요할 때만 로드
const ModeSelection = React.lazy(() => import("./components/ModeSelection"));
const ProjectList = React.lazy(() => import("./components/ProjectList"));
const ProjectDetail = React.lazy(() => import("./components/ProjectDetail"));
const CreateProject = React.lazy(() => import("./components/CreateProject"));

// 빠른 로딩을 위한 미니멀 스켈레톤 컴포넌트
const PageSkeleton = () => (
  <div className="min-h-screen bg-gray-50 dark:bg-dark-primary animate-pulse">
    <div className="bg-white dark:bg-dark-secondary">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="h-6 bg-gray-200 dark:bg-dark-tertiary rounded w-32"></div>
      </div>
    </div>
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="space-y-4">
        <div className="h-4 bg-gray-200 dark:bg-dark-tertiary rounded w-3/4"></div>
        <div className="h-4 bg-gray-200 dark:bg-dark-tertiary rounded w-1/2"></div>
        <div className="h-4 bg-gray-200 dark:bg-dark-tertiary rounded w-5/6"></div>
      </div>
    </div>
  </div>
);

function AppContent() {
  const location = useLocation();
  // Header를 숨길 경로들: 모드 선택 페이지와 프로젝트 상세 페이지
  const isHeaderHidden =
    location.pathname === "/" || location.pathname.startsWith("/projects/");

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-dark-primary transition-colors duration-300">
      {!isHeaderHidden && <Header />}
      <main
        className={
          isHeaderHidden
            ? ""
            : "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 bg-gray-50 dark:bg-dark-primary"
        }
      >
        <Suspense fallback={<PageSkeleton />}>
          <Routes>
            <Route path="/" element={<ModeSelection />} />
            <Route path="/projects" element={<ProjectList />} />
            <Route path="/create" element={<CreateProject />} />
            <Route path="/projects/:projectId" element={<ProjectDetail />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppProvider>
          <Router>
            <AppContent />
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                className: "dark:bg-gray-800 dark:text-white",
                style: {
                  background: "var(--toaster-bg, #ffffff)",
                  color: "var(--toaster-color, #374151)",
                  border: "1px solid var(--toaster-border, #e5e7eb)",
                },
                success: {
                  className: "dark:bg-gray-800 dark:text-green-400",
                  style: {
                    background: "var(--toaster-success-bg, #f0fdf4)",
                    color: "var(--toaster-success-color, #15803d)",
                    border: "1px solid var(--toaster-success-border, #bbf7d0)",
                  },
                },
                error: {
                  className: "dark:bg-gray-800 dark:text-red-400",
                  style: {
                    background: "var(--toaster-error-bg, #fef2f2)",
                    color: "var(--toaster-error-color, #dc2626)",
                    border: "1px solid var(--toaster-error-border, #fecaca)",
                  },
                },
              }}
            />
          </Router>
        </AppProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
