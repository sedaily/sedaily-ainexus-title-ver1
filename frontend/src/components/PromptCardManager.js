import React, { useState, useEffect, useCallback } from "react";
import { toast } from "react-hot-toast";
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  EyeIcon,
  EyeSlashIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  Cog6ToothIcon,
  DocumentTextIcon,
  SparklesIcon,
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
      const response = await promptCardAPI.getPromptCards(projectId, true, true);
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
      toast.success(enabled ? "카드가 활성화되었습니다!" : "카드가 비활성화되었습니다!");
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
    return PROMPT_CARD_CATEGORIES.find((cat) => cat.id === categoryId) || {
      name: "알 수 없음",
      color: "gray",
      icon: "❓",
    };
  };

  // 모델 정보 가져오기
  const getModelInfo = (modelId) => {
    return AVAILABLE_MODELS.find((model) => model.id === modelId) || {
      name: "알 수 없는 모델",
    };
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">프롬프트 카드 관리</h2>
          <p className="text-gray-600 mt-1">
            드래그 앤 드롭으로 순서를 변경하고, 각 단계별 프롬프트를 설정하세요.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          새 카드 추가
        </button>
      </div>

      {/* 프롬프트 카드 목록 */}
      {promptCards.length === 0 ? (
        <div className="text-center py-12">
          <DocumentTextIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            프롬프트 카드가 없습니다
          </h3>
          <p className="text-gray-600 mb-6">
            첫 번째 프롬프트 카드를 추가해보세요.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center mx-auto px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            첫 카드 만들기
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {promptCards.map((card, index) => {
            const categoryInfo = getCategoryInfo(card.category);
            const modelInfo = getModelInfo(card.model);

            return (
              <div
                key={card.promptId}
                draggable
                onDragStart={(e) => handleDragStart(e, card)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, index)}
                className={`bg-white rounded-lg border-2 transition-all duration-200 cursor-move ${
                  dragOverIndex === index
                    ? "border-blue-500 shadow-lg"
                    : "border-gray-200 hover:border-gray-300"
                } ${
                  draggedCard?.promptId === card.promptId
                    ? "opacity-50 scale-95"
                    : ""
                } ${!card.enabled ? "opacity-60" : ""}`}
              >
                <div className="p-6">
                  {/* 카드 헤더 */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      <div className="flex items-center space-x-2">
                        <span className="text-lg">{categoryInfo.icon}</span>
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-${categoryInfo.color}-100 text-${categoryInfo.color}-800`}
                        >
                          Step {card.stepOrder}
                        </span>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          {card.title || `${categoryInfo.name} 단계`}
                        </h3>
                        <p className="text-sm text-gray-600">
                          {card.description || categoryInfo.description}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {/* 활성/비활성 토글 */}
                      <button
                        onClick={() =>
                          handleToggleCard(card.promptId, !card.enabled)
                        }
                        className={`p-2 rounded-lg transition-colors ${
                          card.enabled
                            ? "text-green-600 hover:bg-green-50"
                            : "text-gray-400 hover:bg-gray-50"
                        }`}
                        title={card.enabled ? "비활성화" : "활성화"}
                      >
                        {card.enabled ? (
                          <EyeIcon className="h-5 w-5" />
                        ) : (
                          <EyeSlashIcon className="h-5 w-5" />
                        )}
                      </button>

                      {/* 수정 버튼 */}
                      <button
                        onClick={() => setEditingCard(card)}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="수정"
                      >
                        <PencilIcon className="h-5 w-5" />
                      </button>

                      {/* 삭제 버튼 */}
                      <button
                        onClick={() => handleDeleteCard(card.promptId)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="삭제"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </div>

                  {/* 카드 설정 정보 */}
                  <div className="flex items-center space-x-4 mb-4">
                    <div className="flex items-center space-x-1 text-sm text-gray-600">
                      <SparklesIcon className="h-4 w-4" />
                      <span>{modelInfo.name}</span>
                    </div>
                    <div className="flex items-center space-x-1 text-sm text-gray-600">
                      <Cog6ToothIcon className="h-4 w-4" />
                      <span>Temperature: {card.temperature}</span>
                    </div>
                  </div>

                  {/* 프롬프트 내용 미리보기 */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-sm text-gray-700">
                      {card.prompt_text ? (
                        card.prompt_text.length > 200 ? (
                          <>
                            {card.prompt_text.substring(0, 200)}...
                            <button
                              onClick={() => setEditingCard(card)}
                              className="text-blue-600 hover:underline ml-1"
                            >
                              더보기
                            </button>
                          </>
                        ) : (
                          card.prompt_text
                        )
                      ) : (
                        <span className="text-gray-400 italic">
                          프롬프트 내용이 없습니다.
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
const PromptCardModal = ({ isOpen, onClose, onSave, editingCard, projectId }) => {
  const [formData, setFormData] = useState({
    category: "instruction",
    title: "",
    description: "",
    prompt_text: "",
    model: "anthropic.claude-3-5-sonnet-20241022-v2:0",
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
        model: "anthropic.claude-3-5-sonnet-20241022-v2:0",
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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit}>
          {/* 모달 헤더 */}
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">
              {editingCard ? "프롬프트 카드 수정" : "새 프롬프트 카드"}
            </h3>
          </div>

          {/* 모달 본문 */}
          <div className="px-6 py-4 space-y-6">
            {/* 기본 정보 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  카테고리
                </label>
                <select
                  value={formData.category}
                  onChange={(e) =>
                    setFormData({ ...formData, category: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  AI 모델
                </label>
                <select
                  value={formData.model}
                  onChange={(e) =>
                    setFormData({ ...formData, model: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  {AVAILABLE_MODELS.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  제목
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) =>
                    setFormData({ ...formData, title: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="카드 제목을 입력하세요"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Temperature (0.0 - 1.0)
                </label>
                <input
                  type="number"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                설명
              </label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="카드 설명을 입력하세요"
              />
            </div>

            {/* 프롬프트 내용 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                프롬프트 내용 *
              </label>
              <textarea
                value={formData.prompt_text}
                onChange={(e) =>
                  setFormData({ ...formData, prompt_text: e.target.value })
                }
                rows={12}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="프롬프트 내용을 입력하세요..."
                required
              />
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
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="enabled" className="ml-2 text-sm text-gray-700">
                카드 활성화
              </label>
            </div>
          </div>

          {/* 모달 푸터 */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              취소
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              {editingCard ? "수정" : "생성"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PromptCardManager;