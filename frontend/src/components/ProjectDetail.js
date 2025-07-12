import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import {
  ArrowLeftIcon,
  DocumentTextIcon,
  SparklesIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from "@heroicons/react/24/outline";
import {
  projectAPI,
  generateAPI,
  handleAPIError,
  promptCardAPI,
} from "../services/api";
import PromptCardManager from "./PromptCardManager";
import ArticleInput from "./ArticleInput";
import ResultDisplay from "./ResultDisplay";

const ProjectDetail = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("prompt-cards");
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
      const response = await promptCardAPI.getPromptCards(
        projectId,
        false,
        true
      );
      setPromptCards(response.promptCards || []);
    } catch (error) {
      console.error("프롬프트 카드 로딩 실패:", error);
      setPromptCards([]);
    }
  }, [projectId]);

  useEffect(() => {
    loadProject();
    loadPromptCards();
  }, [loadProject, loadPromptCards]);

  const canGenerate = () => {
    // 최소 1개 이상의 활성화된 프롬프트 카드가 있으면 생성 가능
    return promptCards.some((card) => card.enabled !== false);
  };

  const handleGenerateTitle = async (article, aiSettings) => {
    try {
      setIsGenerating(true);
      setExecutionProgress(null);
      setGenerationResult(null);

      const result = await generateAPI.generateTitle(
        projectId,
        article,
        (progress) => {
          setExecutionProgress(progress);
        },
        aiSettings
      );

      setGenerationResult(result);
      toast.success("제목 생성이 완료되었습니다!");
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`제목 생성 실패: ${errorInfo.message}`);
      setExecutionProgress({ status: "failed", message: errorInfo.message });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCardReorder = useCallback(async (fromIndex, toIndex) => {
    const sortedCards = [...promptCards].sort((a, b) => (a.stepOrder || 0) - (b.stepOrder || 0));
    const newCards = [...sortedCards];
    const [movedCard] = newCards.splice(fromIndex, 1);
    newCards.splice(toIndex, 0, movedCard);

    // stepOrder 업데이트
    const updatedCards = newCards.map((card, index) => ({
      ...card,
      stepOrder: index + 1
    }));

    setPromptCards(updatedCards);

    try {
      // API 호출로 순서 업데이트
      await Promise.all(
        updatedCards.map(card => 
          promptCardAPI.updatePromptCard(projectId, card.promptId, {
            ...card,
            stepOrder: card.stepOrder
          })
        )
      );
      toast.success("카드 순서가 변경되었습니다!");
    } catch (error) {
      console.error("카드 순서 변경 실패:", error);
      toast.error("카드 순서 변경에 실패했습니다.");
      // 실패시 원래 순서로 복원
      loadPromptCards();
    }
  }, [promptCards, projectId, loadPromptCards]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">프로젝트 로딩 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={() => navigate(-1)}
            className="text-blue-600 hover:underline"
          >
            돌아가기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <div className="bg-white shadow-sm border-b border-gray-200 mb-8 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <button
                onClick={() => navigate(-1)}
                className="flex items-center text-gray-600 hover:text-gray-900 transition-all duration-200 hover:bg-gray-100 px-3 py-2 rounded-lg group"
              >
                <ArrowLeftIcon className="h-5 w-5 mr-2 group-hover:-translate-x-1 transition-transform duration-200" />
                <span className="font-medium">프로젝트 목록</span>
              </button>

              <div className="flex items-center space-x-4">
                <div className="w-1 h-12 bg-blue-500 rounded-full"></div>
                <div>
                  <h1 className="text-3xl font-bold text-gray-900">
                    {project?.name}
                  </h1>
                  <p className="text-gray-600 mt-1 text-lg">
                    {project?.description || "AI 기반 제목 생성 프로젝트"}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* 프로젝트 상태 정보 */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white border border-blue-200 rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <DocumentTextIcon className="h-6 w-6 text-blue-600" />
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold text-blue-600">
                    {promptCards.length}
                  </p>
                  <p className="text-sm text-blue-500 font-medium">
                    프롬프트 카드
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">활성 카드</span>
                <span className="text-sm font-semibold text-blue-600">
                  {promptCards.filter((card) => card.enabled !== false).length}개
                </span>
              </div>
            </div>

            <div className="bg-white border border-green-200 rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-green-100 rounded-lg">
                  <CheckCircleIcon className="h-6 w-6 text-green-600" />
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold text-green-600">
                    {canGenerate() ? "준비" : "대기"}
                  </p>
                  <p className="text-sm text-green-500 font-medium">
                    생성 상태
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">
                  {canGenerate() ? "제목 생성 가능" : "프롬프트 카드 필요"}
                </span>
                <div className={`w-3 h-3 rounded-full ${canGenerate() ? 'bg-green-400' : 'bg-yellow-400'}`}></div>
              </div>
            </div>

            <div className="bg-white border border-purple-200 rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-purple-100 rounded-lg">
                  <SparklesIcon className="h-6 w-6 text-purple-600" />
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-purple-600">
                    Claude 3.5
                  </p>
                  <p className="text-sm text-purple-500 font-medium">
                    AI 모델
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">최고 성능 모델</span>
                <div className="flex space-x-1">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="w-1.5 h-1.5 bg-purple-400 rounded-full"></div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 탭 네비게이션 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-2 shadow-sm border border-gray-200/50">
            <nav className="flex space-x-2">
              <button
                onClick={() => setActiveTab("prompt-cards")}
                className={`flex items-center px-6 py-3 rounded-xl font-medium text-sm transition-all duration-200 ${
                  activeTab === "prompt-cards"
                    ? "bg-blue-600 text-white shadow-md shadow-blue-600/25"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-100/70"
                }`}
              >
                <DocumentTextIcon className="h-5 w-5 mr-2" />
                <span>프롬프트 카드</span>
                <span className={`ml-3 px-2 py-1 text-xs rounded-full font-semibold ${
                  activeTab === "prompt-cards" 
                    ? "bg-white/20 text-white" 
                    : "bg-blue-100 text-blue-600"
                }`}>
                  {promptCards.length}
                </span>
              </button>

              <button
                onClick={() => setActiveTab("generate")}
                className={`flex items-center px-6 py-3 rounded-xl font-medium text-sm transition-all duration-200 ${
                  activeTab === "generate"
                    ? "bg-blue-600 text-white shadow-md shadow-blue-600/25"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-100/70"
                }`}
              >
                <SparklesIcon className="h-5 w-5 mr-2" />
                <span>제목 생성</span>
                {!canGenerate() && (
                  <span className={`ml-3 px-2 py-1 text-xs rounded-full font-semibold ${
                    activeTab === "generate" 
                      ? "bg-white/20 text-white" 
                      : "bg-yellow-100 text-yellow-600"
                  }`}>
                    대기
                  </span>
                )}
              </button>
            </nav>
          </div>
        </div>

        {/* 탭 설명 */}
        <div className="mb-8">
          {activeTab === "prompt-cards" && (
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/50 rounded-2xl p-6 backdrop-blur-sm">
              <div className="flex items-start space-x-4">
                <div className="p-3 bg-blue-100 rounded-xl">
                  <InformationCircleIcon className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-blue-900 mb-2">
                    프롬프트 카드 관리
                  </h3>
                  <p className="text-blue-800 leading-relaxed">
                    AI가 제목을 생성할 때 사용할 지침과 규칙을 카드 형태로 관리합니다. 
                    카드의 순서를 드래그앤드롭으로 조정하고 활성/비활성을 설정할 수 있습니다.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "generate" && (
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200/50 rounded-2xl p-6 backdrop-blur-sm">
              <div className="flex items-start space-x-4">
                <div className="p-3 bg-green-100 rounded-xl">
                  <InformationCircleIcon className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-green-900 mb-2">
                    AI 제목 생성
                  </h3>
                  <p className="text-green-800 leading-relaxed">
                    기사 내용을 입력하면 설정된 프롬프트 카드를 바탕으로 AI가 최적의 제목을 생성합니다. 
                    실시간으로 생성 과정을 확인하고 다양한 제목 옵션을 받아볼 수 있습니다.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 탭 콘텐츠 */}
        <div className="min-h-screen">
          {activeTab === "prompt-cards" && (
            <PromptCardManager
              projectId={projectId}
              onCardsChanged={loadPromptCards}
            />
          )}

          {activeTab === "generate" && (
            <div className="flex gap-8">
              {/* 메인 콘텐츠 */}
              <div className="flex-1 space-y-8">
                <ArticleInput
                  canGenerate={canGenerate()}
                  isGenerating={isGenerating}
                  onGenerate={handleGenerateTitle}
                  executionProgress={executionProgress}
                />

                {/* 생성 결과를 동일 탭에서 표시 */}
                {generationResult && (
                  <ResultDisplay
                    result={generationResult}
                    projectName={project?.name}
                  />
                )}
              </div>

              {/* 프롬프트 카드 사이드바 */}
              <div className="w-80 flex-shrink-0">
                <div className="bg-white/70 backdrop-blur-sm rounded-2xl border border-gray-200/50 p-6 sticky top-8">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                      <DocumentTextIcon className="h-5 w-5 mr-2 text-blue-600" />
                      프롬프트 카드
                    </h3>
                    <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                      {promptCards.length}개
                    </span>
                  </div>
                  
                  {promptCards.length > 1 && (
                    <div className="mb-3 p-2 bg-blue-50 rounded-lg border border-blue-200">
                      <p className="text-xs text-blue-700 text-center">
                        💡 카드를 드래그하여 순서를 변경할 수 있습니다
                      </p>
                    </div>
                  )}

                  {promptCards.length === 0 ? (
                    <div className="text-center py-8">
                      <DocumentTextIcon className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                      <p className="text-gray-500 text-sm">
                        프롬프트 카드가 없습니다
                      </p>
                      <button
                        onClick={() => setActiveTab("prompt-cards")}
                        className="mt-3 text-blue-600 hover:text-blue-700 text-sm font-medium"
                      >
                        카드 생성하기
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {promptCards
                        .sort((a, b) => (a.stepOrder || 0) - (b.stepOrder || 0))
                        .map((card, index) => (
                          <PromptCardMini
                            key={card.promptId}
                            card={card}
                            index={index}
                            total={promptCards.length}
                            onReorder={handleCardReorder}
                          />
                        ))}
                    </div>
                  )}

                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <button
                      onClick={() => setActiveTab("prompt-cards")}
                      className="w-full text-center py-2 px-4 text-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors font-medium"
                    >
                      카드 관리하기
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "result" && generationResult && (
            <ResultDisplay
              result={generationResult}
              projectName={project?.name}
              onBackToGenerate={() => setActiveTab("generate")}
            />
          )}
        </div>
      </div>
    </div>
  );
};

// 프롬프트 카드 미니 컴포넌트
const PromptCardMini = ({ card, index, total, onReorder }) => {
  const [isDragging, setIsDragging] = useState(false);

  const getCategoryIcon = (category) => {
    switch (category) {
      case "instruction":
        return "📋";
      case "knowledge":
        return "📚";
      case "summary":
        return "📝";
      case "style_guide":
        return "🎨";
      case "validation":
        return "✅";
      case "enhancement":
        return "✨";
      default:
        return "📄";
    }
  };

  const getCategoryColor = (category) => {
    switch (category) {
      case "instruction":
        return "blue";
      case "knowledge":
        return "green";
      case "summary":
        return "purple";
      case "style_guide":
        return "pink";
      case "validation":
        return "orange";
      case "enhancement":
        return "indigo";
      default:
        return "gray";
    }
  };

  const categoryColor = getCategoryColor(card.category);

  const handleDragStart = (e) => {
    setIsDragging(true);
    e.dataTransfer.setData("text/plain", index.toString());
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const draggedIndex = parseInt(e.dataTransfer.getData("text/plain"));
    if (draggedIndex !== index && onReorder) {
      onReorder(draggedIndex, index);
    }
  };

  const handleDragEnd = () => {
    setIsDragging(false);
  };

  return (
    <div 
      draggable
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onDragEnd={handleDragEnd}
      className={`p-3 rounded-lg border transition-all duration-200 cursor-move ${
        isDragging ? "opacity-50 scale-95" : ""
      } ${
        card.enabled !== false
          ? `bg-${categoryColor}-50 border-${categoryColor}-200 hover:bg-${categoryColor}-100`
          : "bg-gray-50 border-gray-200 opacity-60"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-2 flex-1">
          <span className="text-lg flex-shrink-0">
            {getCategoryIcon(card.category)}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-xs font-medium text-gray-500 bg-white px-2 py-0.5 rounded-full">
                {card.stepOrder || index + 1}
              </span>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                card.enabled !== false
                  ? `bg-${categoryColor}-100 text-${categoryColor}-700`
                  : "bg-gray-100 text-gray-500"
              }`}>
                {card.category?.replace('_', ' ').toUpperCase()}
              </span>
            </div>
            <h4 className={`text-sm font-medium truncate ${
              card.enabled !== false ? "text-gray-900" : "text-gray-500"
            }`}>
              {card.title || `${card.category} 카드`}
            </h4>
            {card.description && (
              <p className="text-xs text-gray-600 truncate mt-1">
                {card.description}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {card.enabled !== false ? (
            <CheckCircleIcon className="h-4 w-4 text-green-500 flex-shrink-0" />
          ) : (
            <div className="w-4 h-4 rounded-full bg-gray-300 flex-shrink-0"></div>
          )}
          <div className="text-gray-400">
            <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 3a1 1 0 01.707.293l3 3a1 1 0 01-1.414 1.414L10 5.414 7.707 7.707a1 1 0 01-1.414-1.414l3-3A1 1 0 0110 3zM10 17a1 1 0 01-.707-.293l-3-3a1 1 0 011.414-1.414L10 14.586l2.293-2.293a1 1 0 011.414 1.414l-3 3A1 1 0 0110 17z" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProjectDetail;
