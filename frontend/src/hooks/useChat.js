import { useState, useEffect, useRef, useCallback } from "react";
import { toast } from "react-hot-toast";
import { copyToClipboard } from "../utils/clipboard";
import { useOrchestration } from "./useOrchestration";

/**
 * AI 응답을 파싱하고 UI에 맞는 메시지 객체로 변환
 */
const processAIResponse = (result) => {
  if (!result || !result.result) {
    console.error("AI 응답 오류: 결과가 없습니다", result);
    return {
      id: "error-" + Date.now(),
      type: "assistant",
      content: "처리 중 오류가 발생했습니다. 다시 시도해주세요.",
      timestamp: new Date(),
      isError: true,
    };
  }

  // LangChain과 직접 통신하므로, 결과가 바로 content가 됨
  const responseContent = result.result;

  return {
    id: "response-" + Date.now(),
    type: "assistant",
    content: responseContent,
    timestamp: new Date(),
    // 성능 메트릭 포함
    performance_metrics: result.performance_metrics,
    model_info: result.model_info,
  };
};

/**
 * 채팅 기능을 위한 커스텀 훅
 * @param {string} projectId - 프로젝트 ID
 * @param {string} projectName - 프로젝트 이름
 * @param {Array} promptCards - 프롬프트 카드 배열
 * @returns {Object} - 채팅 관련 상태와 함수들
 */
export const useChat = (projectId, projectName, promptCards = []) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [copiedMessage, setCopiedMessage] = useState(null);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const {
    isExecuting: isGenerating,
    executeOrchestration,
    pollOrchestrationResult,
    resetOrchestration,
  } = useOrchestration(projectId);

  // 초기 환영 메시지 설정 - 제거됨 (빈 상태로 시작)
  useEffect(() => {
    setMessages([]); // 빈 배열로 시작
  }, [projectName]);

  // 메시지 추가 시 스크롤 하단으로
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  /**
   * 메시지 전송
   */
  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || isGenerating) return;

    const userMessage = {
      id: "user-" + Date.now(),
      type: "user",
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    // 개선된 로딩 메시지
    const loadingMessage = {
      id: "loading-" + Date.now(),
      type: "assistant",
      content: "AI가 답변을 생성하고 있습니다...",
      timestamp: new Date(),
      isLoading: true,
      loadingProgress: {
        stage: "initializing",
        message: "요청을 처리하고 있습니다...",
        percentage: 10,
      },
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setInputValue("");

    try {
      // 프롬프트 분석 단계 표시
      setMessages((prev) =>
        prev.map((msg) =>
          msg.isLoading
            ? {
                ...msg,
                content: "프롬프트를 분석하고 있습니다...",
                loadingProgress: {
                  stage: "analyzing",
                  message: "프로젝트 프롬프트를 불러오는 중...",
                  percentage: 25,
                },
              }
            : msg
        )
      );

      // AI 처리 단계 표시
      setTimeout(() => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.isLoading
              ? {
                  ...msg,
                  content: "AI 모델이 응답을 생성하고 있습니다...",
                  loadingProgress: {
                    stage: "generating",
                    message:
                      "고품질 응답을 위해 분석 중입니다. 잠시만 기다려주세요...",
                    percentage: 60,
                  },
                }
              : msg
          )
        );
      }, 1000);

      // 완료 단계 표시
      setTimeout(() => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.isLoading
              ? {
                  ...msg,
                  content: "응답을 정리하고 있습니다...",
                  loadingProgress: {
                    stage: "finalizing",
                    message: "거의 완료되었습니다...",
                    percentage: 85,
                  },
                }
              : msg
          )
        );
      }, 3000);

      const orchestrationData = {
        userInput: userMessage.content,
        chat_history: messages
          .filter((msg) => !msg.isLoading && !msg.isError)
          .map((msg) => ({
            role: msg.type === "user" ? "user" : "assistant",
            content: msg.content,
          })),
      };

      // 수정된 호출 방식: 문자열과 옵션 객체로 분리
      const result = await executeOrchestration(userMessage.content, {
        chat_history: messages
          .filter((msg) => !msg.isLoading && !msg.isError)
          .map((msg) => ({
            role: msg.type === "user" ? "user" : "assistant",
            content: msg.content,
          })),
      });
      await pollOrchestrationResult();

      // 로딩 메시지 제거하고 실제 응답 추가
      const responseMessage = processAIResponse(result);
      setMessages((prev) =>
        prev.filter((msg) => !msg.isLoading).concat([responseMessage])
      );
    } catch (error) {
      console.error("메시지 전송 실패:", error);

      // 개선된 오류 메시지
      const errorType = error.code === "ECONNABORTED" ? "timeout" : "general";
      const errorMessage = {
        id: "error-" + Date.now(),
        type: "assistant",
        content:
          errorType === "timeout"
            ? "처리 시간이 초과되었습니다. 요청이 복잡하거나 서버가 바쁜 상태일 수 있습니다. 잠시 후 다시 시도해주세요."
            : "메시지 처리 중 오류가 발생했습니다. 네트워크 연결을 확인하고 다시 시도해주세요.",
        timestamp: new Date(),
        isError: true,
        errorDetails: {
          type: errorType,
          message: error.message,
          status: error.response?.status,
        },
      };

      setMessages((prev) =>
        prev.filter((msg) => !msg.isLoading).concat([errorMessage])
      );
    }
  }, [
    inputValue,
    isGenerating,
    executeOrchestration,
    pollOrchestrationResult,
    promptCards,
    messages, // messages를 의존성에 추가
  ]);

  /**
   * Enter 키로 전송
   */
  const handleKeyPress = useCallback(
    (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    },
    [handleSendMessage]
  );

  /**
   * 메시지 복사
   */
  const handleCopyMessage = useCallback(async (content, messageId) => {
    const success = await copyToClipboard(content);
    if (success) {
      setCopiedMessage(messageId);
      setTimeout(() => setCopiedMessage(null), 2000);
    }
  }, []);

  /**
   * 개별 제목 복사
   */
  const handleCopyTitle = useCallback(async (title, messageId, index) => {
    const success = await copyToClipboard(title, "복사되었습니다!");
    if (success) {
      setCopiedMessage(`${messageId}_title_${index}`);
      setTimeout(() => setCopiedMessage(null), 2000);
    }
  }, []);

  /**
   * 채팅 초기화
   */
  const resetChat = useCallback(() => {
    setMessages([]);
    setInputValue("");
    setCopiedMessage(null);
    resetOrchestration();
  }, [resetOrchestration]);

  return {
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
    resetChat,
    scrollToBottom,
  };
};
