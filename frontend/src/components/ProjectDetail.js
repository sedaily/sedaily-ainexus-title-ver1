import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { ArrowLeftIcon } from "@heroicons/react/24/outline";
import { projectAPI, handleAPIError } from "../services/api";
import LoadingSpinner from "./LoadingSpinner";
import AdminView from "./AdminView";
import UserView from "./UserView";
import { useApp } from "../contexts/AppContext";
import { ChatInterfaceSkeleton } from "./skeleton/SkeletonComponents";
import DarkModeToggle from "./DarkModeToggle";

const ProjectDetail = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { mode, setMode } = useApp();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProjectData();
  }, [projectId, navigate]);

  const loadProjectData = async () => {
    try {
      setLoading(true);
      const projectData = await projectAPI.getProject(projectId);
      setProject(projectData);
    } catch (error) {
      console.error("프로젝트 로드 실패:", error);
      const errorInfo = handleAPIError(error);
      toast.error(errorInfo.message);
      navigate("/projects");
    } finally {
      setLoading(false);
    }
  };

  const handleBackNavigation = () => {
    navigate("/projects");
  };

  if (loading) {
    return <ChatInterfaceSkeleton />;
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center transition-colors duration-200">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            프로젝트를 찾을 수 없습니다
          </h2>
          <button
            onClick={() => navigate("/projects")}
            className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900 hover:bg-blue-200 dark:hover:bg-blue-800 focus:outline-none transition-colors duration-200"
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            프로젝트 목록으로
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-dark-primary transition-all duration-500">
      {/* 상단 네비게이션 바 */}
      <div className="flex-shrink-0 bg-gray-50 dark:bg-dark-secondary px-6 py-4 transition-all duration-300 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <button
              onClick={handleBackNavigation}
              className="btn-neo group relative overflow-hidden bg-white dark:bg-dark-tertiary"
            >
              <ArrowLeftIcon className="h-4 w-4 mr-2 group-hover:-translate-x-1 transition-transform duration-300 text-gray-700 dark:text-white" />
              <span className="group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors duration-300 text-gray-700 dark:text-white">
                목록으로
              </span>
            </button>

            <div className="flex items-center space-x-4">
              <div className="w-2 h-8 bg-blue-500 rounded-full" />
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                {project.name}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* 다크모드 토글 */}
            <DarkModeToggle size="md" />

            {/* 모드 전환 버튼 */}
            <div className="card-neo p-1 rounded-xl">
              <div className="flex items-center">
                <button
                  onClick={() => setMode("user")}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-300 ${
                    mode === "user"
                      ? "btn-neo bg-blue-500 text-white shadow-lg"
                      : "text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-dark-tertiary"
                  }`}
                >
                  👥 사용자
                </button>
                <button
                  onClick={() => setMode("admin")}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-300 ${
                    mode === "admin"
                      ? "btn-neo bg-emerald-500 text-white shadow-lg"
                      : "text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-dark-tertiary"
                  }`}
                >
                  ⚙️ 관리자
                </button>
              </div>
            </div>

            {/* 상태 인디케이터 */}
            <div className="card-neo px-4 py-2 rounded-xl">
              <div className="flex items-center gap-2">
                <div className="relative">
                  <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                  <div className="absolute inset-0 w-2 h-2 bg-emerald-500 rounded-full animate-ping opacity-30" />
                </div>
                <span className="text-xs text-emerald-500 font-medium">
                  준비완료
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 메인 콘텐츠 */}
      <div className="flex-1 overflow-hidden">
        {mode === "admin" ? (
          // 관리자 모드: 프롬프트 카드 관리 + 채팅
          <AdminView projectId={projectId} projectName={project.name} />
        ) : (
          // 사용자 모드: 채팅만
          <UserView projectId={projectId} projectName={project.name} />
        )}
      </div>
    </div>
  );
};

export default ProjectDetail;
