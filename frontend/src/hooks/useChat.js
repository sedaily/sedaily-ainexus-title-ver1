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
  const [streamingMessageId, setStreamingMessageId] = useState(null);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const {
    isExecuting: isGenerating,
    isStreaming,
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
   * 스트리밍 응답 처리 함수
   */
  const handleStreamingResponse = useCallback(
    (chunk, metadata) => {
      setMessages((prev) => {
        const updatedMessages = [...prev];
        const streamingMsgIndex = updatedMessages.findIndex(
          (msg) => msg.id === streamingMessageId
        );

        if (streamingMsgIndex !== -1) {
          // 기존 스트리밍 메시지 업데이트
          updatedMessages[streamingMsgIndex] = {
            ...updatedMessages[streamingMsgIndex],
            content: updatedMessages[streamingMsgIndex].content + chunk,
            isLoading: true,
            isStreaming: true,
          };
        }

        return updatedMessages;
      });

      // 스크롤 조정
      scrollToBottom();
    },
    [streamingMessageId, scrollToBottom]
  );

  /**
   * 스트리밍 완료 처리 함수
   */
  const handleStreamingComplete = useCallback(
    (result) => {
      setMessages((prev) => {
        const updatedMessages = [...prev];
        const streamingMsgIndex = updatedMessages.findIndex(
          (msg) => msg.id === streamingMessageId
        );

        if (streamingMsgIndex !== -1) {
          // 스트리밍 메시지 완료 처리
          updatedMessages[streamingMsgIndex] = {
            ...updatedMessages[streamingMsgIndex],
            content: result.result,
            isLoading: false,
            isStreaming: false,
            performance_metrics: result.performance_metrics,
            model_info: result.model_info,
            timestamp: new Date(),
          };
        }

        return updatedMessages;
      });

      // 스트리밍 ID 초기화
      setStreamingMessageId(null);

      // 스크롤 조정
      scrollToBottom();
    },
    [streamingMessageId, scrollToBottom]
  );

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

    // 스트리밍 메시지 ID 생성
    const streamMsgId = "streaming-" + Date.now();
    setStreamingMessageId(streamMsgId);

    // 스트리밍 응답을 위한 초기 메시지
    const streamingMessage = {
      id: streamMsgId,
      type: "assistant",
      content: "",
      timestamp: new Date(),
      isLoading: true,
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, streamingMessage]);
    setInputValue("");

    try {
      const orchestrationData = {
        userInput: userMessage.content,
        chat_history: messages
          .filter((msg) => !msg.isLoading && !msg.isError)
          .map((msg) => ({
            role: msg.type === "user" ? "user" : "assistant",
            content: msg.content,
          })),
      };

      // 스트리밍 옵션 설정
      const streamingOptions = {
        useStreaming: true,
        chat_history: orchestrationData.chat_history,
        onChunk: handleStreamingResponse,
        onError: (error) => {
          console.error("스트리밍 오류:", error);

          // 오류 메시지로 변환
          setMessages((prev) => {
            const updatedMessages = [...prev];
            const streamingMsgIndex = updatedMessages.findIndex(
              (msg) => msg.id === streamingMessageId
            );

            if (streamingMsgIndex !== -1) {
              updatedMessages[streamingMsgIndex] = {
                ...updatedMessages[streamingMsgIndex],
                content:
                  "메시지 처리 중 오류가 발생했습니다. 다시 시도해주세요.",
                isLoading: false,
                isStreaming: false,
                isError: true,
                timestamp: new Date(),
              };
            }

            return updatedMessages;
          });

          setStreamingMessageId(null);
        },
        onComplete: handleStreamingComplete,
      };

      // 스트리밍 방식으로 실행
      await executeOrchestration(userMessage.content, streamingOptions);

      // 스트리밍에서는 pollOrchestrationResult 호출이 필요 없음
      // 모든 처리는 콜백에서 이루어짐
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

      setMessages((prev) => {
        // 스트리밍 메시지를 찾아 제거
        const filteredMessages = prev.filter(
          (msg) => msg.id !== streamingMessageId
        );
        return [...filteredMessages, errorMessage];
      });

      setStreamingMessageId(null);
    }
  }, [
    inputValue,
    isGenerating,
    executeOrchestration,
    handleStreamingResponse,
    handleStreamingComplete,
    streamingMessageId,
    messages,
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
    setStreamingMessageId(null);
    resetOrchestration();
  }, [resetOrchestration]);

  return {
    messages,
    inputValue,
    setInputValue,
    copiedMessage,
    isGenerating,
    isStreaming,
    streamingMessageId,
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
