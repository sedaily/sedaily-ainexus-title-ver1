import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import {
  ArrowLeftIcon,
  CloudArrowUpIcon,
  DocumentTextIcon,
  SparklesIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  Cog8ToothIcon,
  ChatBubbleLeftRightIcon,
  BeakerIcon,
} from "@heroicons/react/24/outline";
import {
  projectAPI,
  generateAPI,
  uploadAPI,
  handleAPIError,
  PROMPT_CATEGORIES,
  promptCardAPI,
} from "../services/api";
import PromptUpload from "./PromptUpload";
import PromptCardManager from "./PromptCardManager";
import ArticleInput from "./ArticleInput";
import ResultDisplay from "./ResultDisplay";
import ChatInterface from "./ChatInterface";
import BedrockAgentChat from "./BedrockAgentChat";

const ProjectDetail = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("prompt-cards");
  const [promptStatus, setPromptStatus] = useState({});
  const [promptCards, setPromptCards] = useState([]);
  const [generationResult, setGenerationResult] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [executionProgress, setExecutionProgress] = useState(null);

  const loadProject = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const projectData = await projectAPI.getProject(projectId);
      setProject(projectData);

      // 프롬프트 상태 초기화
      const status = {};
      PROMPT_CATEGORIES.forEach((category) => {
        status[category.id] = {
          uploaded: false,
          indexed: false,
          fileName: null,
        };
      });
      setPromptStatus(status);
    } catch (err) {
      const errorInfo = handleAPIError(err);
      setError(errorInfo.message);
      toast.error(errorInfo.message);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const loadPromptCards = useCallback(async () => {
    try {
      const response = await promptCardAPI.getPromptCards(projectId, false, true);
      setPromptCards(response.promptCards || []);
    } catch (error) {
      console.error("프롬프트 카드 로딩 실패:", error);
      // 에러가 발생해도 기존 기능은 유지되도록 함
      setPromptCards([]);
    }
  }, [projectId]);

  useEffect(() => {
    loadProject();
    loadPromptCards();
  }, [loadProject, loadPromptCards]);

  const handlePromptUpload = async (categoryId, file) => {
    try {
      // 업로드 URL 요청
      const uploadData = await projectAPI.getUploadUrl(
        projectId,
        categoryId,
        file.name
      );

      // S3에 파일 업로드
      await uploadAPI.uploadFile(uploadData.uploadUrl, file);

      // 상태 업데이트
      setPromptStatus((prev) => ({
        ...prev,
        [categoryId]: {
          uploaded: true,
          indexed: false, // 색인은 Lambda에서 자동으로 처리
          fileName: file.name,
        },
      }));

      toast.success(`${file.name} 업로드 완료! 색인 중...`);

      // 색인 완료 확인 (간단한 폴링)
      setTimeout(() => {
        setPromptStatus((prev) => ({
          ...prev,
          [categoryId]: {
            ...prev[categoryId],
            indexed: true,
          },
        }));
        toast.success(`${file.name} 색인 완료!`);
      }, 3000);
    } catch (err) {
      const errorInfo = handleAPIError(err);
      toast.error(`업로드 실패: ${errorInfo.message}`);
    }
  };

  const handleGenerateTitle = async (article, onProgress) => {
    try {
      setIsGenerating(true);
      setGenerationResult(null);
      setExecutionProgress(null);

      // 진행 상황 콜백 설정
      const progressCallback = (progress) => {
        setExecutionProgress(progress);
        if (onProgress) {
          onProgress(progress);
        }
      };

      // Step Functions 기반 제목 생성
      const result = await generateAPI.generateTitle(
        projectId,
        article,
        progressCallback
      );

      setGenerationResult(result);
      setActiveTab("result");

      toast.success("제목 생성 완료!");
    } catch (err) {
      const errorInfo = handleAPIError(err);
      toast.error(`제목 생성 실패: ${errorInfo.message}`);
      setExecutionProgress({ status: "failed", message: errorInfo.message });
    } finally {
      setIsGenerating(false);
    }
  };

  const canGenerate = () => {
    // 새로운 프롬프트 카드 시스템: 최소 1개의 활성화된 카드가 있으면 생성 가능
    const enabledPromptCards = promptCards.filter(card => card.enabled);
    if (enabledPromptCards.length > 0) {
      return true;
    }

    // 레거시 시스템: 기존 필수 카테고리 체크 (하위 호환성)
    const requiredCategories = PROMPT_CATEGORIES.filter((cat) => cat.required);
    return requiredCategories.every((cat) => promptStatus[cat.id]?.indexed);
  };

  const getGenerationStatusIcon = () => {
    if (!executionProgress) return null;

    switch (executionProgress.status) {
      case "started":
        return <Cog8ToothIcon className="h-5 w-5 text-blue-600 animate-spin" />;
      case "completed":
        return <CheckCircleIcon className="h-5 w-5 text-green-600" />;
      case "failed":
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />;
      default:
        return <SparklesIcon className="h-5 w-5 text-blue-600 animate-pulse" />;
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">⚠️ 오류가 발생했습니다</div>
        <p className="text-gray-600 mb-6">{error}</p>
        <button
          onClick={loadProject}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
        >
          다시 시도
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* 헤더 */}
      <div className="mb-8">
        <button
          onClick={() => navigate("/")}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-5 w-5 mr-2" />
          프로젝트 목록으로
        </button>

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <DocumentTextIcon className="h-8 w-8 text-blue-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {project?.name}
              </h1>
              <p className="text-gray-600 mt-1">
                {project?.description || "프로젝트 설명 없음"}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                canGenerate()
                  ? "bg-green-100 text-green-800"
                  : "bg-yellow-100 text-yellow-800"
              }`}
            >
              {canGenerate() 
                ? `제목 생성 준비됨 (${promptCards.filter(card => card.enabled).length}개 카드 활성)` 
                : "프롬프트 카드 또는 파일 업로드 필요"}
            </span>

            {/* 실행 상태 표시 */}
            {executionProgress && (
              <div className="flex items-center space-x-2">
                {getGenerationStatusIcon()}
                <span className="text-sm font-medium text-gray-700">
                  {executionProgress.status === "started" && "실행 중"}
                  {executionProgress.status === "completed" && "완료"}
                  {executionProgress.status === "failed" && "실패"}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 탭 네비게이션 */}
      <div className="mb-8">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab("setup")}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === "setup"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <CloudArrowUpIcon className="h-5 w-5 inline mr-2" />
            프롬프트 설정 (레거시)
          </button>
          <button
            onClick={() => setActiveTab("prompt-cards")}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === "prompt-cards"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <DocumentTextIcon className="h-5 w-5 inline mr-2" />
            프롬프트 카드
          </button>
          <button
            onClick={() => setActiveTab("generate")}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === "generate"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <SparklesIcon className="h-5 w-5 inline mr-2" />
            제목 생성
          </button>
          <button
            onClick={() => setActiveTab("chat")}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === "chat"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <ChatBubbleLeftRightIcon className="h-5 w-5 inline mr-2" />
            LangChain 채팅
          </button>
          <button
            onClick={() => setActiveTab("agent-chat")}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === "agent-chat"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <BeakerIcon className="h-5 w-5 inline mr-2" />
            Bedrock Agent 채팅
          </button>
          {generationResult && (
            <button
              onClick={() => setActiveTab("result")}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === "result"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              <CheckCircleIcon className="h-5 w-5 inline mr-2" />
              결과 확인
            </button>
          )}
        </nav>
      </div>

      {/* 탭 컨텐츠 */}
      <div className="min-h-screen">
        {activeTab === "setup" && (
          <PromptUpload
            categories={PROMPT_CATEGORIES}
            promptStatus={promptStatus}
            onUpload={handlePromptUpload}
          />
        )}

        {activeTab === "prompt-cards" && (
          <PromptCardManager 
            projectId={projectId} 
            onCardsChanged={loadPromptCards}
          />
        )}

        {activeTab === "generate" && (
          <ArticleInput
            canGenerate={canGenerate()}
            isGenerating={isGenerating}
            onGenerate={handleGenerateTitle}
          />
        )}

        {activeTab === "chat" && (
          <div className="h-[calc(100vh-16rem)]">
            <ChatInterface projectId={projectId} projectName={project?.name} />
          </div>
        )}

        {activeTab === "agent-chat" && (
          <div className="h-[calc(100vh-16rem)]">
            <BedrockAgentChat 
              projectId={projectId} 
              projectName={project?.name} 
              projectInfo={project}
            />
          </div>
        )}

        {activeTab === "result" && generationResult && (
          <ResultDisplay
            result={generationResult}
            projectName={project?.name}
          />
        )}
      </div>
    </div>
  );
};

export default ProjectDetail;
