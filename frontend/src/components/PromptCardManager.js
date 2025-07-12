import React, { useState, useEffect, useCallback } from "react";
import { toast } from "react-hot-toast";
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  EyeIcon,
  EyeSlashIcon,
  Cog6ToothIcon,
  DocumentTextIcon,
  SparklesIcon,
  InformationCircleIcon,
  ArrowsUpDownIcon,
  Bars3Icon,
} from "@heroicons/react/24/outline";
import {
  promptCardAPI,
  PROMPT_CARD_CATEGORIES,
  AVAILABLE_MODELS,
  handleAPIError,
} from "../services/api";

const PromptCardManager = ({ projectId, onCardsChanged }) => {
  const [promptCards, setPromptCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingCard, setEditingCard] = useState(null);
  const [draggedCard, setDraggedCard] = useState(null);
  const [dragOverIndex, setDragOverIndex] = useState(null);

  // 프롬프트 카드 목록 로딩
  const loadPromptCards = useCallback(async () => {
    try {
      setLoading(true);
      const response = await promptCardAPI.getPromptCards(
        projectId,
        true,
        true
      );
      setPromptCards(response.promptCards || []);
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`프롬프트 카드 로딩 실패: ${errorInfo.message}`);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadPromptCards();
  }, [loadPromptCards]);

  // 새 프롬프트 카드 생성
  const handleCreateCard = async (cardData) => {
    try {
      await promptCardAPI.createPromptCard(projectId, cardData);
      toast.success("프롬프트 카드가 생성되었습니다!");
      setShowCreateModal(false);
      loadPromptCards();
      if (onCardsChanged) onCardsChanged();
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`카드 생성 실패: ${errorInfo.message}`);
    }
  };

  // 프롬프트 카드 수정
  const handleUpdateCard = async (promptId, cardData) => {
    try {
      await promptCardAPI.updatePromptCard(projectId, promptId, cardData);
      toast.success("프롬프트 카드가 수정되었습니다!");
      setEditingCard(null);
      loadPromptCards();
      if (onCardsChanged) onCardsChanged();
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`카드 수정 실패: ${errorInfo.message}`);
    }
  };

  // 프롬프트 카드 삭제
  const handleDeleteCard = async (promptId) => {
    if (!window.confirm("정말로 이 프롬프트 카드를 삭제하시겠습니까?")) {
      return;
    }

    try {
      await promptCardAPI.deletePromptCard(projectId, promptId);
      toast.success("프롬프트 카드가 삭제되었습니다!");
      loadPromptCards();
      if (onCardsChanged) onCardsChanged();
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`카드 삭제 실패: ${errorInfo.message}`);
    }
  };

  // 프롬프트 카드 활성/비활성 토글
  const handleToggleCard = async (promptId, enabled) => {
    try {
      await promptCardAPI.togglePromptCard(projectId, promptId, enabled);
      toast.success(
        enabled ? "카드가 활성화되었습니다!" : "카드가 비활성화되었습니다!"
      );
      loadPromptCards();
      if (onCardsChanged) onCardsChanged();
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`상태 변경 실패: ${errorInfo.message}`);
    }
  };

  // 드래그 앤 드롭 핸들러
  const handleDragStart = (e, card) => {
    setDraggedCard(card);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverIndex(index);
  };

  const handleDragLeave = () => {
    setDragOverIndex(null);
  };

  const handleDrop = async (e, targetIndex) => {
    e.preventDefault();
    setDragOverIndex(null);

    if (!draggedCard) return;

    const currentIndex = promptCards.findIndex(
      (card) => card.promptId === draggedCard.promptId
    );

    if (currentIndex === targetIndex) {
      setDraggedCard(null);
      return;
    }

    try {
      // 새로운 step_order 계산
      const newStepOrder = targetIndex + 1;

      await promptCardAPI.reorderPromptCard(
        projectId,
        draggedCard.promptId,
        newStepOrder
      );

      toast.success("카드 순서가 변경되었습니다!");
      loadPromptCards();
      if (onCardsChanged) onCardsChanged();
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`순서 변경 실패: ${errorInfo.message}`);
    }

    setDraggedCard(null);
  };

  // 카테고리 정보 가져오기
  const getCategoryInfo = (categoryId) => {
    return (
      PROMPT_CARD_CATEGORIES.find((cat) => cat.id === categoryId) || {
        name: "알 수 없음",
        color: "gray",
        icon: "❓",
      }
    );
  };

  // 모델 정보 가져오기
  const getModelInfo = (modelId) => {
    return (
      AVAILABLE_MODELS.find((model) => model.id === modelId) || {
        name: "알 수 없는 모델",
      }
    );
  };

  // 카테고리별 색상 클래스 반환
  const getCategoryColorClasses = (color, enabled = true) => {
    const opacity = enabled ? "" : "opacity-60";
    const colors = {
      blue: `bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-200 dark:border-blue-800`,
      purple: `bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/30 dark:text-purple-200 dark:border-purple-800`,
      green: `bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-200 dark:border-green-800`,
      orange: `bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-200 dark:border-orange-800`,
      red: `bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-200 dark:border-red-800`,
      yellow: `bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-200 dark:border-yellow-800`,
      gray: `bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600`,
    };
    return `${colors[color] || colors.gray} ${opacity}`;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-400 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">
            프롬프트 카드 로딩 중...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            프롬프트 카드 관리
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            드래그 앤 드롭으로 순서를 변경하고, 각 단계별 프롬프트를 설정하세요.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors shadow-sm"
        >
          <PlusIcon className="h-5 w-5 mr-2" />새 카드 추가
        </button>
      </div>

      {/* 사용 안내 */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
        <div className="flex items-start">
          <InformationCircleIcon className="h-5 w-5 text-blue-600 dark:text-blue-400 mr-2 mt-0.5" />
          <div>
            <h3 className="font-medium text-blue-900 dark:text-blue-100 mb-1">
              💡 프롬프트 카드 사용 팁
            </h3>
            <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
              <li>• 카드를 드래그하여 실행 순서를 변경할 수 있습니다</li>
              <li>• 각 카드는 독립적으로 활성/비활성화할 수 있습니다</li>
              <li>• 카테고리별로 색상이 구분되어 관리가 쉽습니다</li>
              <li>• AI 모델과 온도 설정을 카드별로 개별 설정 가능합니다</li>
            </ul>
          </div>
        </div>
      </div>

      {/* 통계 정보 */}
      {promptCards.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center">
              <DocumentTextIcon className="h-5 w-5 text-blue-600 dark:text-blue-400 mr-2" />
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                총 카드
              </span>
            </div>
            <p className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">
              {promptCards.length}
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center">
              <EyeIcon className="h-5 w-5 text-green-600 dark:text-green-400 mr-2" />
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                활성 카드
              </span>
            </div>
            <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">
              {promptCards.filter((card) => card.enabled !== false).length}
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center">
              <EyeSlashIcon className="h-5 w-5 text-gray-600 dark:text-gray-400 mr-2" />
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                비활성 카드
              </span>
            </div>
            <p className="text-2xl font-bold text-gray-600 dark:text-gray-400 mt-1">
              {promptCards.filter((card) => card.enabled === false).length}
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center">
              <ArrowsUpDownIcon className="h-5 w-5 text-purple-600 dark:text-purple-400 mr-2" />
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                카테고리
              </span>
            </div>
            <p className="text-2xl font-bold text-purple-600 dark:text-purple-400 mt-1">
              {new Set(promptCards.map((card) => card.category)).size}
            </p>
          </div>
        </div>
      )}

      {/* 프롬프트 카드 목록 */}
      {promptCards.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <DocumentTextIcon className="h-16 w-16 text-gray-400 dark:text-gray-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            프롬프트 카드가 없습니다
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            첫 번째 프롬프트 카드를 추가해서 AI 제목 생성을 시작해보세요.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center mx-auto px-6 py-3 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors shadow-sm"
          >
            <PlusIcon className="h-5 w-5 mr-2" />첫 카드 만들기
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {promptCards.map((card, index) => {
            const categoryInfo = getCategoryInfo(card.category);
            const modelInfo = getModelInfo(card.model);
            const isEnabled = card.enabled !== false;

            return (
              <div
                key={card.promptId}
                draggable
                onDragStart={(e) => handleDragStart(e, card)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, index)}
                className={`bg-white dark:bg-gray-800 rounded-lg border-2 transition-all duration-200 cursor-move shadow-sm hover:shadow-md ${
                  dragOverIndex === index
                    ? "border-blue-500 dark:border-blue-400 shadow-lg transform scale-[1.02]"
                    : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
                } ${
                  draggedCard?.promptId === card.promptId
                    ? "opacity-50 scale-95"
                    : ""
                } ${!isEnabled ? "opacity-60" : ""}`}
              >
                <div className="p-6">
                  {/* 카드 헤더 */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      <div className="flex items-center space-x-2">
                        <Bars3Icon className="h-4 w-4 text-gray-400 dark:text-gray-500" />
                        <span className="text-lg">{categoryInfo.icon}</span>
                        <span
                          className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${getCategoryColorClasses(
                            categoryInfo.color,
                            isEnabled
                          )}`}
                        >
                          Step {card.stepOrder}
                        </span>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                          {card.title || `${categoryInfo.name} 단계`}
                        </h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {card.description || categoryInfo.description}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {/* 활성/비활성 토글 */}
                      <button
                        onClick={() =>
                          handleToggleCard(card.promptId, !isEnabled)
                        }
                        className={`p-2 rounded-lg transition-colors ${
                          isEnabled
                            ? "text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20"
                            : "text-gray-400 dark:text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-700"
                        }`}
                        title={isEnabled ? "비활성화" : "활성화"}
                      >
                        {isEnabled ? (
                          <EyeIcon className="h-5 w-5" />
                        ) : (
                          <EyeSlashIcon className="h-5 w-5" />
                        )}
                      </button>

                      {/* 수정 버튼 */}
                      <button
                        onClick={() => setEditingCard(card)}
                        className="p-2 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                        title="수정"
                      >
                        <PencilIcon className="h-5 w-5" />
                      </button>

                      {/* 삭제 버튼 */}
                      <button
                        onClick={() => handleDeleteCard(card.promptId)}
                        className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                        title="삭제"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </div>

                  {/* 카드 설정 정보 */}
                  <div className="flex items-center space-x-4 mb-4">
                    <div className="flex items-center space-x-1 text-sm text-gray-600 dark:text-gray-400">
                      <SparklesIcon className="h-4 w-4" />
                      <span>{modelInfo.name}</span>
                    </div>
                    <div className="flex items-center space-x-1 text-sm text-gray-600 dark:text-gray-400">
                      <Cog6ToothIcon className="h-4 w-4" />
                      <span>온도: {card.temperature}</span>
                    </div>
                    <div className="flex items-center space-x-1 text-sm text-gray-600 dark:text-gray-400">
                      <DocumentTextIcon className="h-4 w-4" />
                      <span>
                        {card.prompt_text
                          ? `${card.prompt_text.length}자`
                          : "내용 없음"}
                      </span>
                    </div>
                  </div>

                  {/* 프롬프트 내용 미리보기 */}
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
                    <div className="text-sm text-gray-700 dark:text-gray-300">
                      {card.prompt_text ? (
                        card.prompt_text.length > 200 ? (
                          <>
                            <span className="font-mono text-xs leading-relaxed">
                              {card.prompt_text.substring(0, 200)}...
                            </span>
                            <button
                              onClick={() => setEditingCard(card)}
                              className="text-blue-600 dark:text-blue-400 hover:underline ml-2 font-medium"
                            >
                              더보기
                            </button>
                          </>
                        ) : (
                          <span className="font-mono text-xs leading-relaxed">
                            {card.prompt_text}
                          </span>
                        )
                      ) : (
                        <span className="text-gray-400 dark:text-gray-500 italic">
                          프롬프트 내용이 없습니다. 수정하여 내용을
                          추가해주세요.
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 카드 생성/수정 모달 */}
      {(showCreateModal || editingCard) && (
        <PromptCardModal
          isOpen={showCreateModal || !!editingCard}
          onClose={() => {
            setShowCreateModal(false);
            setEditingCard(null);
          }}
          onSave={editingCard ? handleUpdateCard : handleCreateCard}
          editingCard={editingCard}
          projectId={projectId}
        />
      )}
    </div>
  );
};

// 프롬프트 카드 생성/수정 모달
const PromptCardModal = ({
  isOpen,
  onClose,
  onSave,
  editingCard,
  projectId,
}) => {
  const [formData, setFormData] = useState({
    category: "instruction",
    title: "",
    description: "",
    prompt_text: "",
    model: "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    temperature: 0.7,
    enabled: true,
  });

  useEffect(() => {
    if (editingCard) {
      setFormData({
        category: editingCard.category,
        title: editingCard.title || "",
        description: editingCard.description || "",
        prompt_text: editingCard.prompt_text || "",
        model: editingCard.model,
        temperature: editingCard.temperature,
        enabled: editingCard.enabled,
      });
    } else {
      setFormData({
        category: "instruction",
        title: "",
        description: "",
        prompt_text: "",
        model: "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        temperature: 0.7,
        enabled: true,
      });
    }
  }, [editingCard]);

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!formData.prompt_text.trim()) {
      toast.error("프롬프트 내용을 입력해주세요.");
      return;
    }

    if (editingCard) {
      onSave(editingCard.promptId, formData);
    } else {
      onSave(formData);
    }
  };

  const selectedCategory = PROMPT_CARD_CATEGORIES.find(
    (cat) => cat.id === formData.category
  );
  const selectedModel = AVAILABLE_MODELS.find(
    (model) => model.id === formData.model
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit}>
          {/* 모달 헤더 */}
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {editingCard ? "프롬프트 카드 수정" : "새 프롬프트 카드"}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              AI가 제목을 생성할 때 사용할 프롬프트를 설정합니다
            </p>
          </div>

          {/* 모달 본문 */}
          <div className="px-6 py-4 space-y-6">
            {/* 카테고리 정보 표시 */}
            {selectedCategory && (
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-lg">{selectedCategory.icon}</span>
                  <h4 className="font-medium text-blue-900 dark:text-blue-100">
                    {selectedCategory.name}
                  </h4>
                </div>
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  {selectedCategory.description}
                </p>
              </div>
            )}

            {/* 기본 정보 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  카테고리 *
                </label>
                <select
                  value={formData.category}
                  onChange={(e) =>
                    setFormData({ ...formData, category: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  required
                >
                  {PROMPT_CARD_CATEGORIES.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.icon} {category.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  AI 모델 *
                </label>
                <select
                  value={formData.model}
                  onChange={(e) =>
                    setFormData({ ...formData, model: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  required
                >
                  {AVAILABLE_MODELS.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))}
                </select>
                {selectedModel && (
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {selectedModel.description}
                  </p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  제목
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) =>
                    setFormData({ ...formData, title: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="카드 제목을 입력하세요"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  창의성 (Temperature): {formData.temperature}
                </label>
                <div className="space-y-2">
                  <div className="flex items-center space-x-4">
                    <span className="text-xs text-gray-500 dark:text-gray-400 min-w-[50px]">
                      보수적
                    </span>
                    <div className="flex-1 relative">
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={formData.temperature}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            temperature: parseFloat(e.target.value),
                          })
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
                          width: 18px;
                          height: 18px;
                          border-radius: 50%;
                          background: linear-gradient(135deg, #3b82f6, #f97316);
                          cursor: pointer;
                          border: 2px solid white;
                          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                        }
                        input[type="range"]::-moz-range-thumb {
                          width: 18px;
                          height: 18px;
                          border-radius: 50%;
                          background: linear-gradient(135deg, #3b82f6, #f97316);
                          cursor: pointer;
                          border: 2px solid white;
                          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                        }
                      `}</style>
                    </div>
                    <span className="text-xs text-gray-500 dark:text-gray-400 min-w-[50px]">
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
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                설명
              </label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                placeholder="카드 설명을 입력하세요"
              />
            </div>

            {/* 프롬프트 내용 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                프롬프트 내용 *
              </label>
              <textarea
                value={formData.prompt_text}
                onChange={(e) =>
                  setFormData({ ...formData, prompt_text: e.target.value })
                }
                rows={12}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                placeholder="프롬프트 내용을 입력하세요..."
                required
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                현재 {formData.prompt_text.length}자 입력됨
              </p>
            </div>

            {/* 활성화 체크박스 */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="enabled"
                checked={formData.enabled}
                onChange={(e) =>
                  setFormData({ ...formData, enabled: e.target.checked })
                }
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 rounded"
              />
              <label
                htmlFor="enabled"
                className="ml-2 text-sm text-gray-700 dark:text-gray-300"
              >
                카드 활성화 (체크 해제 시 제목 생성에 사용되지 않습니다)
              </label>
            </div>
          </div>

          {/* 모달 푸터 */}
          <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              취소
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors font-medium"
            >
              {editingCard ? "수정 완료" : "카드 생성"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PromptCardManager;
