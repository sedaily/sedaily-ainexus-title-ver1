import React, { useState, useCallback, useMemo, memo } from "react";
import {
  ChatBubbleLeftRightIcon,
  SparklesIcon,
  PaperAirplaneIcon,
  StopIcon,
  CpuChipIcon,
} from "@heroicons/react/24/outline";
import ConversationDrawer from "./ConversationDrawer";
import ModelSelector from "../ModelSelector";
import { useChat } from "../../hooks/useChat";
import { useMessages } from "../../hooks/useMessages";
import { useConversations } from "../../hooks/useConversations";
import { useConversationContext } from "../../contexts/ConversationContext";
import { useAuth } from "../../contexts/AuthContext";
import SimpleChatMessage from "../SimpleChatMessage";
const ThoughtProcess = React.lazy(() => import("../ThoughtProcess"));
const StepwiseExecution = React.lazy(() => import("../StepwiseExecution"));

const ChatWindow = memo(
  ({
    promptCards = [],
    isAdminMode = false,
    rightSidebarCollapsed = false,
  }) => {
    console.log(
      "🔍 [DEBUG] ChatWindow - 받은 promptCards:",
      promptCards.length,
      promptCards
    );
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [enableStepwise, setEnableStepwise] = useState(false);
    const [thoughts, setThoughts] = useState([]);
    const [steps, setSteps] = useState([]);
    const [isExecutingSteps, setIsExecutingSteps] = useState(false);

    // Auth context for user info
    const { user } = useAuth();

    // Conversation context
    const { currentConversationId, setCurrentConversation, addConversation } =
      useConversationContext();
    const { createConversation } = useConversations();

    // Messages hook for current conversation
    const { messages: historicalMessages, loading: messagesLoading } =
      useMessages(currentConversationId);

    // Chat hook for sending messages
    console.log("🔍 [DEBUG] ChatWindow - useChat 호출:", {
      currentConversationId,
      currentConversationIdType: typeof currentConversationId,
      isCurrentConversationIdNull: currentConversationId === null,
    });

    // 단계별 실행 핸들러
    const handleThoughtProcess = useCallback((thought) => {
      setThoughts((prev) => [...prev, thought]);
    }, []);

    const handleStepResult = useCallback((step) => {
      setSteps((prev) => [...prev, step]);
    }, []);

    const handleStepwiseStart = useCallback(() => {
      setIsExecutingSteps(true);
      setThoughts([]);
      setSteps([]);
    }, []);

    const handleStepwiseComplete = useCallback(() => {
      setIsExecutingSteps(false);
    }, []);

    const {
      messages: chatMessages,
      inputValue,
      handleInputChange,
      copiedMessage,
      isGenerating,
      inputHeight,
      handleSendMessage,
      handleStopGeneration,
      handleKeyPress,
      handleCopyMessage,
      handleCopyTitle,
      wsConnected,
      wsConnecting,
      selectedModel,
      setSelectedModel,
    } = useChat(
      promptCards,
      currentConversationId,
      createConversation, // 대화 생성 함수 전달
      setCurrentConversation, // 대화 설정 함수 전달
      addConversation, // 전역 상태에 대화 추가 함수 전달
      enableStepwise, // 단계별 실행 모드
      handleThoughtProcess, // 사고과정 핸들러
      handleStepResult, // 단계 결과 핸들러
      handleStepwiseStart, // 단계별 실행 시작
      handleStepwiseComplete // 단계별 실행 완료
    );

    // 통합된 메시지 목록 (최적화된 메모이제이션)
    const allMessages = useMemo(() => {
      if (!currentConversationId) {
        // 새 대화 모드: useChat의 현재 세션 메시지만 표시
        return chatMessages;
      } else {
        // 기존 대화 모드: 저장된 메시지 + 현재 세션의 새 메시지
        return [...historicalMessages, ...chatMessages];
      }
    }, [currentConversationId, historicalMessages, chatMessages]);

    // 메시지 렌더링 최적화를 위한 콜백
    const renderMessage = useCallback(
      (message) => (
        <SimpleChatMessage
          key={message.id}
          message={message}
          onCopyMessage={handleCopyMessage}
          onCopyTitle={handleCopyTitle}
          copiedMessage={copiedMessage}
        />
      ),
      [handleCopyMessage, handleCopyTitle, copiedMessage]
    );

    return (
      <div className="flex h-[calc(100vh-56px)] overflow-hidden relative">
        {/* 대화 드로어 - 모바일에서는 오버레이로 표시 */}
        <ConversationDrawer onCollapsedChange={setSidebarCollapsed} />

        {/* 메인 채팅 영역 */}
        <div
          className={`flex-1 flex flex-col bg-gray-50 dark:bg-dark-primary transition-all duration-500 ease-out w-full ${
            sidebarCollapsed ? "ml-12" : "ml-12 md:ml-72"
          } ${isAdminMode && !rightSidebarCollapsed ? "mr-0 md:mr-80" : ""}`}
        >
          {/* 메시지 영역 */}
          <div className="flex-1 overflow-y-auto px-0 py-0 bg-gray-50 dark:bg-dark-primary transition-all duration-300 w-full custom-scrollbar">
            <div
              className={`w-full ${
                isAdminMode ? "" : "max-w-6xl mx-auto px-2 sm:px-4"
              } space-y-6`}
            >
              {allMessages.length === 0 && !messagesLoading ? (
                // 빈 상태 - 새 대화 시작
                <div
                  className={`flex flex-col items-center justify-center min-h-[60vh] ${
                    isAdminMode ? "px-4 sm:px-8" : "px-4"
                  }`}
                >
                  <div
                    className={`bg-white dark:bg-dark-secondary rounded-2xl shadow-md p-4 sm:p-8 w-full ${
                      isAdminMode ? "" : "max-w-3xl mx-auto"
                    } transition-colors duration-300`}
                  >
                    <div className="flex justify-center mb-6">
                      <div className="bg-blue-100 dark:bg-dark-tertiary p-3 rounded-full">
                        <ChatBubbleLeftRightIcon className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                      </div>
                    </div>
                    <h2 className="text-lg sm:text-xl font-semibold text-center text-gray-800 dark:text-white mb-4">
                      AI 헤드라인 어시스턴트
                    </h2>
                    <p className="text-sm sm:text-base text-gray-600 dark:text-gray-300 text-center mb-6">
                      본문을 입력하면 AI가 최적의 헤드라인을 제안해 드립니다.
                    </p>

                    <div className="space-y-4">
                      <div className="flex items-start p-3 bg-gray-50 dark:bg-dark-tertiary rounded-lg">
                        <div className="mr-3 mt-1">
                          <SparklesIcon className="h-5 w-5 text-blue-500 dark:text-blue-400" />
                        </div>
                        <div>
                          <p className="text-sm text-gray-700 dark:text-gray-300">
                            <span className="font-medium">시작하는 방법:</span>{" "}
                            아래 입력창에 본문을 붙여넣고 전송 버튼을 클릭하세요
                          </p>
                        </div>
                      </div>
                      <div className="flex items-start p-3 bg-gray-50 dark:bg-dark-tertiary rounded-lg">
                        <div className="mr-3 mt-1">
                          <SparklesIcon className="h-5 w-5 text-blue-500 dark:text-blue-400" />
                        </div>
                        <div>
                          <p className="text-sm text-gray-700 dark:text-gray-300">
                            <span className="font-medium">대화 기록:</span> 좌측
                            메뉴에서 이전 대화를 확인하고 이어서 대화할 수
                            있습니다
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                // 메시지 목록 (최적화된 렌더링)
                <div className="space-y-4 py-4 px-6 lg:px-6">
                  {allMessages.map(renderMessage)}

                  {/* 단계별 실행 컴포넌트 - 활성화되고 실행 중일 때만 표시 */}
                  {enableStepwise &&
                    (thoughts.length > 0 ||
                      steps.length > 0 ||
                      isExecutingSteps) && (
                      <div className="space-y-4 mt-6">
                        <React.Suspense fallback={<div>Loading...</div>}>
                          {/* 사고과정 표시 */}
                          {thoughts.length > 0 && (
                            <div className="max-w-6xl mx-auto">
                              <ThoughtProcess thoughts={thoughts} />
                            </div>
                          )}

                          {/* 단계별 실행 결과 */}
                          {(steps.length > 0 || isExecutingSteps) && (
                            <div className="max-w-6xl mx-auto">
                              <StepwiseExecution
                                steps={steps}
                                isExecuting={isExecutingSteps}
                              />
                            </div>
                          )}
                        </React.Suspense>
                      </div>
                    )}
                </div>
              )}
            </div>
          </div>

          {/* 하단 입력 영역 - 별도 영역으로 분리 */}
          <div className="flex-shrink-0 bg-gray-50 dark:bg-dark-primary border-t border-gray-200 dark:border-gray-700 w-full">
            <div
              className={`w-full ${
                isAdminMode ? "px-0" : "max-w-6xl mx-auto px-2 sm:px-4"
              } py-4 sm:py-6 pb-8 sm:pb-12`}
            >
              {/* 둥근 모서리 통짜 입력창 */}
              <div className="w-full rounded-2xl bg-white dark:bg-[#2E333D] border border-gray-200 dark:border-transparent shadow-sm dark:shadow-none transition-all duration-200">
                {/* 메인 입력 영역 */}
                <div className="flex items-center gap-2 sm:gap-3 px-3 sm:px-5 py-3 sm:py-4">
                  {/* 글 입력 영역 */}
                  <textarea
                    value={inputValue}
                    onChange={(e) => handleInputChange(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={
                      isGenerating
                        ? "생성 중입니다..."
                        : "기사 본문을 입력하세요..."
                    }
                    className="flex-1 resize-none bg-transparent text-sm sm:text-base text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none appearance-none"
                    rows={1}
                    style={{
                      height: `${Math.max(inputHeight || 24, 24)}px`,
                      minHeight: "24px",
                      maxHeight: "200px",
                      lineHeight: "1.5",
                      overflowY: inputHeight > 120 ? "auto" : "hidden",
                    }}
                    disabled={isGenerating}
                  />

                  {/* 전송/중단 버튼 */}
                  {isGenerating ? (
                    <button
                      onClick={handleStopGeneration}
                      className="shrink-0 rounded-full p-2.5 bg-red-500 hover:bg-red-600 text-white transition-all duration-200 animate-pulse shadow-lg"
                      title="생성 중단"
                    >
                      <StopIcon className="w-4 h-4" />
                    </button>
                  ) : (
                    <button
                      onClick={handleSendMessage}
                      disabled={!inputValue.trim()}
                      className={`shrink-0 rounded-full p-2.5 transition-all duration-200 ${
                        inputValue.trim()
                          ? "bg-[#5E89FF] hover:bg-[#4A7BFF] text-white shadow-md"
                          : "bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed"
                      }`}
                      title={
                        inputValue.trim()
                          ? "메시지 전송"
                          : "메시지를 입력하세요"
                      }
                    >
                      <PaperAirplaneIcon className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {/* 하단 정보 영역 - 입력창 안에 위치 */}
                <div className="flex items-center justify-between px-3 sm:px-5 pb-2 sm:pb-3 pt-1">
                  <div className="flex items-center gap-3">
                    {/* 모델 선택기 */}
                    <div className="scale-90 origin-left">
                      <ModelSelector
                        selectedModel={selectedModel}
                        onModelChange={setSelectedModel}
                      />
                    </div>

                    {/* 글자 수 표시 */}
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {inputValue.length}자
                    </div>
                  </div>

                  {/* 연결 상태 */}
                  <div className="flex items-center gap-1.5">
                    {wsConnecting ? (
                      <>
                        <div className="w-1.5 h-1.5 bg-yellow-500 rounded-full animate-pulse"></div>
                        <span className="text-xs text-yellow-600 dark:text-yellow-400">
                          연결 중
                        </span>
                      </>
                    ) : wsConnected ? (
                      <>
                        <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
                        <span className="text-xs text-green-600 dark:text-green-400">
                          실시간 스트리밍
                        </span>
                      </>
                    ) : (
                      <>
                        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full"></div>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          일반 모드
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* 하단 경고 문구 */}
              <div className="text-center mt-6 mb-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  AI는 실수를 할 수 있습니다. 중요한 정보는 재차 확인하세요.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }
);

export default ChatWindow;
