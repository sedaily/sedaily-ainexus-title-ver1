import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  PaperAirplaneIcon,
  DocumentPlusIcon,
  XMarkIcon,
  ChatBubbleLeftRightIcon,
  SparklesIcon,
  StopIcon,
} from "@heroicons/react/24/outline";
import { useChat } from "../hooks/useChat";
import AnimatedChatMessage from "./AnimatedChatMessage";
import ModelSelector from "./ModelSelector";

const ChatInterface = ({ projectId, projectName, promptCards = [] }) => {
  const navigate = useNavigate();
  const [uploadedFile, setUploadedFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const {
    messages,
    inputValue,
    setInputValue,
    handleInputChange,
    copiedMessage,
    isGenerating,
    canSendMessage,
    messagesEndRef,
    inputRef,
    inputHeight,
    handleSendMessage,
    handleStopGeneration,
    handleKeyPress,
    handleCopyMessage,
    handleCopyTitle,
    wsConnected,
    wsConnecting,
    wsError,
    // 스크롤 관련 추가
    scrollContainerRef,
    handleScroll,
    isUserScrolling,
    // 모델 선택 관련 추가
    selectedModel,
    setSelectedModel,
  } = useChat(projectId, projectName, promptCards);

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    if (file && file.type === "text/plain") {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result || "";
        handleInputChange(content); // 높이 자동 조절
        setUploadedFile(file);
      };
      reader.readAsText(file);
    }
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragOver(false);
    const files = event.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      if (file.type === "text/plain") {
        const reader = new FileReader();
        reader.onload = (e) => {
          const content = e.target?.result || "";
          handleInputChange(content); // 높이 자동 조절
          setUploadedFile(file);
        };
        reader.readAsText(file);
      }
    }
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const removeFile = () => {
    setUploadedFile(null);
    handleInputChange(""); // 높이 초기화
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-dark-primary transition-colors duration-300">
      {/* 메시지 영역 */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-6 py-6 min-h-0 bg-gray-50 dark:bg-dark-primary"
      >
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 mt-12">
              <div className="bg-white dark:bg-dark-secondary card-dark rounded-2xl shadow-md p-8 max-w-2xl w-full transition-colors duration-300">
                <div className="flex justify-center mb-6">
                  <div className="bg-blue-100 dark:bg-dark-tertiary p-3 rounded-full">
                    <ChatBubbleLeftRightIcon className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                  </div>
                </div>
                <h2 className="text-xl font-semibold text-center text-gray-800 dark:text-white mb-4">
                  AI 헤드라인 어시스턴트
                </h2>
                <p className="text-gray-600 dark:text-gray-300 text-center mb-6">
                  본문을 입력하면 AI가 최적의 헤드라인을 제안해 드립니다.
                </p>

                <div className="space-y-4">
                  <div className="flex items-start p-3 bg-gray-50 dark:bg-dark-tertiary rounded-lg">
                    <div className="mr-3 mt-1">
                      <SparklesIcon className="h-5 w-5 text-blue-500 dark:text-blue-400" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        <span className="font-medium">시작하는 방법:</span> 아래
                        입력창에 본문을 붙여넣고 전송 버튼을 클릭하세요
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start p-3 bg-gray-50 dark:bg-dark-tertiary rounded-lg">
                    <div className="mr-3 mt-1">
                      <SparklesIcon className="h-5 w-5 text-blue-500 dark:text-blue-400" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        <span className="font-medium">프롬프트 카드:</span>{" "}
                        관리자 모드에서 프롬프트 카드를 작성하여 제목을
                        생성하세요
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <AnimatedChatMessage
                key={message.id}
                message={message}
                onCopyMessage={handleCopyMessage}
                onCopyTitle={handleCopyTitle}
                copiedMessage={copiedMessage}
              />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 입력 영역 */}
      <div className="flex-shrink-0 px-6 py-4">
        <div className="max-w-4xl mx-auto">
          {/* 업로드된 파일 표시 */}
          {uploadedFile && (
            <div className="mb-3 p-3 bg-blue-50 dark:bg-dark-tertiary rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-2">
                <DocumentPlusIcon className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                <span className="text-sm text-blue-700 dark:text-white">
                  {uploadedFile.name}
                </span>
              </div>
              <button
                onClick={removeFile}
                className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 p-1"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>
          )}

          <div
            className="bg-white dark:bg-dark-secondary rounded-[20px] p-4 relative transition-colors duration-300 flex flex-col gap-6"
            style={{
              minHeight: Math.max(128, inputHeight + 80),
              transition: "min-height 0.2s ease-in-out",
              boxShadow: "none",
            }}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <div className="flex-1 relative focus:outline-none">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => handleInputChange(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={
                  isGenerating
                    ? "생성 중입니다..."
                    : "기사 본문을 입력하세요..."
                }
                className={`w-full pr-14 pl-2 border-0 focus:outline-none resize-none transition-all duration-300 ${
                  dragOver
                    ? "bg-blue-50 dark:bg-dark-tertiary"
                    : isGenerating
                    ? "bg-gray-50 dark:bg-dark-primary"
                    : "bg-white dark:bg-dark-secondary text-gray-900 dark:text-white"
                }`}
                rows={1}
                style={{
                  height: `${inputHeight}px`,
                  minHeight: "24px",
                  maxHeight: "400px",
                  lineHeight: "1.4",
                  paddingTop: "0px",
                  paddingBottom: "6px",
                  overflowY: inputHeight > 200 ? "auto" : "hidden",
                  whiteSpace: "pre-wrap",
                  fontSize: "16px",
                  fontWeight: "400",
                  color: isGenerating ? "var(--text-muted)" : "inherit",
                  outline: "none",
                  boxShadow: "none",
                }}
                disabled={isGenerating}
              />

              {/* 전송/중단 버튼 - 입력창 내부에 위치 */}
              <div
                className="absolute right-3 bottom-0 flex items-center gap-2"
                style={{ bottom: "2px" }}
              >
                {isGenerating && (
                  <button
                    onClick={handleStopGeneration}
                    className="flex-shrink-0 bg-red-600 hover:bg-red-700 text-white p-2 rounded-full transition-colors flex items-center justify-center"
                    style={{ width: "32px", height: "32px" }}
                    title="생성 중단"
                  >
                    <StopIcon className="h-4 w-4" />
                  </button>
                )}
                <button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isGenerating}
                  className="flex-shrink-0 bg-blue-600 dark:bg-blue-600 hover:bg-blue-700 dark:hover:bg-blue-700 text-white p-2 rounded-full disabled:opacity-70 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
                  style={{ width: "32px", height: "32px" }}
                  title={
                    isGenerating
                      ? "생성 중..."
                      : wsConnected
                      ? "실시간 스트리밍 사용 가능"
                      : "일반 모드 (WebSocket 연결 안됨)"
                  }
                >
                  {isGenerating ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  ) : (
                    <PaperAirplaneIcon className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {/* 글자 수 표시 */}
                <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-dark-muted">
                  <span>{inputValue.length}자</span>
                </div>

                {/* 모델 선택기 */}
                <div className="flex items-center gap-2">
                  <ModelSelector
                    selectedModel={selectedModel}
                    onModelChange={setSelectedModel}
                  />
                </div>
              </div>

              {/* WebSocket 연결 상태 및 스크롤 상태 표시 */}
              <div className="flex items-center gap-3 text-xs">
                {/* 스크롤 상태 표시 */}
                {isUserScrolling && (
                  <div className="flex items-center gap-1 text-blue-600 dark:text-blue-400">
                    <span>📜</span>
                    <span>자유 스크롤</span>
                  </div>
                )}

                {/* WebSocket 연결 상태 */}
                {wsConnecting ? (
                  <div className="flex items-center gap-1 text-yellow-600 dark:text-yellow-400">
                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-yellow-600"></div>
                    <span>연결 중...</span>
                  </div>
                ) : wsConnected ? (
                  <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
                    <div className="w-2 h-2 bg-green-600 rounded-full"></div>
                    <span>실시간 스트리밍</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-1 text-gray-500 dark:text-dark-muted">
                    <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full"></div>
                    <span>일반 모드</span>
                  </div>
                )}
                {wsError && (
                  <div
                    className="text-red-500 dark:text-red-400 text-xs"
                    title={wsError}
                  >
                    ⚠️
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
