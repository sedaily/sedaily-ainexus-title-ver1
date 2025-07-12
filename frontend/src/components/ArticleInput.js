import React, { useState, memo } from "react";
import {
  SparklesIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  Cog8ToothIcon,
  CpuChipIcon,
  AdjustmentsHorizontalIcon,
  PlayIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { AVAILABLE_MODELS } from "../services/api";

const ArticleInput = ({
  canGenerate,
  isGenerating,
  onGenerate,
  executionProgress,
}) => {
  const [article, setArticle] = useState("");
  const [wordCount, setWordCount] = useState(0);
  const [showAISettings, setShowAISettings] = useState(false);
  const [aiSettings, setAiSettings] = useState({
    model: "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    temperature: 0.7,
    maxTokens: 4000,
    titleCount: 5, // 제목 개수 설정 추가
  });

  const handleArticleChange = (e) => {
    const text = e.target.value;
    setArticle(text);
    setWordCount(
      text
        .trim()
        .split(/\s+/)
        .filter((word) => word.length > 0).length
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!article.trim()) {
      alert("기사 내용을 입력해주세요.");
      return;
    }
    if (article.length < 100) {
      alert("더 자세한 기사 내용을 입력해주세요. (최소 100자)");
      return;
    }

    try {
      await onGenerate(article, aiSettings);
    } catch (error) {
      console.error("제목 생성 실패:", error);
    }
  };

  const getProgressSteps = () => {
    return [
      {
        id: "fetch_prompts",
        name: "프롬프트 조회",
        description: "설정된 프롬프트 카드를 가져옵니다",
        icon: DocumentTextIcon,
      },
      {
        id: "build_payload",
        name: "페이로드 구성",
        description: "AI 모델 입력 데이터를 준비합니다",
        icon: Cog8ToothIcon,
      },
      {
        id: "call_bedrock",
        name: "AI 모델 호출",
        description: "Bedrock AI 모델이 제목을 생성합니다",
        icon: SparklesIcon,
      },
      {
        id: "save_results",
        name: "결과 저장",
        description: "생성된 제목과 메타데이터를 저장합니다",
        icon: CheckCircleIcon,
      },
    ];
  };

  const getCurrentStepIndex = () => {
    if (!executionProgress) return -1;

    switch (executionProgress.status) {
      case "started":
        return 0;
      case "processing":
        return 1;
      case "generating":
        return 2;
      case "saving":
        return 3;
      case "completed":
        return 4;
      default:
        return -1;
    }
  };

  const getStepStatus = (stepIndex) => {
    const currentStep = getCurrentStepIndex();

    if (executionProgress?.status === "failed") {
      return stepIndex <= currentStep ? "failed" : "pending";
    }

    if (stepIndex < currentStep) return "completed";
    if (stepIndex === currentStep) return "active";
    return "pending";
  };

  const getStepIcon = (step, status) => {
    const IconComponent = step.icon;

    switch (status) {
      case "completed":
        return <CheckCircleIcon className="h-5 w-5 text-green-600" />;
      case "active":
        return (
          <IconComponent className="h-5 w-5 text-blue-600 animate-pulse" />
        );
      case "failed":
        return <XMarkIcon className="h-5 w-5 text-red-600" />;
      default:
        return <IconComponent className="h-5 w-5 text-gray-400" />;
    }
  };

  const selectedModel = AVAILABLE_MODELS.find((m) => m.id === aiSettings.model);

  return (
    <div className="space-y-6">
      {/* AI 설정 패널 */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <button
          onClick={() => setShowAISettings(!showAISettings)}
          className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <AdjustmentsHorizontalIcon className="h-5 w-5 text-gray-600" />
            <div className="text-left">
              <h3 className="font-medium text-gray-900">AI 모델 설정</h3>
              <p className="text-sm text-gray-500">
                {selectedModel?.name} • 온도: {aiSettings.temperature} • 최대
                토큰: {aiSettings.maxTokens} • 제목 수: {aiSettings.titleCount}개
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">
              {showAISettings ? "접기" : "펼치기"}
            </span>
            <div
              className={`transform transition-transform ${
                showAISettings ? "rotate-180" : ""
              }`}
            >
              <svg
                className="h-5 w-5 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </div>
          </div>
        </button>

        {showAISettings && (
          <div className="px-6 pb-6 border-t border-gray-200 bg-gray-50">
            <div className="pt-4 space-y-6">
              {/* 모델 선택 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  AI 모델
                </label>
                <select
                  value={aiSettings.model}
                  onChange={(e) =>
                    setAiSettings((prev) => ({
                      ...prev,
                      model: e.target.value,
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
                >
                  {AVAILABLE_MODELS.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))}
                </select>
                {selectedModel && (
                  <p className="mt-1 text-sm text-gray-500">
                    {selectedModel.description}
                  </p>
                )}
              </div>

              {/* 온도 설정 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  창의성 (Temperature): {aiSettings.temperature}
                </label>
                <div className="space-y-2">
                  <div className="flex items-center space-x-4">
                    <span className="text-sm text-gray-500 min-w-[60px]">
                      보수적
                    </span>
                    <div className="flex-1 relative">
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={aiSettings.temperature}
                        onChange={(e) =>
                          setAiSettings((prev) => ({
                            ...prev,
                            temperature: parseFloat(e.target.value),
                          }))
                        }
                        className="w-full h-2 bg-gradient-to-r from-blue-200 to-orange-200 rounded-lg appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                        style={{
                          background: `linear-gradient(to right, #dbeafe 0%, #fed7aa 100%)`,
                          WebkitAppearance: "none",
                        }}
                      />
                      <style jsx>{`
                        input[type="range"]::-webkit-slider-thumb {
                          appearance: none;
                          width: 20px;
                          height: 20px;
                          border-radius: 50%;
                          background: linear-gradient(135deg, #3b82f6, #f97316);
                          cursor: pointer;
                          border: 2px solid white;
                          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                        }
                        input[type="range"]::-moz-range-thumb {
                          width: 20px;
                          height: 20px;
                          border-radius: 50%;
                          background: linear-gradient(135deg, #3b82f6, #f97316);
                          cursor: pointer;
                          border: 2px solid white;
                          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                        }
                      `}</style>
                    </div>
                    <span className="text-sm text-gray-500 min-w-[60px]">
                      창의적
                    </span>
                  </div>
                  {/* 눈금 표시 */}
                  <div className="flex justify-between text-xs text-gray-400 px-2">
                    <span>0.0</span>
                    <span>0.2</span>
                    <span>0.4</span>
                    <span>0.6</span>
                    <span>0.8</span>
                    <span>1.0</span>
                  </div>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  낮을수록 일관된 결과, 높을수록 창의적인 결과를 생성합니다
                </p>
              </div>

              {/* 최대 토큰 설정 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  최대 토큰 수
                </label>
                <input
                  type="number"
                  min="1000"
                  max={selectedModel?.maxTokens || 200000}
                  value={aiSettings.maxTokens}
                  onChange={(e) =>
                    setAiSettings((prev) => ({
                      ...prev,
                      maxTokens: parseInt(e.target.value),
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
                />
                <p className="mt-1 text-xs text-gray-500">
                  생성할 수 있는 최대 토큰 수 (대략 단어 수의 3/4)
                </p>
              </div>

              {/* 제목 개수 설정 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  생성할 제목 개수
                </label>
                <div className="grid grid-cols-5 gap-2">
                  {[3, 5, 7, 10, 15].map((count) => (
                    <button
                      key={count}
                      type="button"
                      onClick={() =>
                        setAiSettings((prev) => ({
                          ...prev,
                          titleCount: count,
                        }))
                      }
                      className={`px-3 py-2 text-sm font-medium rounded-lg border transition-all duration-200 ${
                        aiSettings.titleCount === count
                          ? "bg-blue-600 text-white border-blue-600 shadow-md"
                          : "bg-white text-gray-700 border-gray-300 hover:bg-blue-50 hover:border-blue-300"
                      }`}
                    >
                      {count}개
                    </button>
                  ))}
                </div>
                <div className="mt-3">
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    또는 직접 입력 (최대 20개)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={aiSettings.titleCount}
                    onChange={(e) =>
                      setAiSettings((prev) => ({
                        ...prev,
                        titleCount: Math.min(20, Math.max(1, parseInt(e.target.value) || 1)),
                      }))
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900 text-sm"
                  />
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  더 많은 제목을 생성할수록 더 다양한 옵션을 받을 수 있습니다
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 제목 생성 안내 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3 flex items-center">
          <InformationCircleIcon className="h-5 w-5 mr-2" />
          제목 생성 안내
        </h3>
        <div className="space-y-2 text-sm text-blue-800">
          <p>
            • 기사 원문을 입력하시면 설정된 프롬프트 카드를 바탕으로 AI가 최적의
            제목을 생성합니다
          </p>
          <p>
            • 생성 과정은 4단계로 진행되며, 각 단계별 진행 상황을 실시간으로
            확인할 수 있습니다
          </p>
          <p>• 최소 100자 이상의 기사 내용을 입력해주세요</p>
          <p>• 더 자세한 기사 내용일수록 더 정확한 제목이 생성됩니다</p>
        </div>
      </div>

      {/* 제목 생성 가능 여부 표시 */}
      {!canGenerate && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center">
            <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 mr-2" />
            <p className="text-sm font-medium text-yellow-800">
              제목 생성을 위해서는 먼저 프롬프트 카드를 설정해야 합니다.
            </p>
          </div>
        </div>
      )}

      {/* 진행 상황 표시 */}
      {isGenerating && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center mb-4">
            <Cog8ToothIcon className="h-5 w-5 text-blue-600 animate-spin mr-2" />
            <h3 className="text-lg font-semibold text-gray-900">
              제목 생성 중...
            </h3>
          </div>

          <div className="space-y-4">
            {getProgressSteps().map((step, index) => {
              const status = getStepStatus(index);
              return (
                <div
                  key={step.id}
                  className={`flex items-center space-x-4 p-3 rounded-lg ${
                    status === "active"
                      ? "bg-blue-50 border border-blue-200"
                      : status === "completed"
                      ? "bg-green-50 border border-green-200"
                      : status === "failed"
                      ? "bg-red-50 border border-red-200"
                      : "bg-gray-50 border border-gray-200"
                  }`}
                >
                  <div className="flex-shrink-0">
                    {getStepIcon(step, status)}
                  </div>
                  <div className="flex-1">
                    <h4
                      className={`font-medium ${
                        status === "active"
                          ? "text-blue-900"
                          : status === "completed"
                          ? "text-green-900"
                          : status === "failed"
                          ? "text-red-900"
                          : "text-gray-700"
                      }`}
                    >
                      {step.name}
                    </h4>
                    <p
                      className={`text-sm ${
                        status === "active"
                          ? "text-blue-700"
                          : status === "completed"
                          ? "text-green-700"
                          : status === "failed"
                          ? "text-red-700"
                          : "text-gray-500"
                      }`}
                    >
                      {step.description}
                    </p>
                  </div>
                  {status === "active" && (
                    <div className="flex-shrink-0">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {executionProgress?.message && (
            <div className="mt-4 p-3 bg-gray-100 rounded-lg">
              <p className="text-sm text-gray-700">
                {executionProgress.message}
              </p>
            </div>
          )}
        </div>
      )}

      {/* 기사 입력 폼 */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <DocumentTextIcon className="h-5 w-5 mr-2 text-blue-600" />
              기사 내용 입력
            </h3>
            <div className="flex items-center space-x-4 text-sm text-gray-500">
              <span>{wordCount} 단어</span>
              <span>{article.length} 글자</span>
            </div>
          </div>

          <textarea
            value={article}
            onChange={handleArticleChange}
            placeholder="제목을 생성할 기사 내용을 입력해주세요. 최소 100자 이상 입력해야 합니다."
            className="w-full h-64 px-4 py-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900 placeholder-gray-500"
            disabled={isGenerating}
          />

          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {article.length >= 100 ? (
                <CheckCircleIcon className="h-5 w-5 text-green-600" />
              ) : (
                <ClockIcon className="h-5 w-5 text-yellow-600" />
              )}
              <span
                className={`text-sm ${
                  article.length >= 100 ? "text-green-600" : "text-yellow-600"
                }`}
              >
                {article.length >= 100
                  ? "입력 완료"
                  : `${100 - article.length}자 더 입력해주세요`}
              </span>
            </div>

            <button
              type="submit"
              disabled={
                !canGenerate ||
                !article.trim() ||
                article.length < 100 ||
                isGenerating
              }
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isGenerating ? (
                <>
                  <Cog8ToothIcon className="h-5 w-5 mr-2 animate-spin" />
                  생성 중...
                </>
              ) : (
                <>
                  <PlayIcon className="h-5 w-5 mr-2" />
                  제목 생성하기
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* 팁 */}
      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <h4 className="font-medium text-gray-900 mb-2 flex items-center">
          <InformationCircleIcon className="h-4 w-4 mr-1" />
          💡 더 나은 제목을 위한 팁
        </h4>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>• 기사의 핵심 내용과 주요 키워드를 포함해주세요</li>
          <li>• 구체적인 수치나 데이터가 있다면 함께 입력해주세요</li>
          <li>• 기사의 톤앤매너(긍정적/부정적/중립적)를 명확히 해주세요</li>
          <li>• 대상 독자층을 고려한 내용을 작성해주세요</li>
        </ul>
      </div>
    </div>
  );
};

export default memo(ArticleInput);
