import React, { useState, useEffect, useCallback } from "react";
import { toast } from "react-hot-toast";
import { PlusIcon, Bars3Icon, ChatBubbleLeftRightIcon, TrashIcon } from "@heroicons/react/24/outline";
import { promptCardAPI, handleAPIError } from "../services/api";
import ChatInterface from "./ChatInterface";
import PromptCard from "./prompts/PromptCard";
import PromptEditForm from "./prompts/PromptEditForm";
import { SidebarSkeleton } from "./SkeletonLoader";

// AI 워크플로우 기반 프롬프트 템플릿
const FIXED_PROMPT_CATEGORIES = [
  {
    id: "instruction", 
    name: "역할 및 목표",
    order: 1,
    color: "bg-slate-100/80 text-slate-700 border-slate-200/80",
    icon: "",
    description: "AI의 역할, 정체성, 핵심 목표를 명확히 정의합니다",
    defaultContent: "당신은 전문적인 기사 제목 생성 AI입니다.\n목표: 독자의 관심을 끌고 정확한 정보를 전달하는 제목 생성",
    placeholder: "AI의 역할과 주요 목표를 구체적으로 작성하세요...",
  },
  {
    id: "knowledge",
    name: "지식 베이스", 
    order: 2,
    color: "bg-slate-100/80 text-slate-700 border-slate-200/80",
    icon: "",
    description: "작업 수행에 필요한 핵심 지식과 원칙을 제공합니다",
    defaultContent: "제목 작성 원칙:\n- 간결하고 명확한 표현\n- 핵심 키워드 포함\n- 독자의 관심 유발",
    placeholder: "작업에 필요한 핵심 지식과 원칙을 작성하세요...",
  },
  {
    id: "secondary",
    name: "CoT (사고 과정)",
    order: 3, 
    color: "bg-slate-100/80 text-slate-700 border-slate-200/80",
    icon: "",
    description: "단계별 추론 과정을 통해 사고의 투명성을 확보합니다",
    defaultContent: "다음 단계로 사고하세요:\n1. 기사의 핵심 내용 파악\n2. 주요 키워드 추출\n3. 독자 관점에서 흥미도 평가\n4. 제목 후보 생성\n5. 최적 제목 선택",
    placeholder: "단계별 사고 과정을 구체적으로 작성하세요...",
    isCoT: true,
  },
  {
    id: "style_guide",
    name: "스타일 가이드",
    order: 4,
    color: "bg-slate-100/80 text-slate-700 border-slate-200/80", 
    icon: "",
    description: "일관된 스타일과 형식을 유지하기 위한 가이드라인",
    defaultContent: "스타일 요구사항:\n- 길이: 15-25자 권장\n- 톤: 전문적이면서 친근\n- 형식: 명사형 종결",
    placeholder: "스타일과 형식 요구사항을 작성하세요...",
  },
  {
    id: "validation", 
    name: "ReAct (추론+행동)",
    order: 5,
    color: "bg-slate-100/80 text-slate-700 border-slate-200/80",
    icon: "",
    description: "추론과 행동을 결합하여 더 정확한 결과를 도출합니다",
    defaultContent: "Thought: 이 기사의 핵심은 무엇인가?\nAction: 키워드를 추출하고 중요도를 평가한다\nObservation: 추출된 정보를 바탕으로 제목을 구성한다\nThought: 생성된 제목이 요구사항을 충족하는가?\nAction: 필요시 수정하고 최종 검증한다",
    placeholder: "Thought/Action/Observation 패턴으로 작성하세요...",
    isReAct: true,
  },
  {
    id: "enhancement",
    name: "품질 검증",
    order: 6,
    color: "bg-slate-100/80 text-slate-700 border-slate-200/80",
    icon: "",
    description: "최종 결과물의 품질을 검증하고 개선합니다",
    defaultContent: "품질 검증 기준:\n- 정확성: 기사 내용과 일치\n- 매력도: 독자 관심 유발\n- 적절성: 매체 성격에 부합\n- 완성도: 문법과 표현의 정확성",
    placeholder: "품질 검증 기준과 개선 방안을 작성하세요...",
  },
];

// 프롬프트 편집 모달
const PromptEditModal = ({ isOpen, onSubmit, onCancel, initialData }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-lg max-h-[80vh] overflow-y-auto">
        <PromptEditForm
          onSubmit={onSubmit}
          onCancel={onCancel}
          initialData={initialData}
          isModal={true}
        />
      </div>
    </div>
  );
};

const PromptCardManager = ({ projectId, onCardsChanged, projectName }) => {
  // 상태 관리
  const [promptCards, setPromptCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingCard, setEditingCard] = useState(null);
  const [savedChats, setSavedChats] = useState([]);
  const [showSavedChats, setShowSavedChats] = useState(false);

  // 프롬프트 카드 로드 및 기본 템플릿 생성
  const loadPromptCards = useCallback(async () => {
    try {
      setLoading(true);
      const response = await promptCardAPI.getPromptCards(projectId);

      // API 응답 구조 확인 및 안전한 처리
      let cards = [];
      if (Array.isArray(response)) {
        cards = response;
      } else if (response && Array.isArray(response.promptCards)) {
        cards = response.promptCards;
      } else if (response && Array.isArray(response.data)) {
        cards = response.data;
      } else {
        console.warn("Unexpected API response structure:", response);
        cards = [];
      }

      // 고정된 템플릿 카드들과 기존 카드들을 매칭
      const templateCards = FIXED_PROMPT_CATEGORIES.map((template) => {
        const existingCard = cards.find(
          (card) => card.category === template.id
        );

        if (existingCard) {
          // 기존 카드가 있으면 해당 카드 사용
          return {
            ...existingCard,
            ...template, // 템플릿 정보로 덮어쓰기 (name, order, color, description)
            title: existingCard.title || `${template.name} 프롬프트`,
            prompt_text: existingCard.prompt_text || template.defaultContent,
          };
        } else {
          // 기존 카드가 없으면 템플릿으로 기본 카드 생성
          return {
            id: `template-${template.id}`,
            promptId: `template-${template.id}`,
            title: `${template.name} 프롬프트`,
            category: template.id,
            prompt_text: template.defaultContent,
            model_name: "claude-3-5-sonnet-20241022",
            temperature: 0.7,
            enabled: true,
            step_order: template.order,
            isTemplate: true, // 템플릿 카드임을 표시
            ...template,
          };
        }
      });

      // 순서대로 정렬
      templateCards.sort((a, b) => (a.order || 999) - (b.order || 999));

      setPromptCards(templateCards);
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`프롬프트 카드 로딩 실패: ${errorInfo.message}`);

      // 오류 시에도 기본 템플릿 카드들 표시
      const defaultCards = FIXED_PROMPT_CATEGORIES.map((template) => ({
        id: `template-${template.id}`,
        promptId: `template-${template.id}`,
        title: `${template.name} 프롬프트`,
        category: template.id,
        prompt_text: template.defaultContent,
        model_name: "claude-3-5-sonnet-20241022",
        temperature: 0.7,
        enabled: true,
        step_order: template.order,
        isTemplate: true,
        ...template,
      }));

      setPromptCards(defaultCards);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadPromptCards();
    // 저장된 대화 로드
    const existingChats = JSON.parse(localStorage.getItem('savedChats') || '[]');
    setSavedChats(existingChats.filter(chat => chat.projectId === projectId));
  }, [loadPromptCards, projectId]);

  // 카드 업데이트
  const handleUpdateCard = async (cardData) => {
    try {
      if (editingCard && !editingCard.isTemplate) {
        // 기존 카드 편집 - 기존 정보 유지
        const updateData = {
          ...cardData,
          category: editingCard.category,
          title: editingCard.title,
          step_order: editingCard.step_order || editingCard.order,
        };
        await promptCardAPI.updatePromptCard(
          projectId,
          editingCard.promptId || editingCard.id,
          updateData
        );
        toast.success("프롬프트 카드가 수정되었습니다!");
      } else if (editingCard && editingCard.isTemplate) {
        // 템플릿 카드를 실제 카드로 생성
        const newCardData = {
          ...cardData,
          category: editingCard.category,
          title: editingCard.title,
          step_order: editingCard.order,
        };
        await promptCardAPI.createPromptCard(projectId, newCardData);
        toast.success("프롬프트 카드가 생성되었습니다!");
      } else {
        // 새 카드 생성
        const newCardData = {
          ...cardData,
          category: "instruction", // 기본 카테고리
          title: "새 프롬프트 카드",
          step_order: 1,
        };
        await promptCardAPI.createPromptCard(projectId, newCardData);
        toast.success("프롬프트 카드가 생성되었습니다!");
      }

      await loadPromptCards();
      setShowForm(false);
      setEditingCard(null);

      if (onCardsChanged) onCardsChanged();
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(
        `카드 ${editingCard ? "수정" : "생성"} 실패: ${errorInfo.message}`
      );
    }
  };

  // 카드 토글 (최적화 UI)
  const handleToggleCard = async (promptId, enabled) => {
    // promptCards가 배열인지 확인
    if (!Array.isArray(promptCards)) {
      console.error("promptCards is not an array:", promptCards);
      return;
    }

    // 낙관적 업데이트: 즉시 UI 반영
    const originalCards = [...promptCards];
    const updatedCards = promptCards.map((card) =>
      (card.promptId || card.id) === promptId ? { ...card, enabled } : card
    );
    setPromptCards(updatedCards);

    try {
      // 템플릿 카드가 아닌 경우에만 API 호출
      const card = promptCards.find((c) => (c.promptId || c.id) === promptId);
      if (card && !card.isTemplate) {
        await promptCardAPI.updatePromptCard(projectId, promptId, { enabled });
      }
      if (onCardsChanged) onCardsChanged();
    } catch (error) {
      // 실패 시 복원
      setPromptCards(originalCards);
      const errorInfo = handleAPIError(error);
      toast.error(`카드 상태 변경 실패: ${errorInfo.message}`);
    }
  };

  // 카드 삭제 또는 초기화
  const handleDeleteCard = async (promptId) => {
    const card = promptCards.find((c) => (c.promptId || c.id) === promptId);

    if (card && card.isTemplate) {
      if (!window.confirm("이 프롬프트를 기본값으로 초기화하시겠습니까?")) {
        return;
      }
      // 템플릿 카드는 기본값으로 초기화
      const template = FIXED_PROMPT_CATEGORIES.find(t => t.id === card.category);
      if (template) {
        const updatedCards = promptCards.map(c => 
          (c.promptId || c.id) === promptId 
            ? { ...c, prompt_text: template.defaultContent }
            : c
        );
        setPromptCards(updatedCards);
        toast.success("프롬프트가 기본값으로 초기화되었습니다!");
      }
      return;
    }

    if (!window.confirm("정말로 이 프롬프트 카드를 삭제하시겠습니까?")) {
      return;
    }

    try {
      await promptCardAPI.deletePromptCard(projectId, promptId);
      await loadPromptCards();
      toast.success("프롬프트 카드가 삭제되었습니다!");
      if (onCardsChanged) onCardsChanged();
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`카드 삭제 실패: ${errorInfo.message}`);
    }
  };

  // 편집 모드 시작
  const handleEditCard = (card) => {
    setEditingCard(card);
    setShowForm(true);
  };

  // 폼 취소
  const handleCancelForm = () => {
    setShowForm(false);
    setEditingCard(null);
  };

  // 저장된 대화 삭제
  const deleteSavedChat = (chatId) => {
    if (window.confirm('저장된 대화를 삭제하시겠습니까?')) {
      const existingChats = JSON.parse(localStorage.getItem('savedChats') || '[]');
      const updatedChats = existingChats.filter(chat => chat.id !== chatId);
      localStorage.setItem('savedChats', JSON.stringify(updatedChats));
      setSavedChats(updatedChats.filter(chat => chat.projectId === projectId));
    }
  };

  // promptCards가 배열인지 확인하고 안전하게 처리
  const safePromptCards = Array.isArray(promptCards) ? promptCards : [];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* 메인 콘텐츠 - 채팅 인터페이스 */}
      <div className="flex-1 min-w-0 relative p-3 lg:pr-2">
        {/* 우측 상단 메뉴 버튼 (모바일용) */}
        <div className="absolute top-6 right-6 z-10 lg:hidden">
          <button className="p-3 text-slate-500 hover:text-slate-700 hover:bg-white/80 hover:shadow-lg rounded-xl backdrop-blur-sm transition-all duration-300">
            <Bars3Icon className="h-5 w-5" />
          </button>
        </div>

        <div className="h-full bg-white rounded-lg border border-gray-200 overflow-hidden">
          <ChatInterface
            projectId={projectId}
            projectName={projectName}
            promptCards={safePromptCards}
          />
        </div>
      </div>

      {/* 우측 사이드바 */}
      <div className="w-[350px] flex flex-col hidden lg:flex p-3 pl-2">
        <div className="h-full bg-white rounded-lg border border-gray-200 flex flex-col overflow-hidden">
          {/* 사이드바 헤더 */}
          <div className="flex-shrink-0 p-3 border-b border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setShowSavedChats(false)}
                  className={`text-sm font-medium transition-colors ${
                    !showSavedChats ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  프롬프트
                </button>
                <button
                  onClick={() => setShowSavedChats(true)}
                  className={`text-sm font-medium transition-colors flex items-center gap-1 ${
                    showSavedChats ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <ChatBubbleLeftRightIcon className="h-4 w-4" />
                  대화 기록
                </button>
              </div>
              {!showSavedChats && (
                <div className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                  {safePromptCards.filter((card) => card.enabled).length}/{safePromptCards.length}
                </div>
              )}
            </div>
            <p className="text-xs text-gray-600">
              {showSavedChats ? '저장된 대화 기록을 확인하세요' : '각 카테고0리별 프롬프트를 설정하세요'}
            </p>
          </div>

          {/* 콘텐츠 영역 */}
          <div className="flex-1 overflow-y-auto p-3">
            {!showSavedChats ? (
              // 프롬프트 카드 목록
              loading ? (
                <SidebarSkeleton />
              ) : (
                <div className="space-y-2">
                  {safePromptCards.map((card, index) => (
                    <PromptCard
                      key={card.promptId || card.id || index}
                      card={card}
                      onEdit={handleEditCard}
                      onToggle={handleToggleCard}
                      onDelete={handleDeleteCard}
                      stepNumber={index + 1}
                      hideDeleteButton={card.isTemplate ? false : false}
                    />
                  ))}
                </div>
              )
            ) : (
              // 저장된 대화 목록
              <div className="space-y-2">
                {savedChats.length === 0 ? (
                  <div className="text-center py-8">
                    <ChatBubbleLeftRightIcon className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-sm text-gray-500">저장된 대화가 없습니다</p>
                    <p className="text-xs text-gray-400 mt-1">대화창에서 '저장' 버튼을 눌러주세요</p>
                  </div>
                ) : (
                  savedChats.map((chat) => (
                    <div
                      key={chat.id}
                      className="bg-white border border-gray-200 rounded-lg p-3 hover:border-gray-300 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-medium text-gray-900 truncate">
                            {chat.title}
                          </h4>
                          <p className="text-xs text-gray-500 mt-1">
                            {new Date(chat.timestamp).toLocaleString()}
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            {chat.messages.length}개 메시지
                          </p>
                        </div>
                        <button
                          onClick={() => deleteSavedChat(chat.id)}
                          className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                          title="삭제"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* 하단 정보 */}
          <div className="flex-shrink-0 p-3 border-t border-gray-200 bg-gray-50">
            <div className="text-xs text-gray-600">
              {!showSavedChats ? (
                <>
                  <p className="font-medium mb-1">고정 템플릿 시스템</p>
                  <p>체계적인 프롬프트 관리가 가능합니다.</p>
                </>
              ) : (
                <>
                  <p className="font-medium mb-1">대화 기록 관리</p>
                  <p>최대 10개의 대화가 저장됩니다.</p>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 편집 모달 */}
      <PromptEditModal
        isOpen={showForm}
        onSubmit={handleUpdateCard}
        onCancel={handleCancelForm}
        initialData={editingCard}
      />
    </div>
  );
};

export default PromptCardManager;
