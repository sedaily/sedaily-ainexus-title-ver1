import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import {
  ClipboardDocumentIcon,
  CheckCircleIcon,
  DocumentDuplicateIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";
import { ChatMessageSkeleton } from "./skeleton/SkeletonComponents";

// 스트리밍 표시 컴포넌트
const AnimatedStreamingIndicator = () => {
  return (
    <motion.div
      className="inline-flex items-center mt-2 px-2 py-1 bg-blue-50 dark:bg-blue-900 rounded-lg text-blue-600 dark:text-blue-400 text-xs font-medium"
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      <motion.div
        className="relative h-2 w-2 mr-2"
        animate={{ scale: [1, 1.2, 1] }}
        transition={{ repeat: Infinity, duration: 1.5 }}
      >
        <div className="absolute animate-ping h-2 w-2 rounded-full bg-blue-400 opacity-75"></div>
        <div className="absolute h-2 w-2 rounded-full bg-blue-600 dark:bg-blue-400"></div>
      </motion.div>
      <motion.span
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ repeat: Infinity, duration: 2 }}
      >
        스트리밍 중...
      </motion.span>
    </motion.div>
  );
};

// 간단한 로딩 표시
const AnimatedLoadingIndicator = () => {
  return (
    <motion.div
      className="flex items-center text-blue-600 dark:text-blue-400 text-sm"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4 }}
    >
      <motion.div
        className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 dark:border-blue-400 mr-2"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 1 }}
      />
      <span>답변 생성 중...</span>
    </motion.div>
  );
};

// 오류 상세 정보 표시 컴포넌트
const AnimatedErrorDetails = ({ errorDetails }) => {
  if (!errorDetails) return null;

  return (
    <motion.div
      className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800"
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex items-center text-sm text-red-700 dark:text-red-400 mb-2">
        <ExclamationTriangleIcon className="h-4 w-4 mr-2" />
        <span className="font-medium">오류 상세 정보</span>
      </div>
      <div className="text-xs text-red-600 dark:text-red-400 space-y-1">
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
    </motion.div>
  );
};

const AnimatedChatMessage = ({
  message,
  onCopyMessage,
  onCopyTitle,
  copiedMessage,
}) => {
  const isUser = message.type === "user";

  const messageVariants = {
    initial: {
      opacity: 0,
      y: 20,
      scale: 0.95,
    },
    animate: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 25,
        staggerChildren: 0.1,
      },
    },
  };

  const contentVariants = {
    initial: { opacity: 0, y: 10 },
    animate: {
      opacity: 1,
      y: 0,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 25,
      },
    },
  };

  const buttonVariants = {
    initial: { opacity: 0, scale: 0.8 },
    animate: {
      opacity: 1,
      scale: 1,
      transition: {
        type: "spring",
        stiffness: 400,
        damping: 20,
      },
    },
    hover: {
      scale: 1.05,
      transition: {
        type: "spring",
        stiffness: 400,
        damping: 20,
      },
    },
    tap: {
      scale: 0.95,
      transition: {
        type: "spring",
        stiffness: 600,
        damping: 30,
      },
    },
  };

  return (
    <motion.div
      className={`group relative ${isUser ? "ml-8" : "mr-8"} mb-6`}
      variants={messageVariants}
      initial="initial"
      animate="animate"
    >
      <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
        {isUser ? (
          // 사용자 메시지 - 디자인된 박스
          <motion.div
            className="max-w-[85%] rounded-lg px-6 py-4 bg-blue-600 dark:bg-blue-700 text-white"
            variants={contentVariants}
            whileHover={{ scale: 1.01 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
          >
            <motion.div
              className="text-base font-medium whitespace-pre-wrap leading-relaxed"
              variants={contentVariants}
            >
              {message.content}
            </motion.div>
            <motion.div
              className="text-xs mt-3 font-medium text-blue-100 dark:text-blue-200"
              variants={contentVariants}
            >
              {message.timestamp?.toLocaleTimeString() || ""}
            </motion.div>
          </motion.div>
        ) : (
          // AI 메시지 - 박스 없이 깔끔하게
          <motion.div className="max-w-[85%] w-full" variants={contentVariants}>
            {/* AI 응답 내용 */}
            <motion.div
              className="whitespace-pre-wrap leading-relaxed text-gray-800 dark:text-gray-200"
              variants={contentVariants}
            >
              {message.isError ? (
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.4 }}
                >
                  <div className="text-red-600 dark:text-red-400 text-base">
                    {message.content}
                  </div>
                  <AnimatedErrorDetails errorDetails={message.errorDetails} />
                </motion.div>
              ) : message.isLoading ? (
                <div>
                  {message.isStreaming ? (
                    // 스트리밍 메시지 표시
                    <div>
                      {message.content ? (
                        <div className="prose prose-base max-w-none prose-p:text-gray-800 dark:prose-p:text-white prose-headings:text-gray-900 dark:prose-headings:text-white prose-strong:text-gray-900 dark:prose-strong:text-white prose-ul:text-gray-800 dark:prose-ul:text-white prose-li:text-gray-800 dark:prose-li:text-white prose-code:text-gray-800 dark:prose-code:text-white prose-pre:bg-transparent dark:prose-pre:bg-transparent">
                          <ReactMarkdown>{message.content}</ReactMarkdown>
                        </div>
                      ) : (
                        <div className="text-blue-600 dark:text-blue-400 text-base font-medium">
                          응답을 생성하는 중...
                        </div>
                      )}
                      <AnimatedStreamingIndicator />
                    </div>
                  ) : (
                    // 스켈레톤 UI 표시
                    <ChatMessageSkeleton isUser={false} />
                  )}
                </div>
              ) : (
                <div className="prose prose-base max-w-none prose-p:text-gray-800 dark:prose-p:text-white prose-headings:text-gray-900 dark:prose-headings:text-white prose-strong:text-gray-900 dark:prose-strong:text-white prose-ul:text-gray-800 dark:prose-ul:text-white prose-li:text-gray-800 dark:prose-li:text-white prose-code:text-gray-800 dark:prose-code:text-white prose-pre:bg-transparent dark:prose-pre:bg-transparent">
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>
              )}
            </motion.div>

            {/* 제목 복사 버튼들 */}
            <AnimatePresence>
              {message.titles && (
                <motion.div
                  className="mt-4 pt-3"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  transition={{ duration: 0.3 }}
                >
                  <div className="flex flex-wrap gap-2">
                    {message.titles.map((title, index) => (
                      <motion.button
                        key={index}
                        onClick={() => onCopyTitle(title, message.id, index)}
                        className={`flex items-center px-3 py-1.5 bg-gray-50 dark:bg-dark-tertiary border-0 text-gray-800 dark:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-dark-secondary transition-colors text-sm font-medium ${
                          copiedMessage === `${message.id}_title_${index}`
                            ? "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-700"
                            : "bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600"
                        }`}
                        variants={buttonVariants}
                        initial="initial"
                        animate="animate"
                        whileHover="hover"
                        whileTap="tap"
                        custom={index}
                      >
                        <motion.div
                          animate={
                            copiedMessage === `${message.id}_title_${index}`
                              ? { scale: [1, 1.2, 1] }
                              : {}
                          }
                          transition={{ duration: 0.3 }}
                        >
                          {copiedMessage === `${message.id}_title_${index}` ? (
                            <CheckCircleIcon className="h-3 w-3 mr-1" />
                          ) : (
                            <DocumentDuplicateIcon className="h-3 w-3 mr-1" />
                          )}
                        </motion.div>
                        제목 {index + 1} 복사
                      </motion.button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* 전체 메시지 복사 버튼 및 타임스탬프 */}
            {!message.isLoading && !message.isError && (
              <motion.div
                className="flex items-center justify-between mt-3"
                variants={contentVariants}
              >
                <motion.button
                  onClick={() => onCopyMessage(message.content)}
                  className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                  variants={buttonVariants}
                  initial="initial"
                  animate="animate"
                  whileHover="hover"
                  whileTap="tap"
                >
                  {copiedMessage === message.content ? (
                    <>
                      <CheckCircleIcon className="h-4 w-4 text-green-500" />
                      <span className="text-green-600 dark:text-green-400">
                        복사 완료
                      </span>
                    </>
                  ) : (
                    <>
                      <ClipboardDocumentIcon className="h-4 w-4" />
                      <span>답변 복사</span>
                    </>
                  )}
                </motion.button>
                <div className="text-xs text-gray-400 dark:text-gray-500">
                  {message.timestamp?.toLocaleTimeString() || ""}
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

export default AnimatedChatMessage;
