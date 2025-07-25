import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";

// 타임스탬프 포맷팅 유틸리티 함수
const formatTimestamp = (timestamp) => {
  if (!timestamp) return "";

  try {
    // 이미 Date 객체인 경우
    if (timestamp instanceof Date) {
      return timestamp.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      });
    }

    // 문자열인 경우 Date 객체로 변환
    if (typeof timestamp === "string") {
      const date = new Date(timestamp);
      return isNaN(date.getTime()) ? "" : date.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      });
    }

    // 숫자인 경우 (타임스탬프)
    if (typeof timestamp === "number") {
      return new Date(timestamp).toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      });
    }

    return "";
  } catch (error) {
    console.warn("타임스탬프 포맷 오류:", error);
    return "";
  }
};

const SimpleChatMessage = React.memo(({ message, onCopyMessage, onCopyTitle, copiedMessage }) => {
  // 사용자가 대화창에서 전송한 메시지면 사용자 메시지!
  const isUser = message.role === "user" || message.type === "user";
  const isError = message.role === "error";
  const isLoading = message.isLoading || false;
  
  // 버튼 상태 관리
  const [likeClicked, setLikeClicked] = useState(false);
  const [dislikeClicked, setDislikeClicked] = useState(false);
  const [copyClicked, setCopyClicked] = useState(false);
  
  // 복사 기능
  const handleCopyClick = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopyClicked(true);
      setTimeout(() => setCopyClicked(false), 1000);
      // 팝업 알림 없이 복사만 실행
    } catch (err) {
      console.error('복사 실패:', err);
    }
  };
  
  // 좋아요 클릭
  const handleLikeClick = () => {
    setLikeClicked(true);
    setDislikeClicked(false); // 반대 버튼 비활성화
    setTimeout(() => setLikeClicked(false), 2000);
  };
  
  // 싫어요 클릭
  const handleDislikeClick = () => {
    setDislikeClicked(true);
    setLikeClicked(false); // 반대 버튼 비활성화
    setTimeout(() => setDislikeClicked(false), 2000);
  };
  

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      {isUser ? (
        // 사용자 메시지 - 우측 말풍선
        <div className="max-w-[70%]">
          <div 
            className="bg-[#5E89FF] text-white rounded-2xl px-4 py-2 shadow-md"
          >
            <div className="text-[15px] font-normal leading-[1.5] whitespace-pre-wrap break-words">
              {message.content}
            </div>
            {/* 타임스탬프 - 말풍선 내부 하단 */}
            {message.timestamp && (
              <div className="text-[12px] text-white/70 mt-1 text-right">
                {formatTimestamp(message.timestamp)}
              </div>
            )}
          </div>
        </div>
      ) : (
        // AI 메시지 - 좌측 플랫형 답변
        <div className="w-full max-w-[75%]">
          <div 
            className="bg-transparent dark:bg-transparent" 
            aria-live="polite"
          >
            {isError ? (
              <div className="text-red-600 dark:text-red-400">
                <div className="flex items-center mb-2">
                  <ExclamationTriangleIcon className="h-4 w-4 mr-2" />
                  <span className="text-[14px] font-semibold">오류가 발생했습니다</span>
                </div>
                <div className="text-[15px] font-normal leading-[1.5]">{message.content}</div>
              </div>
            ) : isLoading ? (
              // 스트리밍 중 - 실시간 텍스트 표시
              <div className="flex items-start gap-3">
                {/* AI 아이콘 */}
                <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-indigo-400 to-purple-500 rounded-full flex items-center justify-center shadow-sm mt-1">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.847a4.5 4.5 0 003.09 3.09L15.75 12l-2.847.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
                  </svg>
                </div>
                
                {/* 실시간 스트리밍 텍스트 */}
                <div className="flex-1 text-[#202124] dark:text-[#E5E7EB] prose prose-sm max-w-none">
                  <div className="text-[15px] font-normal leading-[1.6] whitespace-pre-wrap [&>p]:mb-3 [&>ul]:mb-3 [&>ol]:mb-3 [&>h1]:text-[18px] [&>h1]:font-semibold [&>h1]:mb-3 [&>h2]:text-[16px] [&>h2]:font-semibold [&>h2]:mb-2 [&>h3]:text-[15px] [&>h3]:font-medium [&>h3]:mb-2">
                    <ReactMarkdown>{message.content || ""}</ReactMarkdown>
                    {/* 타이핑 커서 애니메이션 */}
                    <span className="inline-block w-2 h-5 bg-blue-500 ml-1 animate-pulse"></span>
                  </div>
                </div>
              </div>
            ) : (
              // 일반 AI 응답 - 제미나이 스타일 로고 포함
              <div className="flex items-start gap-3">
                {/* AI 아이콘 */}
                <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-indigo-400 to-purple-500 rounded-full flex items-center justify-center shadow-sm mt-1">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.847a4.5 4.5 0 003.09 3.09L15.75 12l-2.847.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
                  </svg>
                </div>
                
                {/* 답변 내용 */}
                <div className="flex-1 text-[#202124] dark:text-[#E5E7EB] prose prose-sm max-w-none">
                  <div className="text-[15px] font-normal leading-[1.6] whitespace-pre-wrap [&>p]:mb-3 [&>ul]:mb-3 [&>ol]:mb-3 [&>h1]:text-[18px] [&>h1]:font-semibold [&>h1]:mb-3 [&>h2]:text-[16px] [&>h2]:font-semibold [&>h2]:mb-2 [&>h3]:text-[15px] [&>h3]:font-medium [&>h3]:mb-2">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                </div>
              </div>
            )}
            {/* 타임스탬프 - 아이콘 위치에 맞춘 여백 */}
            {message.timestamp && (
              <div className="text-[12px] text-gray-500 dark:text-gray-400 mt-1 ml-11">
                {formatTimestamp(message.timestamp)}
              </div>
            )}
          </div>
          
          {/* AI 메시지 하단 액션 버튼들 - GPT 스타일 */}
          {!isError && !isLoading && (
            <div className="flex items-center gap-1 mt-2 ml-11">
              {/* 복사 버튼 */}
              <button
                onClick={handleCopyClick}
                className={`p-1.5 rounded transition-all duration-200 transform ${
                  copyClicked
                    ? "text-green-500 bg-green-100 dark:bg-green-900/30 scale-110"
                    : "text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                }`}
                title={copyClicked ? "복사됨!" : "복사"}
              >
                <svg 
                  className="w-4 h-4" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  {copyClicked ? (
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  )}
                </svg>
              </button>
              
              {/* 좋아요 버튼 */}
              <button
                onClick={handleLikeClick}
                className={`p-1.5 rounded transition-all duration-300 transform ${
                  likeClicked
                    ? "text-blue-500 bg-blue-100 dark:bg-blue-900/30 scale-110 animate-pulse"
                    : "text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                }`}
                title={likeClicked ? "좋아요!" : "좋아요"}
              >
                <svg 
                  className="w-4 h-4" 
                  fill={likeClicked ? "currentColor" : "none"}
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                </svg>
              </button>
              
              {/* 싫어요 버튼 */}
              <button
                onClick={handleDislikeClick}
                className={`p-1.5 rounded transition-all duration-300 transform ${
                  dislikeClicked
                    ? "text-red-500 bg-red-100 dark:bg-red-900/30 scale-110 border-2 border-red-300 animate-pulse"
                    : "text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                }`}
                title={dislikeClicked ? "싫어요!" : "싫어요"}
              >
                <svg 
                  className="w-4 h-4 rotate-180" 
                  fill={dislikeClicked ? "currentColor" : "none"}
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.60L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                </svg>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

export default SimpleChatMessage;