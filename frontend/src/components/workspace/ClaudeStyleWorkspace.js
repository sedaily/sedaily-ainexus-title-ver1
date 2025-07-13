import React, { useState, useEffect, useCallback, useRef } from "react";
import { toast } from "react-hot-toast";
import {
  PaperAirplaneIcon,
  ArrowPathIcon,
  DocumentDuplicateIcon,
  PlusIcon,
  BookOpenIcon,
  Cog6ToothIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XMarkIcon,
  CloudArrowUpIcon,
  DocumentTextIcon,
  TrashIcon,
  PencilIcon,
  Bars3Icon,
  EllipsisVerticalIcon,
  AdjustmentsHorizontalIcon,
} from "@heroicons/react/24/outline";
import { orchestrationAPI, promptCardAPI } from "../../services/api";

// 메시지 컴포넌트
const Message = ({ message, onCopy }) => {
  const isUser = message.type === "user";

  return (
    <div className={`group relative ${isUser ? "ml-12" : "mr-12"} mb-6`}>
      <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
        <div
          className={`
          max-w-[80%] rounded-lg px-4 py-3 relative shadow-sm
          ${
            isUser
              ? "bg-blue-600 text-white"
              : "bg-white text-gray-800 border border-gray-200"
          }
        `}
        >
          {/* 메시지 내용 */}
          <div className="whitespace-pre-wrap text-sm leading-relaxed">
            {message.content}
          </div>

          {/* 제목 복사 버튼들 */}
          {message.titles && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="flex flex-wrap gap-2">
                {message.titles.map((title, index) => (
                  <button
                    key={index}
                    onClick={() => onCopy(title)}
                    className="flex items-center px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-xs text-gray-700 transition-colors"
                  >
                    <DocumentDuplicateIcon className="h-3 w-3 mr-1" />
                    제목 {index + 1} 복사
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 타임스탬프 */}
          <div
            className={`text-xs mt-2 ${
              isUser ? "text-blue-100" : "text-gray-500"
            }`}
          >
            {message.timestamp.toLocaleTimeString("ko-KR", {
              hour: "numeric",
              minute: "2-digit",
            })}
          </div>

          {/* 로딩 상태 */}
          {message.isLoading && (
            <div className="flex items-center text-blue-600 mt-2">
              <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />
              <span className="text-sm">AI가 응답을 생성하고 있습니다...</span>
            </div>
          )}

          {/* 에러 상태 */}
          {message.isError && (
            <div className="flex items-center text-red-600 mt-2">
              <ExclamationTriangleIcon className="h-4 w-4 mr-2" />
              <span className="text-sm">오류가 발생했습니다</span>
            </div>
          )}
        </div>
      </div>

      {/* 사용자 아바타 */}
      {isUser && (
        <div className="absolute top-0 right-0 -mr-10 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-sm text-white font-medium">
          U
        </div>
      )}

      {/* AI 아바타 */}
      {!isUser && (
        <div className="absolute top-0 left-0 -ml-10 w-8 h-8 bg-green-600 rounded-full flex items-center justify-center text-sm text-white font-medium">
          AI
        </div>
      )}
    </div>
  );
};

// 파일 업로드 컴포넌트
const FileUploadArea = ({ projectId, onFileUploaded }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    handleFileUpload(files);
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    handleFileUpload(files);
  };

  const handleFileUpload = async (files) => {
    if (!files.length) return;

    setUploading(true);
    try {
      for (const file of files) {
        // TODO: S3 업로드 및 벡터 임베딩 API 호출
        toast.success(`${file.name} 업로드 완료`);
      }
      onFileUploaded?.();
    } catch (error) {
      console.error("파일 업로드 실패:", error);
      toast.error("파일 업로드에 실패했습니다");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div
      className={`
        border-2 border-dashed rounded-lg p-4 text-center transition-colors
        ${
          isDragging
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 hover:border-gray-400"
        }
      `}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".txt,.md,.pdf,.doc,.docx"
        onChange={handleFileSelect}
        className="hidden"
      />

      <CloudArrowUpIcon className="h-8 w-8 text-gray-400 mx-auto mb-3" />

      {uploading ? (
        <div className="text-blue-600">
          <ArrowPathIcon className="h-4 w-4 animate-spin mx-auto mb-2" />
          <p className="text-xs">업로드 중...</p>
        </div>
      ) : (
        <>
          <p className="text-gray-600 mb-2 text-xs">파일을 드래그하거나</p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="text-blue-600 hover:text-blue-800 font-medium text-xs"
          >
            기기에서 선택
          </button>
          <p className="text-xs text-gray-500 mt-1">txt, md, pdf, doc, docx</p>
        </>
      )}
    </div>
  );
};

// 프롬프트 카드 편집 모달
const PromptCardEditModal = ({ card, isOpen, onClose, onSave }) => {
  const [title, setTitle] = useState(card?.title || "");
  const [content, setContent] = useState(card?.content || "");
  const [temperature, setTemperature] = useState(card?.temperature || 0.7);

  useEffect(() => {
    if (card) {
      setTitle(card.title || "");
      setContent(card.content || "");
      setTemperature(card.temperature || 0.7);
    }
  }, [card]);

  const handleSave = () => {
    onSave({
      ...card,
      title,
      content,
      temperature,
    });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            프롬프트 카드 편집
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="p-4 space-y-4 overflow-y-auto max-h-[60vh]">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              제목
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="프롬프트 카드 제목"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Temperature: {temperature}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>정확 (0.0)</span>
              <span>창의적 (1.0)</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              프롬프트 내용
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={12}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="프롬프트 내용을 입력하세요..."
            />
          </div>
        </div>

        <div className="flex items-center justify-end space-x-3 p-4 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            취소
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors"
          >
            저장
          </button>
        </div>
      </div>
    </div>
  );
};

// 통합 사이드바 컴포넌트
const IntegratedSidebar = ({
  projectId,
  promptCards,
  onCardsChanged,
  isOpen,
  onClose,
}) => {
  const [loading, setLoading] = useState(false);
  const [editingCard, setEditingCard] = useState(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  const handleCardToggle = async (cardId, enabled) => {
    try {
      setLoading(true);
      await promptCardAPI.updatePromptCard(projectId, cardId, { enabled });
      onCardsChanged?.();
      toast.success(
        enabled ? "카드가 활성화되었습니다" : "카드가 비활성화되었습니다"
      );
    } catch (error) {
      console.error("카드 상태 변경 실패:", error);
      toast.error("카드 상태 변경에 실패했습니다");
    } finally {
      setLoading(false);
    }
  };

  const handleEditCard = (card) => {
    setEditingCard(card);
    setIsEditModalOpen(true);
  };

  const handleSaveCard = async (updatedCard) => {
    try {
      await promptCardAPI.updatePromptCard(
        projectId,
        updatedCard.id,
        updatedCard
      );
      onCardsChanged?.();
      toast.success("프롬프트 카드가 수정되었습니다");
    } catch (error) {
      console.error("카드 수정 실패:", error);
      toast.error("카드 수정에 실패했습니다");
    }
  };

  const handleFileUploaded = () => {
    toast.success("파일이 프로젝트 지식에 추가되었습니다");
  };

  const handleTextSubmit = (textData) => {
    console.log("텍스트 추가:", textData);
  };

  const categorizedCards = promptCards.reduce((acc, card) => {
    const category = card.category || "other";
    if (!acc[category]) acc[category] = [];
    acc[category].push(card);
    return acc;
  }, {});

  const categoryNames = {
    role: "역할 정의",
    guideline: "작성 가이드라인",
    workflow: "워크플로우",
    output_format: "출력 형식",
    few_shot: "예시 템플릿",
    scoring: "품질 평가",
    other: "기타 설정",
  };

  return (
    <>
      <div
        className={`
        relative h-full w-96 bg-white border-l border-gray-200 shadow-sm flex flex-col
        ${!isOpen && "hidden md:flex"}
      `}
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
          <div className="flex items-center space-x-2">
            <AdjustmentsHorizontalIcon className="h-5 w-5 text-gray-600" />
            <h3 className="text-sm font-semibold text-gray-900">
              프로젝트 설정
            </h3>
          </div>
          <button
            onClick={onClose}
            className="md:hidden p-1 text-gray-400 hover:text-gray-600 rounded"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {/* 지식 업로드 섹션 */}
          <div className="p-4 border-b border-gray-100">
            <h4 className="text-sm font-medium text-gray-900 mb-3">
              프로젝트 지식 관리
            </h4>

            {/* 컴팩트한 업로드 영역 */}
            <div className="space-y-3">
              <FileUploadArea
                projectId={projectId}
                onFileUploaded={handleFileUploaded}
              />

              {/* 지식 목록 (컴팩트하게) */}
              <div className="space-y-1">
                <div className="text-xs text-gray-500 mb-2">
                  업로드된 지식 (4개)
                </div>
                {[
                  { id: 1, title: "서울경제 스타일 가이드", size: "189자" },
                  { id: 2, title: "NotebookLM TTS 가이드", size: "262자" },
                  { id: 3, title: "Korea-France Cultural", size: "227자" },
                  { id: 4, title: "Script Français", size: "189자" },
                ].map((item) => (
                  <div
                    key={`knowledge-${item.id}`}
                    className="flex items-center justify-between p-2 bg-gray-50 rounded text-xs"
                  >
                    <span className="truncate flex-1 text-gray-700">
                      {item.title}
                    </span>
                    <div className="flex items-center space-x-1 ml-2">
                      <span className="text-gray-500">{item.size}</span>
                      <button className="text-gray-400 hover:text-red-600">
                        <TrashIcon className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 프롬프트 카드 섹션 */}
          <div className="p-4">
            {/* 상태 표시 */}
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-sm font-medium text-gray-900">
                프롬프트 카드
              </h4>
              <div className="text-xs text-gray-500">
                {promptCards.filter((c) => c.enabled).length}/
                {promptCards.length} 활성
              </div>
            </div>

            {/* 프롬프트 카드 목록 */}
            <div className="space-y-3">
              {Object.entries(categorizedCards).map(([category, cards]) => (
                <div key={`category-${category}`}>
                  <h5 className="text-xs font-medium text-gray-700 uppercase tracking-wider mb-2">
                    {categoryNames[category] || category}
                  </h5>
                  <div className="space-y-2">
                    {cards.map((card) => (
                      <div
                        key={`card-${card.id || card.promptId}`}
                        className={`
                          group p-3 rounded-lg border transition-all duration-200 relative
                          ${
                            card.enabled
                              ? "border-blue-300 bg-blue-50"
                              : "border-gray-200 bg-white hover:bg-gray-50"
                          }
                        `}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2 mb-1">
                              <h6 className="text-sm font-medium text-gray-900 truncate">
                                {card.title}
                              </h6>
                              {card.enabled && (
                                <CheckCircleIcon className="h-3 w-3 text-green-500 flex-shrink-0" />
                              )}
                            </div>
                            <div className="text-xs text-gray-500">
                              Temperature: {card.temperature || 0.7} •{" "}
                              {card.model_name || "Claude"}
                            </div>
                          </div>

                          {/* 카드 액션 버튼들 */}
                          <div className="flex items-center space-x-1">
                            <button
                              onClick={() => handleEditCard(card)}
                              className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-blue-600 rounded transition-all"
                            >
                              <EllipsisVerticalIcon className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() =>
                                handleCardToggle(
                                  card.id || card.promptId,
                                  !card.enabled
                                )
                              }
                              disabled={loading}
                              className={`
                                w-8 h-4 rounded-full transition-colors duration-200 focus:outline-none relative
                                ${card.enabled ? "bg-blue-600" : "bg-gray-300"}
                                ${
                                  loading
                                    ? "opacity-50 cursor-not-allowed"
                                    : "cursor-pointer"
                                }
                              `}
                            >
                              <div
                                className={`
                                w-3 h-3 bg-white rounded-full shadow transform transition-transform duration-200 absolute top-0.5
                                ${
                                  card.enabled
                                    ? "translate-x-4"
                                    : "translate-x-0.5"
                                }
                              `}
                              />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {promptCards.length === 0 && (
              <div className="text-center py-6">
                <BookOpenIcon className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-500 text-sm">
                  프롬프트 카드가 없습니다
                </p>
              </div>
            )}
          </div>
        </div>

        {/* 하단 액션 */}
        <div className="p-4 border-t border-gray-200 bg-white">
          <button className="w-full flex items-center justify-center px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm text-white transition-colors">
            <PlusIcon className="h-4 w-4 mr-2" />새 프롬프트 카드 추가
          </button>
        </div>
      </div>

      {/* 편집 모달 */}
      <PromptCardEditModal
        card={editingCard}
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditingCard(null);
        }}
        onSave={handleSaveCard}
      />
    </>
  );
};

// 메인 워크스페이스 컴포넌트
const ClaudeStyleWorkspace = ({ projectId, projectName, onCardsChanged }) => {
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      type: "assistant",
      content: `안녕하세요! 저는 ${projectName}의 AI 제목 작가입니다. 🎯\n\n기사 내용을 입력해주시면 프롬프트 오케스트레이션을 통해 다양한 스타일의 제목을 제안해드릴게요. 오른쪽 패널에서 프로젝트 지식을 관리하고 프롬프트 카드를 설정할 수 있습니다.`,
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [promptCards, setPromptCards] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // 프롬프트 카드 로드
  const loadPromptCards = useCallback(async () => {
    try {
      const response = await promptCardAPI.getPromptCards(
        projectId,
        true,
        true
      );
      setPromptCards(response.promptCards || []);
      onCardsChanged?.(response.promptCards || []);
    } catch (error) {
      console.error("프롬프트 카드 로드 실패:", error);
      setPromptCards([]);
    }
  }, [projectId, onCardsChanged]);

  useEffect(() => {
    loadPromptCards();
  }, [loadPromptCards]);

  // 메시지 끝으로 스크롤
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 메시지 전송
  const handleSendMessage = async () => {
    if (!inputValue.trim() || isGenerating) return;

    const userMessage = {
      id: Date.now() + Math.random(),
      type: "user",
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsGenerating(true);

    try {
      // 오케스트레이션 실행
      const response = await orchestrationAPI.executeOrchestration(
        projectId,
        inputValue,
        {
          useAllSteps: true,
          enabledSteps: promptCards
            .filter((card) => card.enabled)
            .map((card) => card.category),
          maxRetries: 3,
          temperature: 0.7,
        }
      );

      // 임시 로딩 메시지
      const loadingMessage = {
        id: "loading-" + Date.now(),
        type: "assistant",
        content:
          "프롬프트 오케스트레이션을 실행하고 있습니다...\n\n각 단계별로 처리하여 최적의 제목을 생성하겠습니다.",
        timestamp: new Date(),
        isLoading: true,
      };

      setMessages((prev) => [...prev, loadingMessage]);

      // 결과 폴링
      pollOrchestrationResult(response.executionId);
    } catch (error) {
      console.error("메시지 전송 오류:", error);

      const errorMessage = {
        id: "error-" + Date.now(),
        type: "assistant",
        content:
          "죄송합니다. 제목 생성 중 오류가 발생했습니다. 다시 시도해주세요.",
        timestamp: new Date(),
        isError: true,
      };

      setMessages((prev) => [...prev, errorMessage]);
      setIsGenerating(false);
    }
  };

  // 오케스트레이션 결과 폴링
  const pollOrchestrationResult = async (executionId) => {
    const poll = async () => {
      try {
        const status = await orchestrationAPI.getOrchestrationStatus(
          projectId,
          executionId
        );

        if (status.status === "COMPLETED") {
          const result = await orchestrationAPI.getOrchestrationResult(
            projectId,
            executionId
          );

          // 최종 결과에서 제목들 추출
          const titles = result.steps
            ?.filter((step) => step.output)
            ?.map((step) => step.output)
            ?.slice(-3) || ["제목 생성 완료"];

          const responseMessage = {
            id: "response-" + Date.now(),
            type: "assistant",
            content: `✨ **프롬프트 오케스트레이션 완료!**\n\n${
              promptCards.filter((c) => c.enabled).length
            }개의 활성 프롬프트를 통해 생성된 제목 후보들입니다:\n\n${titles
              .map((title, i) => `**${i + 1}.** ${title}`)
              .join(
                "\n\n"
              )}\n\n마음에 드는 제목이 있으시거나 수정이 필요하시면 말씀해주세요!`,
            timestamp: new Date(),
            titles: titles,
          };

          // 로딩 메시지 제거하고 결과 메시지 추가
          setMessages((prev) =>
            prev.filter((msg) => !msg.isLoading).concat([responseMessage])
          );
          setIsGenerating(false);
        } else if (status.status === "FAILED") {
          throw new Error("오케스트레이션 실패");
        } else if (status.status === "RUNNING") {
          // 3초 후 다시 폴링
          setTimeout(poll, 3000);
        }
      } catch (error) {
        console.error("결과 조회 오류:", error);

        const errorMessage = {
          id: "error-" + Date.now(),
          type: "assistant",
          content: "제목 생성 중 문제가 발생했습니다. 다시 시도해주세요.",
          timestamp: new Date(),
          isError: true,
        };

        setMessages((prev) =>
          prev.filter((msg) => !msg.isLoading).concat([errorMessage])
        );
        setIsGenerating(false);
      }
    };

    poll();
  };

  // 메시지 복사
  const copyMessage = (content) => {
    navigator.clipboard.writeText(content);
    toast.success("클립보드에 복사되었습니다");
  };

  return (
    <div className="h-full flex bg-gray-50">
      {/* 메인 채팅 영역 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 채팅 메시지 영역 */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="max-w-3xl mx-auto">
            {messages.map((message) => (
              <Message
                key={message.id}
                message={message}
                onCopy={copyMessage}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* 입력 영역 */}
        <div className="border-t border-gray-200 px-6 py-4 bg-white">
          <div className="max-w-3xl mx-auto">
            <div className="relative">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder="기사 내용을 입력하거나 제목 수정 요청을 해주세요..."
                rows={3}
                className="w-full p-4 pr-12 bg-white text-gray-900 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none placeholder-gray-500"
                disabled={isGenerating}
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isGenerating}
                className={`
                  absolute bottom-3 right-3 w-8 h-8 rounded-lg flex items-center justify-center transition-all
                  ${
                    !inputValue.trim() || isGenerating
                      ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                      : "bg-blue-600 text-white hover:bg-blue-700"
                  }
                `}
              >
                {isGenerating ? (
                  <ArrowPathIcon className="h-4 w-4 animate-spin" />
                ) : (
                  <PaperAirplaneIcon className="h-4 w-4" />
                )}
              </button>
            </div>
            <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
              <span>{inputValue.length}/2000</span>
              <span>Shift + Enter로 줄바꿈, Enter로 전송</span>
            </div>
          </div>
        </div>
      </div>

      {/* 사이드바 토글 버튼 (모바일) */}
      {!sidebarOpen && (
        <button
          onClick={() => setSidebarOpen(true)}
          className="md:hidden fixed top-4 right-4 w-10 h-10 bg-blue-600 text-white rounded-lg shadow-lg z-40 flex items-center justify-center"
        >
          <Bars3Icon className="h-5 w-5" />
        </button>
      )}

      {/* 사이드바 */}
      <IntegratedSidebar
        projectId={projectId}
        promptCards={promptCards}
        onCardsChanged={loadPromptCards}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* 모바일 오버레이 */}
      {sidebarOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
};

export default ClaudeStyleWorkspace;
