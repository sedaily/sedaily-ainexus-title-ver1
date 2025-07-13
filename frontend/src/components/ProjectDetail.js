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
  const [promptCards, setPromptCards] = useState([]);
  const [showProjectMenu, setShowProjectMenu] = useState(false);

  useEffect(() => {
    loadProject();
    loadPromptCards();
  }, [projectId]);

  const loadProject = async () => {
    try {
      setLoading(true);
      const data = await projectAPI.getProject(projectId);
      setProject(data);
    } catch (error) {
      console.error("프로젝트 로드 실패:", error);
      handleAPIError(error, "프로젝트를 불러오는데 실패했습니다.");
      navigate("/");
    } finally {
      setLoading(false);
    }
  };

  const loadPromptCards = async () => {
    try {
      const cards = await promptCardAPI.getPromptCards(projectId);
      setPromptCards(cards);
    } catch (error) {
      console.error("프롬프트 카드 로드 실패:", error);
      handleAPIError(error, "프롬프트 카드를 불러오는데 실패했습니다.");
    }
  };

  const handleDeleteProject = async () => {
    if (
      !window.confirm(
        "정말로 이 프로젝트를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다."
      )
    ) {
      return;
    }

    try {
      await projectAPI.deleteProject(projectId);
      toast.success("프로젝트가 삭제되었습니다.");
      navigate("/");
    } catch (error) {
      console.error("프로젝트 삭제 실패:", error);
      handleAPIError(error, "프로젝트 삭제에 실패했습니다.");
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

      {/* 메인 콘텐츠 - 새로운 PromptCardManager 사용 */}
      <PromptCardManager
        projectId={projectId}
        projectName={project.title}
        promptCards={promptCards}
        onCardsChanged={loadPromptCards}
      />

    </div>
  );
};

export default ProjectDetail;
