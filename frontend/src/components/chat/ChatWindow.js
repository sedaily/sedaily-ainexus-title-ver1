import React, { useState, useCallback, useMemo, memo, useRef } from "react";
import {
  ChatBubbleLeftRightIcon,
  SparklesIcon,
  PaperAirplaneIcon,
  StopIcon,
  CpuChipIcon,
} from "@heroicons/react/24/outline";
import toast from "react-hot-toast";
import ConversationDrawer from "./ConversationDrawer";
import ModelSelector from "../ModelSelector";
import FileUploadButton from "../FileUploadButton";
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
    const [isDragging, setIsDragging] = useState(false);
    const dragCounterRef = useRef(0);
    const fileInputRef = useRef(null);
    const [attachedFiles, setAttachedFiles] = useState([]);

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
      handleSendMessage: originalHandleSendMessage,
      handleStopGeneration,
      handleKeyPress: originalHandleKeyPress,
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

    // 첨부파일과 함께 메시지 전송하는 래퍼 함수
    const handleSendMessage = useCallback(() => {
      console.log('🔍 [DEBUG] handleSendMessage 호출:', {
        inputValue: inputValue,
        inputValueLength: inputValue.length,
        attachedFilesCount: attachedFiles.length,
        attachedFiles: attachedFiles.map(f => ({ name: f.name, contentLength: f.content.length }))
      });

      // 아무것도 없으면 에러
      if (!inputValue?.trim() && attachedFiles.length === 0) {
        toast.error('메시지를 입력하거나 파일을 첨부해주세요.', {
          duration: 3000,
          position: 'top-center',
        });
        return;
      }

      // 메시지 전송
      originalHandleSendMessage(inputValue, attachedFiles);
      
      // 전송 후 첨부파일 초기화
      setAttachedFiles([]);
    }, [inputValue, attachedFiles, originalHandleSendMessage]);

    // 키 입력 핸들러
    const handleKeyPress = useCallback((e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    }, [handleSendMessage]);

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

    // 드래그 앤 드롭 이벤트 핸들러
    const handleDragEnter = useCallback((e) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounterRef.current += 1;
      if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
        setIsDragging(true);
      }
    }, []);

    const handleDragLeave = useCallback((e) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounterRef.current -= 1;
      if (dragCounterRef.current === 0) {
        setIsDragging(false);
      }
    }, []);

    const handleDragOver = useCallback((e) => {
      e.preventDefault();
      e.stopPropagation();
    }, []);

    const handleDrop = useCallback(async (e) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      dragCounterRef.current = 0;

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        // 첫 번째 파일만 처리 (여러 파일 중 하나만)
        const file = files[0];
        
        // FileUploadButton의 로직을 재사용
        if (file.type === 'text/plain' || file.name.endsWith('.txt') || 
            file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
          // 파일 처리를 위해 FileUploadButton의 ref를 통해 처리
          if (fileInputRef.current && fileInputRef.current.handleFile) {
            await fileInputRef.current.handleFile(file);
          }
        } else {
          toast.error('지원하지 않는 파일 형식입니다. TXT 또는 PDF 파일만 업로드 가능합니다.', {
            duration: 4000,
            position: 'top-center',
          });
        }
      }
    }, []);

    return (
      <div 
        className="flex h-[calc(100vh-56px)] overflow-hidden relative"
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {/* 드래그 앤 드롭 오버레이 */}
        {isDragging && (
          <div className="absolute inset-0 z-50 bg-blue-50 dark:bg-blue-900 bg-opacity-95 dark:bg-opacity-20 backdrop-blur-sm flex items-center justify-center transition-all duration-200">
            <div className="bg-white dark:bg-dark-secondary rounded-3xl shadow-2xl p-12 text-center transform scale-105 transition-transform duration-200">
              <div className="relative">
                <div className="bg-gradient-to-br from-blue-100 to-blue-200 dark:from-blue-800 dark:to-blue-900 rounded-full p-8 w-32 h-32 mx-auto mb-6 flex items-center justify-center animate-bounce">
                  <svg className="w-16 h-16 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <div className="absolute inset-0 bg-blue-400 dark:bg-blue-500 rounded-full blur-xl opacity-20 animate-pulse"></div>
              </div>
              <h3 className="text-2xl font-bold text-gray-800 dark:text-white mb-3">
                파일을 여기에 놓으세요
              </h3>
              <p className="text-base text-gray-600 dark:text-gray-300 mb-2">
                TXT, PDF 파일 지원
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                최대 50MB까지 업로드 가능
              </p>
            </div>
          </div>
        )}

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
                {/* 첨부파일 표시 영역 */}
                {attachedFiles.length > 0 && (
                  <div className="flex flex-wrap gap-2 px-3 sm:px-5 pt-3 pb-2 border-b border-gray-200 dark:border-gray-600">
                    {attachedFiles.map(file => (
                      <div
                        key={file.id}
                        className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 rounded-lg group hover:bg-gray-200 dark:hover:bg-gray-600 transition-all duration-200"
                      >
                        <div className="flex items-center gap-2">
                          {/* 파일 아이콘 */}
                          <div className="w-8 h-8 bg-gradient-to-br from-pink-500 to-pink-600 dark:from-pink-600 dark:to-pink-700 rounded flex items-center justify-center shadow-sm">
                            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-5L9 2H4z" clipRule="evenodd" />
                            </svg>
                          </div>
                          <div className="flex flex-col">
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-200 max-w-[150px] truncate">
                              {file.name}
                            </span>
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              {file.type === 'pdf' && file.pageCount ? `${file.pageCount}페이지` : '문서'}
                            </span>
                          </div>
                        </div>
                        {/* 제거 버튼 */}
                        <button
                          onClick={() => setAttachedFiles(prev => prev.filter(f => f.id !== file.id))}
                          className="ml-1 p-1 rounded-full bg-transparent hover:bg-gray-300 dark:hover:bg-gray-500 transition-all duration-200 opacity-60 hover:opacity-100"
                          title="파일 제거"
                        >
                          <svg className="w-4 h-4 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* 메인 입력 영역 */}
                <div className="flex items-center gap-2 sm:gap-3 px-3 sm:px-5 py-3 sm:py-4">
                  {/* 파일 업로드 버튼 */}
                  <FileUploadButton
                    ref={fileInputRef}
                    onFileContent={(text, fileInfo) => {
                      // 파일을 첨부파일 목록에 추가
                      if (fileInfo) {
                        const newFile = {
                          id: Date.now() + Math.random(), // 고유 ID
                          name: fileInfo.fileName,
                          size: fileInfo.fileSize,
                          type: fileInfo.fileType,
                          content: text,
                          pageCount: fileInfo.pageCount
                        };
                        
                        setAttachedFiles(prev => [...prev, newFile]);
                        
                        // 성공 토스트
                        toast.success(`📎 ${fileInfo.fileName} 파일이 첨부되었습니다.`, {
                          duration: 3000,
                          position: 'top-center',
                        });
                      }
                    }}
                    disabled={isGenerating}
                  />
                  
                  {/* 글 입력 영역 */}
                  <textarea
                    value={inputValue}
                    onChange={(e) => handleInputChange(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={
                      isGenerating
                        ? "생성 중입니다..."
                        : "기사 본문을 입력하거나 파일을 업로드하세요..."
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
                      disabled={!inputValue?.trim() && attachedFiles.length === 0}
                      className={`shrink-0 rounded-full p-2.5 transition-all duration-200 ${
                        inputValue?.trim() || attachedFiles.length > 0
                          ? "bg-[#5E89FF] hover:bg-[#4A7BFF] text-white shadow-md"
                          : "bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed"
                      }`}
                      title={
                        inputValue?.trim() || attachedFiles.length > 0
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

                    {/* 글자 수 표시 및 대용량 텍스트 경고 */}
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {inputValue.length.toLocaleString()}자
                      {inputValue.length > 200000 && (
                        <span className="ml-2 text-blue-500 font-medium">
                          (대용량 문서 - 배치 처리 모드)
                        </span>
                      )}
                      {inputValue.length > 150000 && inputValue.length <= 200000 && (
                        <span className="ml-2 text-red-500 font-medium">
                          (너무 긴 텍스트 - 오류 발생 가능)
                        </span>
                      )}
                      {inputValue.length > 50000 && inputValue.length <= 150000 && (
                        <span className="ml-2 text-orange-500">
                          (긴 텍스트 - 처리 시간 증가)
                        </span>
                      )}
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
