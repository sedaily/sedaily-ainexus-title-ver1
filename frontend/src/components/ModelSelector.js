import React, { useState } from "react";
import { ChevronDownIcon, SparklesIcon } from "@heroicons/react/24/outline";

// 백엔드에서 실제 지원하는 모델만 포함 (generate.py의 SUPPORTED_MODELS 기준)
const MODELS = [
  // 기본 모델 (백엔드 DEFAULT_MODEL_ID)
  {
    id: "apac.anthropic.claude-sonnet-4-20250514-v1:0",
    name: "Claude Sonnet 4",
    provider: "Anthropic",
    category: "premium",
    speed: "보통",
    quality: "최고",
    description: "기본 모델, 향상된 텍스트 생성 및 실시간 지원",
    recommended: true,
    default: true,
  },
  
  // Anthropic Claude 4 시리즈
  {
    id: "anthropic.claude-opus-4-v1:0",
    name: "Claude Opus 4",
    provider: "Anthropic",
    category: "premium",
    speed: "느림",
    quality: "최고",
    description: "최고 성능이 필요한 복잡한 제목 생성",
    recommended: true,
  },
  {
    id: "anthropic.claude-sonnet-4-v1:0",
    name: "Claude Sonnet 4",
    provider: "Anthropic",
    category: "premium",
    speed: "보통",
    quality: "최고",
    description: "균형잡힌 최신 모델",
  },
  
  // Anthropic Claude 3 시리즈
  {
    id: "anthropic.claude-3-5-haiku-20241022-v1:0",
    name: "Claude 3.5 Haiku",
    provider: "Anthropic",
    category: "fast",
    speed: "매우 빠름",
    quality: "좋음",
    description: "빠른 응답, 텍스트 생성에 최적화",
  },
  {
    id: "anthropic.claude-3-opus-20240229-v1:0",
    name: "Claude 3 Opus",
    provider: "Anthropic",
    category: "premium",
    speed: "느림",
    quality: "최고",
    description: "복잡한 추론 및 분석에 최적",
  },
  {
    id: "anthropic.claude-3-haiku-20240307-v1:0",
    name: "Claude 3 Haiku",
    provider: "Anthropic",
    category: "fast",
    speed: "빠름",
    quality: "보통",
    description: "대화, 채팅 최적화",
  },
];

const ModelSelector = ({ selectedModel, onModelChange }) => {
  const [isOpen, setIsOpen] = useState(false);

  console.log("🤖 ModelSelector 렌더링됨:", { selectedModel, isOpen });

  const currentModel =
    MODELS.find((model) => model.id === selectedModel) || MODELS[0];

  const handleModelSelect = (modelId) => {
    onModelChange(modelId);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      {/* 모델 선택 버튼 - 컴팩트 버전 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600 shadow-sm transition-all duration-200 text-xs"
        title={`${currentModel.name} (${currentModel.provider})`}
      >
        <SparklesIcon className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
        <span className="text-gray-700 dark:text-gray-300 font-medium">
          {currentModel.name.replace(/Claude |Llama |Nova /, "")}
        </span>
        <ChevronDownIcon
          className={`h-3 w-3 text-gray-500 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* 드롭다운 메뉴 */}
      {isOpen && (
        <div className="absolute bottom-full left-0 mb-2 bg-white dark:bg-dark-secondary  rounded-lg shadow-lg z-50 max-h-[400px] overflow-hidden min-w-[300px]">
          {/* 모델 목록 */}
          <div className="max-h-[300px] overflow-y-auto">
            {MODELS.map((model) => (
              <button
                key={model.id}
                onClick={() => handleModelSelect(model.id)}
                className={`w-full p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700 last:border-b-0 transition-colors ${
                  model.id === selectedModel
                    ? "bg-blue-50 dark:bg-blue-900/20"
                    : ""
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="mb-1">
                    <span className="font-medium text-gray-900 dark:text-white">
                      {model.name}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                    {model.provider} • 속도: {model.speed} • 품질:{" "}
                    {model.quality}
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    {model.description}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 배경 클릭 시 닫기 */}
      {isOpen && (
        <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
      )}
    </div>
  );
};

export default ModelSelector;
