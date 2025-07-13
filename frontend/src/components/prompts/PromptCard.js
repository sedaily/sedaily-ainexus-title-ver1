import React from "react";
import {
  PencilIcon,
  TrashIcon,
  EyeIcon,
  EyeSlashIcon,
  Cog6ToothIcon,
  DocumentTextIcon,
  SparklesIcon,
  EllipsisHorizontalIcon,
} from "@heroicons/react/24/outline";
import { AVAILABLE_MODELS } from "../../services/api";

const PromptCard = ({
  card,
  onEdit,
  onToggle,
  onDelete,
  isCurrentStep = false,
  isExecuted = false,
  isExecuting = false,
  stepNumber = 0,
  hideDeleteButton = false, // 삭제 버튼 숨김 옵션 추가
}) => {
  const getModelDisplayName = (modelId) => {
    const model = AVAILABLE_MODELS.find((m) => m.id === modelId);
    return model ? model.name : modelId;
  };

  const handleToggleClick = async () => {
    try {
      await onToggle(card.promptId || card.id, !card.enabled);
    } catch (error) {
      console.error("카드 토글 실패:", error);
    }
  };

  const handleEdit = () => {
    onEdit(card);
  };

  const getCardStyles = () => {
    let baseStyles =
      "relative bg-white border border-gray-200 rounded-lg p-3 transition-all duration-200 hover:border-gray-300 group";

    if (isCurrentStep) {
      baseStyles += " ring-2 ring-blue-400 border-blue-200 bg-blue-50";
    } else if (isExecuted) {
      baseStyles += " ring-1 ring-green-400 border-green-200 bg-green-50";
    } else if (card.enabled) {
      baseStyles += " hover:ring-1 hover:ring-gray-300";
    } else {
      baseStyles += " bg-gray-50 opacity-60 hover:opacity-80";
    }

    return baseStyles;
  };

  const getCategoryInfo = (categoryId) => {
    const categories = {
      instruction: { 
        name: "역할 및 목표", 
        color: "bg-slate-100/80 text-slate-700 border-slate-200/80",
        icon: "" 
      },
      knowledge: {
        name: "지식 베이스",
        color: "bg-slate-100/80 text-slate-700 border-slate-200/80", 
        icon: ""
      },
      secondary: { 
        name: "CoT (사고 과정)", 
        color: "bg-slate-100/80 text-slate-700 border-slate-200/80",
        icon: ""
      },
      style_guide: {
        name: "스타일 가이드",
        color: "bg-slate-100/80 text-slate-700 border-slate-200/80",
        icon: ""
      },
      validation: { 
        name: "ReAct (추론+행동)", 
        color: "bg-slate-100/80 text-slate-700 border-slate-200/80",
        icon: ""
      },
      enhancement: { 
        name: "품질 검증", 
        color: "bg-slate-100/80 text-slate-700 border-slate-200/80",
        icon: ""
      },
    };
    return (
      categories[categoryId] || {
        name: categoryId,
        color: "bg-slate-100/80 text-slate-700 border-slate-200/80",
        icon: ""
      }
    );
  };

  const categoryInfo = getCategoryInfo(card.category);

  return (
    <div className={getCardStyles()}>
      {/* 실행 상태 표시 */}
      {isExecuting && (
        <div className="absolute -top-1 -right-1 z-10">
          <div className="flex items-center justify-center w-5 h-5 bg-blue-500 text-white rounded-full">
            <div className="animate-spin rounded-full h-2 w-2 border border-t-transparent border-white"></div>
          </div>
        </div>
      )}

      {/* 카드 헤더 */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {/* 아이콘과 카테고리 */}
          <div className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${categoryInfo.color}`}>
            <span>{categoryInfo.name}</span>
          </div>
        </div>

        {/* 액션 버튼들 */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          {/* 활성화/비활성화 토글 */}
          <button
            onClick={handleToggleClick}
            className={`p-1.5 rounded transition-colors ${
              card.enabled
                ? "text-green-600 hover:bg-green-50"
                : "text-gray-400 hover:bg-gray-100"
            }`}
            title={card.enabled ? "비활성화" : "활성화"}
          >
            {card.enabled ? (
              <EyeIcon className="h-3 w-3" />
            ) : (
              <EyeSlashIcon className="h-3 w-3" />
            )}
          </button>

          {/* 편집 버튼 */}
          <button
            onClick={handleEdit}
            className="p-1.5 text-gray-600 hover:bg-blue-50 hover:text-blue-600 rounded transition-colors"
            title="편집"
          >
            <PencilIcon className="h-3 w-3" />
          </button>

          {/* 삭제 버튼 - hideDeleteButton이 true면 숨김 */}
          {!hideDeleteButton && (
            <button
              onClick={() => onDelete(card.promptId || card.id)}
              className="p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 rounded transition-colors"
              title="삭제"
            >
              <TrashIcon className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>

      {/* 프롬프트 설명 */}
      <div className="text-xs text-gray-500 leading-relaxed mb-2">
        {card.description || categoryInfo.description || "프롬프트 설명이 없습니다."}
      </div>

      {/* 특수 기능 표시 */}
      {(card.isCoT || card.isReAct) && (
        <div className="flex gap-1 mb-2">
          {card.isCoT && (
            <span className="inline-flex items-center px-2 py-0.5 bg-purple-50 text-purple-700 rounded text-xs font-medium">
              <span>CoT</span>
            </span>
          )}
          {card.isReAct && (
            <span className="inline-flex items-center px-2 py-0.5 bg-orange-50 text-orange-700 rounded text-xs font-medium">
              <span>ReAct</span>
            </span>
          )}
        </div>
      )}


      {/* 실행 완료 표시 */}
      {isExecuted && (
        <div className="mt-2 flex items-center text-green-600 text-xs bg-green-50 p-2 rounded border border-green-200">
          <SparklesIcon className="h-3 w-3 mr-1" />
          <span>실행 완료</span>
        </div>
      )}
    </div>
  );
};

export default PromptCard;
