import { useState, useEffect, useRef, useCallback } from "react";
import { toast } from "react-hot-toast";
import { copyToClipboard } from "../utils/clipboard";
import { useOrchestration } from "./useOrchestration";

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

  // 초기 환영 메시지 설정
  useEffect(() => {
    const welcomeMessage = {
      id: "welcome",
      type: "assistant",
      content: `안녕하세요! 저는 ${projectName}의 AI 제목 작가입니다.\n\n기사 내용을 입력해주시면 다양한 스타일의 제목을 제안해드릴게요. 제목을 수정하거나 다른 스타일로 바꾸고 싶으시면 언제든 말씀해주세요!`,
      timestamp: new Date(),
    };
    setMessages([welcomeMessage]);
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
      id: Date.now() + Math.random(),
      type: "user",
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentInput = inputValue;
    setInputValue("");

    try {
      // 로딩 메시지 추가
      const loadingMessage = {
        id: "loading-" + Date.now(),
        type: "assistant",
        content:
          "AI가 제목을 생성하고 있습니다...\n\n단계별로 처리 중이니 잠시만 기다려주세요!",
        timestamp: new Date(),
        isLoading: true,
      };

      setMessages((prev) => [...prev, loadingMessage]);

      // 오케스트레이션 실행
      const result = await executeOrchestration(currentInput, {
        enabledSteps: promptCards
          .filter((card) => card.enabled)
          .map((card) => card.category),
      });

      if (result && result.result) {
        // 직접 응답 처리 (폴링 불필요)
        // 실제 API 응답에서 result 필드에 제목들이 문자열로 들어있음
        const titleText = result.result;
        
        // 번호가 매겨진 제목들을 파싱
        const titles = titleText
          .split('\n')
          .map(line => line.trim())
          .filter(line => line && /^\d+\./.test(line))
          .map(line => line.replace(/^\d+\.\s*/, ''))
          .slice(0, 5); // 최대 5개

        const responseMessage = {
          id: "response-" + Date.now(),
          type: "assistant",
          content: `**생성된 제목 후보들입니다:**\n\n${titles
            .map((title, i) => `**${i + 1}.** ${title}`)
            .join(
              "\n\n"
            )}\n\n원하시는 제목이 있으시거나 수정이 필요하시면 말씀해주세요!`,
          timestamp: new Date(),
          titles: titles,
        };

        // 로딩 메시지 제거하고 결과 메시지 추가
        setMessages((prev) =>
          prev.filter((msg) => !msg.isLoading).concat([responseMessage])
        );
      } else {
        // 결과가 없는 경우 에러 처리
        console.error("AI 응답 오류: 결과가 없습니다", result);

        const errorMessage = {
          id: "error-" + Date.now(),
          type: "assistant",
          content:
            "죄송합니다. 제목 생성 중 오류가 발생했습니다. 다시 시도해주세요.",
          timestamp: new Date(),
          isError: true,
        };

        setMessages((prev) =>
          prev.filter((msg) => !msg.isLoading).concat([errorMessage])
        );
      }
    } catch (error) {
      console.error("메시지 전송 실패:", error);

      const errorMessage = {
        id: "error-" + Date.now(),
        type: "assistant",
        content:
          "죄송합니다. 메시지 처리 중 오류가 발생했습니다. 다시 시도해주세요.",
        timestamp: new Date(),
        isError: true,
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
    const success = await copyToClipboard(title, "제목이 복사되었습니다!");
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
