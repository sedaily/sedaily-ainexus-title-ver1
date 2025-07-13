import React from "react";
import ReactMarkdown from "react-markdown";
import {
  ClipboardDocumentIcon,
  CheckCircleIcon,
  UserIcon,
  DocumentDuplicateIcon,
} from "@heroicons/react/24/outline";

const ChatMessage = ({
  message,
  onCopyMessage,
  onCopyTitle,
  copiedMessage,
}) => {
  const isUser = message.type === "user";

  return (
    <div
      className={`group relative ${isUser ? "ml-16 pr-6" : "mr-16 pl-6"} mb-6`}
    >
      <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
        <div
          className={`
          max-w-[85%] rounded-2xl px-6 py-4 relative shadow-lg backdrop-blur-sm
          ${
            isUser
              ? "bg-gradient-to-br from-blue-500 to-blue-700 text-white shadow-blue-200"
              : message.isError
              ? "bg-gradient-to-br from-red-50 to-red-100 text-red-800 border border-red-200 shadow-red-100"
              : message.isLoading
              ? "bg-gradient-to-br from-yellow-50 to-yellow-100 text-yellow-800 border border-yellow-200 shadow-yellow-100"
              : "bg-gradient-to-br from-white to-gray-50 text-gray-800 border border-gray-200 shadow-gray-100"
          }
        `}
        >
          {/* 메시지 내용 */}
          <div className="whitespace-pre-wrap leading-relaxed">
            {isUser ? (
              <div className="text-base font-medium">{message.content}</div>
            ) : (
              <div className="prose prose-base max-w-none prose-headings:text-gray-900 prose-p:text-gray-800 prose-strong:text-gray-900 prose-ul:text-gray-800 prose-li:text-gray-800">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            )}
          </div>

          {/* 제목 복사 버튼들 */}
          {message.titles && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="flex flex-wrap gap-2">
                {message.titles.map((title, index) => (
                  <button
                    key={index}
                    onClick={() => onCopyTitle(title, message.id, index)}
                    className={`flex items-center px-2 py-1 rounded text-xs transition-colors ${
                      copiedMessage === `${message.id}_title_${index}`
                        ? "bg-green-100 text-green-700"
                        : "bg-gray-100 hover:bg-gray-200 text-gray-700"
                    }`}
                  >
                    {copiedMessage === `${message.id}_title_${index}` ? (
                      <CheckCircleIcon className="h-3 w-3 mr-1" />
                    ) : (
                      <DocumentDuplicateIcon className="h-3 w-3 mr-1" />
                    )}
                    제목 {index + 1} 복사
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 복사 버튼 */}
          {!isUser && (
            <div className="mt-4 flex items-center space-x-2">
              <button
                onClick={() => onCopyMessage(message.content, message.id)}
                className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  copiedMessage === message.id
                    ? "bg-green-100 text-green-700 border border-green-200 shadow-sm"
                    : "bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-200 hover:shadow-md"
                }`}
              >
                {copiedMessage === message.id ? (
                  <CheckCircleIcon className="h-4 w-4 mr-2" />
                ) : (
                  <ClipboardDocumentIcon className="h-4 w-4 mr-2" />
                )}
                {copiedMessage === message.id ? "복사됨!" : "복사하기"}
              </button>
            </div>
          )}

          {/* 타임스탬프 */}
          <div
            className={`text-xs mt-3 font-medium ${
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
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              <span className="text-sm">AI가 응답을 생성하고 있습니다...</span>
            </div>
          )}

          {/* 에러 상태 */}
          {message.isError && (
            <div className="flex items-center text-red-600 mt-2">
              <span className="text-sm">⚠️ 오류가 발생했습니다</span>
            </div>
          )}
        </div>
      </div>

      {/* 사용자 아바타 */}
      {isUser && (
        <div className="absolute top-0 right-0 -mr-12 w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-700 rounded-full flex items-center justify-center shadow-lg border-2 border-white">
          <UserIcon className="h-5 w-5 text-white" />
        </div>
      )}
    </div>
  );
};

export default ChatMessage;
