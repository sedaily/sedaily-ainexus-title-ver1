import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  PaperAirplaneIcon,
  DocumentPlusIcon,
  XMarkIcon,
  ChatBubbleLeftRightIcon,
  SparklesIcon,
} from "@heroicons/react/24/outline";
import { useChat } from "../hooks/useChat";
import ChatMessage from "./chat/ChatMessage";

const ChatInterface = ({ projectId, projectName, promptCards = [] }) => {
  const navigate = useNavigate();
  const [uploadedFile, setUploadedFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const {
    messages,
    inputValue,
    setInputValue,
    copiedMessage,
    isGenerating,
    messagesEndRef,
    inputRef,
    handleSendMessage,
    handleKeyPress,
    handleCopyMessage,
    handleCopyTitle,
  } = useChat(projectId, projectName, promptCards);

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    if (file && file.type === "text/plain") {
      const reader = new FileReader();
      reader.onload = (e) => {
        setInputValue(e.target?.result || "");
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
          setInputValue(e.target?.result || "");
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
    setInputValue("");
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto px-6 py-6 min-h-0 bg-gray-50">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 mt-12">
              <div className="bg-white rounded-2xl shadow-md p-8 max-w-2xl w-full">
                <div className="flex justify-center mb-6">
                  <div className="bg-blue-100 p-3 rounded-full">
                    <ChatBubbleLeftRightIcon className="h-8 w-8 text-blue-600" />
                  </div>
                </div>
                <h2 className="text-xl font-semibold text-center text-gray-800 mb-4">
                  AI 헤드라인 어시스턴트
                </h2>
                <p className="text-gray-600 text-center mb-6">
                  본문을 입력하면 AI가 최적의 헤드라인을 제안해 드립니다.
                  <br></br>
                  오른쪽 사이드바에서 프롬프트 카드를 작성하여 창의적인 제목을
                  생성해보세요.
                </p>

                <div className="space-y-4">
                  <div className="flex items-start p-3 bg-gray-50 rounded-lg">
                    <div className="mr-3 mt-1">
                      <SparklesIcon className="h-5 w-5 text-blue-500" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-700">
                        <span className="font-medium">시작하는 방법:</span> 아래
                        입력창에 본문을 붙여넣고 전송 버튼을 클릭하세요
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start p-3 bg-gray-50 rounded-lg">
                    <div className="mr-3 mt-1">
                      <SparklesIcon className="h-5 w-5 text-blue-500" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-700">
                        <span className="font-medium">프롬프트 카드:</span>{" "}
                        오른쪽 사이드바에서 프롬프트 카드를 작성하여 제목을
                        생성하세요
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <ChatMessage
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
            <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-2">
                <DocumentPlusIcon className="h-4 w-4 text-blue-600" />
                <span className="text-sm text-blue-700">
                  {uploadedFile.name}
                </span>
              </div>
              <button
                onClick={removeFile}
                className="text-blue-600 hover:text-blue-800 p-1"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>
          )}

          <div
            className="bg-white rounded-[20px] shadow-md p-4 relative"
            style={{
              boxShadow: "rgba(0, 0, 0, 0.1) 0px 4px 12px 0px",
              border: "1px solid rgba(112, 115, 124, 0.08)",
              minHeight: "128px",
              display: "flex",
              flexDirection: "column",
              gap: "24px",
            }}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="기사 본문을 입력하세요..."
                className={`w-full pr-14 pl-2 py-2 border-0 focus:outline-none resize-none transition-colors ${
                  dragOver ? "bg-blue-50" : "bg-white"
                }`}
                rows={1}
                style={{
                  minHeight: "24px",
                  maxHeight: "150px",
                  lineHeight: "1.4",
                  overflowY: "auto",
                  whiteSpace: "pre-wrap",
                  fontSize: "16px",
                  fontWeight: "400",
                  color: "#171719",
                }}
                disabled={isGenerating}
              />

              {/* 전송 버튼 - 입력창 내부에 위치 */}
              <div className="absolute right-3 bottom-3">
                <button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isGenerating}
                  className="flex-shrink-0 bg-blue-600 text-white p-2 rounded-full hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
                  style={{ width: "32px", height: "32px" }}
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
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <span>{inputValue.length}자</span>
                {inputValue.length < 50 && <span>📝 50자 이상 권장</span>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
