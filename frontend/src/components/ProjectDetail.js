import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { ArrowLeftIcon } from "@heroicons/react/24/outline";
import { projectAPI, handleAPIError } from "../services/api";
import LoadingSpinner from "./LoadingSpinner";
import AdminView from "./AdminView";
import UserView from "./UserView";
import { useApp } from "../contexts/AppContext";

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
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner />
        <div className="ml-4 text-gray-600">
          {mode === "admin"
            ? "관리자 화면을 준비하고 있습니다..."
            : "채팅 화면을 준비하고 있습니다..."}
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            프로젝트를 찾을 수 없습니다
          </h2>
          <button
            onClick={() => navigate("/projects")}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            프로젝트 목록으로
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 상단 네비게이션 바 */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBackNavigation}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <ArrowLeftIcon className="h-4 w-4 mr-2" />
              목록으로
            </button>
            <div className="flex items-center">
              <h1 className="text-lg font-semibold text-gray-900">
                {project.name}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1 bg-green-50 border border-green-100 rounded-full">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-xs text-green-700">준비완료</span>
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
