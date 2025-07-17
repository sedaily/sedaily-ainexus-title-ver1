import React from "react";
import ReactMarkdown from "react-markdown";
import {
  ClipboardDocumentIcon,
  CheckCircleIcon,
  DocumentDuplicateIcon,
  ExclamationTriangleIcon,
  ClockIcon,
} from "@heroicons/react/24/outline";

// 로딩 진행률 표시 컴포넌트
const LoadingProgress = ({ loadingProgress }) => {
  if (!loadingProgress) return null;

  const { stage, message, percentage } = loadingProgress;

  const getStageIcon = (currentStage) => {
    const stages = ["initializing", "analyzing", "generating", "finalizing"];
    const currentIndex = stages.indexOf(currentStage);

    return stages.map((stageName, index) => {
      const isActive = index <= currentIndex;
      const isCurrent = index === currentIndex;

      return (
        <div
          key={stageName}
          className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium ${
            isActive
              ? isCurrent
                ? "bg-blue-600 text-white animate-pulse"
                : "bg-green-500 text-white"
              : "bg-gray-200 text-gray-500"
          }`}
        >
          {isActive && !isCurrent ? "✓" : index + 1}
        </div>
      );
    });
  };

  return (
    <div className="mt-3 p-4 bg-blue-50 rounded-lg border border-blue-200">
      {/* 진행률 바 */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-blue-600 mb-1">
          <span>처리 진행률</span>
          <span>{percentage}%</span>
        </div>
        <div className="w-full bg-blue-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${percentage}%` }}
          ></div>
        </div>
      </div>

      {/* 단계별 진행 상황 */}
      <div className="flex justify-between items-center mb-2">
        {getStageIcon(stage)}
      </div>

      {/* 현재 상태 메시지 */}
      <div className="text-sm text-blue-700 font-medium">{message}</div>

      {/* 예상 소요 시간 표시 */}
      <div className="flex items-center mt-2 text-xs text-blue-600">
        <ClockIcon className="h-3 w-3 mr-1" />
        <span>일반적으로 30초-2분 소요됩니다</span>
      </div>
    </div>
  );
};

// 스트리밍 표시 컴포넌트
const StreamingIndicator = () => {
  return (
    <div className="inline-flex items-center mt-2 px-2 py-1 bg-blue-50 rounded-lg text-blue-600 text-xs font-medium">
      <div className="relative h-2 w-2 mr-2">
        <div className="absolute animate-ping h-2 w-2 rounded-full bg-blue-400 opacity-75"></div>
        <div className="absolute h-2 w-2 rounded-full bg-blue-600"></div>
      </div>
      스트리밍 중...
    </div>
  );
};

// 오류 상세 정보 표시 컴포넌트
const ErrorDetails = ({ errorDetails }) => {
  if (!errorDetails) return null;

  return (
    <div className="mt-3 p-3 bg-red-50 rounded-lg border border-red-200">
      <div className="flex items-center text-sm text-red-700 mb-2">
        <ExclamationTriangleIcon className="h-4 w-4 mr-2" />
        <span className="font-medium">오류 상세 정보</span>
      </div>
      <div className="text-xs text-red-600 space-y-1">
        <div>
          <span className="font-medium">유형:</span> {errorDetails.type}
        </div>
        {errorDetails.status && (
          <div>
            <span className="font-medium">상태:</span> {errorDetails.status}
          </div>
        )}
        {errorDetails.message && (
          <div>
            <span className="font-medium">메시지:</span> {errorDetails.message}
          </div>
        )}
      </div>
    </div>
  );
};

const ChatMessage = ({
  message,
  onCopyMessage,
  onCopyTitle,
  copiedMessage,
}) => {
  const isUser = message.type === "user";

  return (
    <div className={`group relative ${isUser ? "ml-8" : "mr-8"} mb-6`}>
      <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
        {isUser ? (
          // 사용자 메시지 - 디자인된 박스
          <div className="max-w-[85%] rounded-lg px-6 py-4 bg-blue-600 text-white">
            <div className="text-base font-medium whitespace-pre-wrap leading-relaxed">
              {message.content}
            </div>
            <div className="text-xs mt-3 font-medium text-blue-100">
              {message.timestamp?.toLocaleTimeString() || ""}
            </div>
          </div>
        ) : (
          // AI 메시지 - 박스 없이 깔끔하게
          <div className="max-w-[85%] w-full">
            {/* AI 응답 내용 */}
            <div className="whitespace-pre-wrap leading-relaxed text-gray-800">
              {message.isError ? (
                <div>
                  <div className="text-red-600 text-base">
                    {message.content}
                  </div>
                  <ErrorDetails errorDetails={message.errorDetails} />
                </div>
              ) : message.isLoading ? (
                <div>
                  {message.isStreaming ? (
                    // 스트리밍 메시지 표시
                    <div>
                      {message.content ? (
                        <div className="prose prose-base max-w-none prose-headings:text-gray-900 prose-p:text-gray-800 prose-strong:text-gray-900 prose-ul:text-gray-800 prose-li:text-gray-800 prose-code:text-gray-800 prose-pre:bg-gray-50">
                          <ReactMarkdown>{message.content}</ReactMarkdown>
                        </div>
                      ) : (
                        <div className="text-blue-600 text-base font-medium">
                          응답을 생성하는 중...
                        </div>
                      )}
                      <StreamingIndicator />
                    </div>
                  ) : (
                    // 일반 로딩 메시지 표시
                    <div>
                      <div className="flex items-center text-blue-600">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                        <span className="text-base font-medium">
                          {message.content ||
                            "AI가 답변을 생성하고 있습니다..."}
                        </span>
                      </div>
                      <LoadingProgress
                        loadingProgress={message.loadingProgress}
                      />
                    </div>
                  )}
                </div>
              ) : (
                <div className="prose prose-base max-w-none prose-headings:text-gray-900 prose-p:text-gray-800 prose-strong:text-gray-900 prose-ul:text-gray-800 prose-li:text-gray-800 prose-code:text-gray-800 prose-pre:bg-gray-50">
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>
              )}
            </div>

            {/* 제목 복사 버튼들 */}
            {message.titles && (
              <div className="mt-4 pt-3 border-t border-gray-200">
                <div className="flex flex-wrap gap-2">
                  {message.titles.map((title, index) => (
                    <button
                      key={index}
                      onClick={() => onCopyTitle(title, message.id, index)}
                      className={`flex items-center px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        copiedMessage === `${message.id}_title_${index}`
                          ? "bg-green-100 text-green-700 border border-green-200"
                          : "bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-200"
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

            {/* 복사 버튼 및 성능 정보 표시 */}
            {!message.isLoading && (
              <div className="mt-4 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  {/* 복사 버튼 */}
                  <button
                    onClick={() => onCopyMessage(message.content, message.id)}
                    className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      copiedMessage === message.id
                        ? "bg-green-100 text-green-700 border border-green-200"
                        : "bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-200"
                    }`}
                  >
                    {copiedMessage === message.id ? (
                      <CheckCircleIcon className="h-4 w-4 mr-2" />
                    ) : (
                      <ClipboardDocumentIcon className="h-4 w-4 mr-2" />
                    )}
                    {copiedMessage === message.id ? "복사됨!" : "복사하기"}
                  </button>

                  {/* 성능 정보 표시 (AI 응답인 경우) */}
                  {message.performance_metrics && (
                    <div className="text-xs text-gray-500 bg-gray-50 px-2 py-1 rounded">
                      처리시간: {message.performance_metrics.total_time}초
                    </div>
                  )}
                </div>

                {/* 타임스탬프 */}
                <div className="text-xs text-gray-500">
                  {message.timestamp?.toLocaleTimeString() || ""}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
