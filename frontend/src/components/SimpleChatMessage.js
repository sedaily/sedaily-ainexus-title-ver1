import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ExclamationTriangleIcon } from "@heroicons/react/24/outline";
import { formatAIResponse } from "../utils/formatAIResponse";

// 테이블 복사 기능을 위한 컴포넌트
const TableWithCopy = ({ children, node, ...props }) => {
  const [copied, setCopied] = useState(false);
  const tableRef = React.useRef(null);
  
  const handleCopyTable = async () => {
    if (!tableRef.current) return;
    
    try {
      // 1. HTML 형식으로 복사 시도 (Excel에서 표로 인식)
      const htmlContent = tableRef.current.outerHTML;
      
      // 2. 텍스트 형식도 준비 (탭 구분)
      const rows = tableRef.current.querySelectorAll('tr');
      let textContent = '';
      
      rows.forEach((row) => {
        const cells = row.querySelectorAll('th, td');
        const rowText = Array.from(cells).map(cell => {
          // 셀 내의 줄바꿈을 공백으로 변환
          return cell.textContent.trim().replace(/\n/g, ' ');
        }).join('\t');
        textContent += rowText + '\n';
      });
      
      // 3. 클립보드 API를 사용하여 여러 형식으로 복사
      const clipboardItem = new ClipboardItem({
        'text/html': new Blob([htmlContent], { type: 'text/html' }),
        'text/plain': new Blob([textContent.trim()], { type: 'text/plain' })
      });
      
      await navigator.clipboard.write([clipboardItem]);
      
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // 구형 브라우저나 권한 문제 시 텍스트만 복사
      console.warn('HTML 복사 실패, 텍스트로 복사 시도:', err);
      
      const rows = tableRef.current.querySelectorAll('tr');
      let textContent = '';
      
      rows.forEach((row) => {
        const cells = row.querySelectorAll('th, td');
        const rowText = Array.from(cells).map(cell => {
          return cell.textContent.trim().replace(/\n/g, ' ');
        }).join('\t');
        textContent += rowText + '\n';
      });
      
      navigator.clipboard.writeText(textContent.trim()).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };
  
  return (
    <div className="table-wrapper">
      <button
        onClick={handleCopyTable}
        className="table-copy-btn"
        title="테이블 복사"
        type="button"
      >
        {copied ? (
          <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <svg className="w-4 h-4 text-gray-600 dark:text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        )}
      </button>
      <table ref={tableRef} {...props}>{children}</table>
    </div>
  );
};

// 마크다운 텍스트 전처리 함수 - 헤딩 제거
const preprocessMarkdown = (text) => {
  if (!text) return text;
  
  // # 으로 시작하는 헤딩을 일반 텍스트로 변환
  return text
    .replace(/^#{1,6}\s+/gm, '') // 줄 시작의 # 제거
    .replace(/\n#{1,6}\s+/g, '\n'); // 줄 중간의 # 제거
};


// 타임스탬프 포맷팅 유틸리티 함수
const formatTimestamp = (timestamp) => {
  if (!timestamp) return "";

  try {
    // 이미 Date 객체인 경우
    if (timestamp instanceof Date) {
      return timestamp.toLocaleTimeString("ko-KR", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    }

    // 문자열인 경우 Date 객체로 변환
    if (typeof timestamp === "string") {
      const date = new Date(timestamp);
      return isNaN(date.getTime())
        ? ""
        : date.toLocaleTimeString("ko-KR", {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          });
    }

    // 숫자인 경우 (타임스탬프)
    if (typeof timestamp === "number") {
      return new Date(timestamp).toLocaleTimeString("ko-KR", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    }

    return "";
  } catch (error) {
    console.warn("타임스탬프 포맷 오류:", error);
    return "";
  }
};

const SimpleChatMessage = React.memo(
  ({ message, onCopyMessage, onCopyTitle, copiedMessage }) => {
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
        console.error("복사 실패:", err);
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
      <div
        className={`flex ${
          isUser ? "justify-end" : "justify-start"
        } mb-3 w-full`}
      >
        {isUser ? (
          // 사용자 메시지 - 우측 말풍선
          <div className="max-w-[85%] sm:max-w-[70%]">
            <div className="bg-[#5E89FF] text-white rounded-2xl px-3 sm:px-4 py-2 shadow-md ml-auto">
              <div className="text-sm sm:text-[15px] font-normal leading-[1.5] whitespace-pre-wrap break-words">
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
          <div className="max-w-[95%] sm:max-w-[85%]">
            <div
              className="bg-transparent dark:bg-transparent"
              aria-live="polite"
            >
              {isError ? (
                <div className="text-red-600 dark:text-red-400">
                  <div className="flex items-center mb-2">
                    <ExclamationTriangleIcon className="h-4 w-4 mr-2" />
                    <span className="text-[14px] font-semibold">
                      오류가 발생했습니다
                    </span>
                  </div>
                  <div className="text-sm sm:text-[15px] font-normal leading-[1.5]">
                    {message.content}
                  </div>
                </div>
              ) : isLoading ? (
                // 스트리밍 중 - 실시간 텍스트 표시
                <div className="flex items-start gap-3">
                  {/* AI 아이콘 */}
                  <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-indigo-400 to-purple-500 rounded-full flex items-center justify-center shadow-sm mt-1">
                    <svg
                      className="w-4 h-4 text-white"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.847a4.5 4.5 0 003.09 3.09L15.75 12l-2.847.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"
                      />
                    </svg>
                  </div>

                  {/* 실시간 스트리밍 텍스트 */}
                  <div className="flex-1 w-full max-w-none">
                    <div
                      className="text-sm sm:text-[17px] font-normal leading-[1.8] sm:leading-[2.2] text-gray-800 dark:text-gray-200 
                    prose prose-sm sm:prose-base max-w-none
                    prose-headings:text-gray-900 dark:prose-headings:text-gray-100
                    prose-headings:font-bold
                    prose-h1:!text-3xl prose-h1:mb-6 prose-h1:mt-8 prose-h1:pb-3 prose-h1:border-b-2 prose-h1:border-gray-200 dark:prose-h1:border-gray-700
                    prose-h2:!text-2xl prose-h2:mb-5 prose-h2:mt-7 prose-h2:pb-2 prose-h2:border-b prose-h2:border-gray-200 dark:prose-h2:border-gray-700
                    prose-h3:!text-xl prose-h3:mb-4 prose-h3:mt-6 prose-h3:text-blue-700 dark:prose-h3:text-blue-400
                    prose-p:mb-6 prose-p:leading-[2.4]
                    prose-ul:mb-8 prose-ul:pl-6 prose-ul:list-disc
                    prose-ol:mb-8 prose-ol:pl-6 prose-ol:list-decimal
                    prose-li:mb-6 prose-li:leading-[2.2]
                    prose-strong:font-bold prose-strong:text-gray-900 dark:prose-strong:text-gray-100
                    prose-code:text-base prose-code:bg-blue-50 dark:prose-code:bg-gray-800 
                    prose-code:px-2 prose-code:py-1 prose-code:rounded prose-code:font-mono
                    prose-code:text-blue-800 dark:prose-code:text-blue-300
                    prose-pre:bg-gray-50 dark:prose-pre:bg-gray-900
                    prose-pre:p-6 prose-pre:rounded-lg prose-pre:overflow-x-auto prose-pre:text-sm
                    prose-pre:border prose-pre:border-gray-200 dark:prose-pre:border-gray-700
                    prose-table:w-full prose-table:border-collapse prose-table:my-6
                    prose-th:border prose-th:border-gray-300 dark:prose-th:border-gray-600 
                    prose-th:px-4 prose-th:py-3 prose-th:bg-gray-100 dark:prose-th:bg-gray-700 
                    prose-th:font-semibold prose-th:text-left
                    prose-td:border prose-td:border-gray-300 dark:prose-td:border-gray-600 
                    prose-td:px-4 prose-td:py-3
                    prose-blockquote:border-l-4 prose-blockquote:border-gray-300 dark:prose-blockquote:border-gray-600
                    prose-blockquote:pl-6 prose-blockquote:italic prose-blockquote:my-6
                    prose-a:text-blue-600 dark:prose-a:text-blue-400 prose-a:underline prose-a:font-medium
                    prose-hr:my-8 prose-hr:border-gray-300 dark:prose-hr:border-gray-600"
                    >
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          table: TableWithCopy,
                          // 헤딩을 일반 텍스트로 렌더링
                          h1: ({children}) => <span className="font-bold text-lg">{children}</span>,
                          h2: ({children}) => <span className="font-bold text-base">{children}</span>,
                          h3: ({children}) => <span className="font-bold text-base">{children}</span>,
                          h4: ({children}) => <span className="font-bold text-base">{children}</span>,
                          h5: ({children}) => <span className="font-bold text-base">{children}</span>,
                          h6: ({children}) => <span className="font-bold text-base">{children}</span>,
                        }}
                      >
                        {preprocessMarkdown(formatAIResponse(message.content || "")).trimEnd()}
                      </ReactMarkdown>
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
                    <svg
                      className="w-4 h-4 text-white"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.847a4.5 4.5 0 003.09 3.09L15.75 12l-2.847.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"
                      />
                    </svg>
                  </div>

                  {/* 답변 내용 */}
                  <div className="flex-1 w-full max-w-none">
                    <div
                      className="text-sm sm:text-[17px] font-normal leading-[1.8] sm:leading-[2.2] text-gray-800 dark:text-gray-200 
                    prose prose-sm sm:prose-base max-w-none
                    prose-headings:text-gray-900 dark:prose-headings:text-gray-100
                    prose-headings:font-bold
                    prose-h1:!text-3xl prose-h1:mb-6 prose-h1:mt-8 prose-h1:pb-3 prose-h1:border-b-2 prose-h1:border-gray-200 dark:prose-h1:border-gray-700
                    prose-h2:!text-2xl prose-h2:mb-5 prose-h2:mt-7 prose-h2:pb-2 prose-h2:border-b prose-h2:border-gray-200 dark:prose-h2:border-gray-700
                    prose-h3:!text-xl prose-h3:mb-4 prose-h3:mt-6 prose-h3:text-blue-700 dark:prose-h3:text-blue-400
                    prose-p:mb-6 prose-p:leading-[2.4]
                    prose-ul:mb-8 prose-ul:pl-6 prose-ul:list-disc
                    prose-ol:mb-8 prose-ol:pl-6 prose-ol:list-decimal
                    prose-li:mb-6 prose-li:leading-[2.2]
                    prose-strong:font-bold prose-strong:text-gray-900 dark:prose-strong:text-gray-100
                    prose-code:text-base prose-code:bg-blue-50 dark:prose-code:bg-gray-800 
                    prose-code:px-2 prose-code:py-1 prose-code:rounded prose-code:font-mono
                    prose-code:text-blue-800 dark:prose-code:text-blue-300
                    prose-pre:bg-gray-50 dark:prose-pre:bg-gray-900
                    prose-pre:p-6 prose-pre:rounded-lg prose-pre:overflow-x-auto prose-pre:text-sm
                    prose-pre:border prose-pre:border-gray-200 dark:prose-pre:border-gray-700
                    prose-table:w-full prose-table:border-collapse prose-table:my-6
                    prose-th:border prose-th:border-gray-300 dark:prose-th:border-gray-600 
                    prose-th:px-4 prose-th:py-3 prose-th:bg-gray-100 dark:prose-th:bg-gray-700 
                    prose-th:font-semibold prose-th:text-left
                    prose-td:border prose-td:border-gray-300 dark:prose-td:border-gray-600 
                    prose-td:px-4 prose-td:py-3
                    prose-blockquote:border-l-4 prose-blockquote:border-gray-300 dark:prose-blockquote:border-gray-600
                    prose-blockquote:pl-6 prose-blockquote:italic prose-blockquote:my-6
                    prose-a:text-blue-600 dark:prose-a:text-blue-400 prose-a:underline prose-a:font-medium
                    prose-hr:my-8 prose-hr:border-gray-300 dark:prose-hr:border-gray-600"
                    >
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          table: TableWithCopy,
                          // 헤딩을 일반 텍스트로 렌더링
                          h1: ({children}) => <span className="font-bold text-lg">{children}</span>,
                          h2: ({children}) => <span className="font-bold text-base">{children}</span>,
                          h3: ({children}) => <span className="font-bold text-base">{children}</span>,
                          h4: ({children}) => <span className="font-bold text-base">{children}</span>,
                          h5: ({children}) => <span className="font-bold text-base">{children}</span>,
                          h6: ({children}) => <span className="font-bold text-base">{children}</span>,
                        }}
                      >
                        {preprocessMarkdown(formatAIResponse(message.content)).trimEnd()}
                      </ReactMarkdown>
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
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M5 13l4 4L19 7"
                      />
                    ) : (
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
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
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"
                    />
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
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.60L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"
                    />
                  </svg>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }
);


// 스타일 추가
const globalStyles = `
  /* 모던 테이블 스타일 */
  .table-wrapper {
    position: relative;
    margin: 1.5rem 0;
  }
  
  .table-wrapper table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 0 0 1px rgba(0,0,0,0.1), 0 4px 12px rgba(0,0,0,0.05);
  }
  
  .table-wrapper thead {
    background: linear-gradient(to bottom, #f8f9fa, #e9ecef);
  }
  
  .table-wrapper th {
    border-bottom: 2px solid #dee2e6;
    border-right: 1px solid #e9ecef;
    padding: 14px 18px;
    font-weight: 600;
    text-align: left;
    color: #495057;
    font-size: 14px;
    letter-spacing: 0.3px;
    text-transform: uppercase;
  }
  
  .table-wrapper th:last-child {
    border-right: none;
  }
  
  .table-wrapper tbody tr {
    transition: background-color 0.2s ease;
  }
  
  .table-wrapper tbody tr:hover {
    background-color: #f8f9fa;
  }
  
  .table-wrapper td {
    border-bottom: 1px solid #e9ecef;
    border-right: 1px solid #f1f3f5;
    padding: 14px 18px;
    color: #212529;
    font-size: 14px;
  }
  
  .table-wrapper td:last-child {
    border-right: none;
  }
  
  .table-wrapper tbody tr:last-child td {
    border-bottom: none;
  }
  
  /* 다크모드 테이블 */
  .dark .table-wrapper table {
    box-shadow: 0 0 0 1px rgba(255,255,255,0.1), 0 4px 12px rgba(0,0,0,0.3);
  }
  
  .dark .table-wrapper thead {
    background: linear-gradient(to bottom, #2a2a2a, #1a1a1a);
  }
  
  .dark .table-wrapper th {
    border-bottom-color: #444;
    border-right-color: #333;
    color: #e9ecef;
  }
  
  .dark .table-wrapper tbody tr:hover {
    background-color: rgba(255,255,255,0.03);
  }
  
  .dark .table-wrapper td {
    border-bottom-color: #2a2a2a;
    border-right-color: #2a2a2a;
    color: #dee2e6;
  }
  
  /* 테이블 복사 버튼 */
  .table-wrapper:hover .table-copy-btn {
    opacity: 1;
  }
  
  .table-copy-btn {
    position: absolute;
    bottom: -8px;
    right: -8px;
    opacity: 0;
    transition: all 0.2s ease;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 8px;
    border-radius: 10px;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    cursor: pointer;
    z-index: 10;
    transform: scale(0.9);
  }
  
  .table-copy-btn:hover {
    transform: scale(1);
    box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
  }
  
  /* 불릿 포인트 크기 */
  .prose ul li {
    list-style: disc;
  }
  
  .prose ul li::marker {
    font-size: 1.5em;
    color: #4b5563;
  }
  
  .dark .prose ul li::marker {
    color: #d1d5db;
  }
`;

// 스타일을 document head에 추가
if (typeof document !== 'undefined') {
  const styleElement = document.createElement('style');
  styleElement.textContent = globalStyles;
  if (!document.head.querySelector('[data-simple-markdown-styles]')) {
    styleElement.setAttribute('data-simple-markdown-styles', 'true');
    document.head.appendChild(styleElement);
  }
}

export default SimpleChatMessage;
