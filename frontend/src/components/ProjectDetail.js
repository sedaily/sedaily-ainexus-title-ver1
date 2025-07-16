import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import {
  ArrowLeftIcon,
  EllipsisHorizontalIcon,
} from "@heroicons/react/24/outline";
import { projectAPI, promptCardAPI, handleAPIError } from "../services/api";
import LoadingSpinner from "./LoadingSpinner";
import PromptCardManager from "./PromptCardManager";

const ProjectDetail = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProject();
  }, [projectId]);

  const loadProject = async () => {
    try {
      setLoading(true);
      const data = await projectAPI.getProject(projectId);
      setProject(data);
    } catch (error) {
      console.error("프로젝트 로드 실패:", error);
      const errorInfo = handleAPIError(error);
      toast.error(errorInfo.message);
      navigate("/");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            프로젝트를 찾을 수 없습니다
          </h2>
          <button
            onClick={() => navigate("/")}
            className="text-blue-600 hover:text-blue-800"
          >
            홈으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 메인 콘텐츠 - PromptCardManager 사용 (채팅 + 프롬프트 카드 사이드바) */}
      <PromptCardManager
        projectId={projectId}
        projectName={project.name}
      />
    </div>
  );
};

export default ProjectDetail;
