import React, { useState } from "react";
import { ChevronDownIcon, SparklesIcon } from "@heroicons/react/24/outline";

const MODELS = [
  // Anthropic Claude 모델들 (추천)
  {
    id: "anthropic.claude-3-5-sonnet-20241022-v2:0",
    name: "Claude 3.5 Sonnet v2",
    provider: "Anthropic",
    category: "premium",
    speed: "빠름",
    quality: "최고",
    description: "텍스트 생성, 다국어 지원, 복잡한 추론에 최적",
    recommended: true,
  },
  {
    id: "anthropic.claude-3-5-haiku-20241022-v1:0",
    name: "Claude 3.5 Haiku",
    provider: "Anthropic",
    category: "fast",
    speed: "매우 빠름",
    quality: "좋음",
    description: "빠른 응답, 텍스트 생성에 최적화",
    recommended: true,
  },
  {
    id: "anthropic.claude-sonnet-4-v1:0",
    name: "Claude Sonnet 4",
    provider: "Anthropic",
    category: "premium",
    speed: "보통",
    quality: "최고",
    description: "최신 모델로 향상된 텍스트 생성, 실시간 지원",
    new: true,
  },
  {
    id: "anthropic.claude-opus-4-v1:0",
    name: "Claude Opus 4",
    provider: "Anthropic",
    category: "premium",
    speed: "느림",
    quality: "최고",
    description: "최고 성능이 필요한 복잡한 제목 생성",
    new: true,
  },
  {
    id: "anthropic.claude-3-opus-20240229-v1:0",
    name: "Claude 3 Opus",
    provider: "Anthropic",
    category: "premium",
    speed: "느림",
    quality: "최고",
    description: "이미지를 텍스트 및 코드로 변환, 복잡한 추론",
  },
  {
    id: "anthropic.claude-3-sonnet-20240229-v1:0",
    name: "Claude 3 Sonnet",
    provider: "Anthropic",
    category: "balanced",
    speed: "보통",
    quality: "좋음",
    description: "균형잡힌 성능과 속도",
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

  // Amazon Nova 모델들
  {
    id: "amazon.nova-pro-v1:0",
    name: "Nova Pro",
    provider: "Amazon",
    category: "balanced",
    speed: "빠름",
    quality: "좋음",
    description: "텍스트 생성, 코드 생성, 복잡한 추론",
    recommended: true,
  },
  {
    id: "amazon.nova-lite-v1:0",
    name: "Nova Lite",
    provider: "Amazon",
    category: "fast",
    speed: "매우 빠름",
    quality: "보통",
    description: "가벼운 모델로 빠른 응답, 다국어 지원",
  },
  {
    id: "amazon.nova-micro-v1:0",
    name: "Nova Micro",
    provider: "Amazon",
    category: "fast",
    speed: "초고속",
    quality: "기본",
    description: "초경량 모델로 매우 빠른 응답",
  },

  // Meta Llama 모델들
  {
    id: "meta.llama3-3-70b-instruct-v1:0",
    name: "Llama 3.3 70B",
    provider: "Meta",
    category: "balanced",
    speed: "보통",
    quality: "좋음",
    description: "툴 사용, 코드 생성, 고급 추론",
  },
  {
    id: "meta.llama3-2-3b-instruct-v1:0",
    name: "Llama 3.2 3B",
    provider: "Meta",
    category: "fast",
    speed: "빠름",
    quality: "보통",
    description: "경량 모델로 빠른 처리",
  },
];

const ModelSelector = ({ selectedModel, onModelChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [filter, setFilter] = useState("all");

  console.log("🤖 ModelSelector 렌더링됨:", { selectedModel, isOpen });

  const currentModel =
    MODELS.find((model) => model.id === selectedModel) || MODELS[0];

  const filteredModels = MODELS.filter((model) => {
    if (filter === "all") return true;
    return model.provider.toLowerCase() === filter;
  });

  const handleModelSelect = (modelId) => {
    onModelChange(modelId);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      {/* 모델 선택 버튼 - 컴팩트 버전 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-2 py-1 bg-gray-50 dark:bg-gray-700 rounded-md hover:bg-gray-100 dark:hover:bg-gray-600 shadow-sm dark:shadow-none transition-colors text-xs"
        title={`${currentModel.name} (${currentModel.provider})`}
      >
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
          {/* 필터 버튼들 */}
          <div className="p-3 ">
            <div className="flex gap-1 text-xs">
              {[
                { key: "all", label: "전체" },
                { key: "anthropic", label: "Anthropic" },
                { key: "amazon", label: "Amazon" },
                { key: "meta", label: "Meta" },
              ].map((filterOption) => (
                <button
                  key={filterOption.key}
                  onClick={() => setFilter(filterOption.key)}
                  className={`px-2 py-1 rounded transition-colors ${
                    filter === filterOption.key
                      ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                      : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-dark-tertiary"
                  }`}
                >
                  {filterOption.label}
                </button>
              ))}
            </div>
          </div>

          {/* 모델 목록 */}
          <div className="max-h-[300px] overflow-y-auto">
            {filteredModels.map((model) => (
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
