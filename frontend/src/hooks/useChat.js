import { useState, useEffect, useRef, useCallback } from "react";
import { toast } from "react-hot-toast";
import { copyToClipboard } from "../utils/clipboard";
import { useOrchestration } from "./useOrchestration";
import { useWebSocket } from "./useWebSocket";

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
  const [canSendMessage, setCanSendMessage] = useState(true);
  const [inputHeight, setInputHeight] = useState(24); // 동적 높이 관리
  const [selectedModel, setSelectedModel] = useState("anthropic.claude-3-5-sonnet-20241022-v2:0");
  const streamingMessageIdRef = useRef(null);
  const currentWebSocketRef = useRef(null);
  const currentExecutionIdRef = useRef(null);
  

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // 사용자 스크롤 상태 추적
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const scrollContainerRef = useRef(null);
  const lastScrollTopRef = useRef(0);

  const {
    isExecuting: isGenerating,
    isStreaming,
    executeOrchestration,
    pollOrchestrationResult,
    resetOrchestration,
  } = useOrchestration(projectId);

  // WebSocket 훅 추가
  const {
    isConnected: wsConnected,
    isConnecting: wsConnecting,
    error: wsError,
    startStreaming: wsStartStreaming,
    addMessageListener,
    removeMessageListener,
  } = useWebSocket(projectId);

  // 초기 환영 메시지 설정 - 제거됨 (빈 상태로 시작)
  useEffect(() => {
    setMessages([]); // 빈 배열로 시작
  }, [projectName]);

  // 사용자 스크롤 감지 함수
  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current) return;

    const container = scrollContainerRef.current;
    const currentScrollTop = container.scrollTop;
    const maxScrollTop = container.scrollHeight - container.clientHeight;

    // 사용자가 수동으로 스크롤했는지 감지
    if (Math.abs(currentScrollTop - lastScrollTopRef.current) > 2) {
      const isAtBottom = currentScrollTop >= maxScrollTop - 20;

      // 하단에 있을 때만 자동 스크롤 허용, 그 외는 사용자 스크롤 모드
      setIsUserScrolling(!isAtBottom);
    }

    lastScrollTopRef.current = currentScrollTop;
  }, []);

  const scrollToBottom = useCallback(() => {
    // 사용자가 스크롤 중이 아닐 때만 자동 스크롤
    if (!isUserScrolling && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [isUserScrolling]);

  // 메시지 추가 시 스크롤 하단으로 (사용자 스크롤 중이 아닐 때만)
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // WebSocket 메시지 리스너 설정
  useEffect(() => {
    const handleWebSocketMessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WebSocket 메시지 수신:", data);

        const currentStreamingId = streamingMessageIdRef.current;

        switch (data.type) {
          case "stream_start":
            console.log("WebSocket 스트리밍 시작");
            break;

          case "progress":
            // 진행 상황 로그만 남기고 UI 업데이트는 제거
            console.log(`진행 상황: ${data.step} (${data.progress}%)`);
            break;

          case "stream_chunk":
            if (currentStreamingId) {
              setMessages((prev) => {
                const updatedMessages = [...prev];
                const streamingMsgIndex = updatedMessages.findIndex(
                  (msg) => msg.id === currentStreamingId
                );

                if (streamingMsgIndex !== -1) {
                  // 기존 내용에 새 청크 추가
                  const currentContent =
                    updatedMessages[streamingMsgIndex].content || "";

                  updatedMessages[streamingMsgIndex] = {
                    ...updatedMessages[streamingMsgIndex],
                    content: currentContent + data.content,
                    isLoading: true,
                    isStreaming: true,
                  };
                }

                return updatedMessages;
              });
              // 스트리밍 중에는 사용자가 스크롤 중이 아닐 때만 자동 스크롤
              if (!isUserScrolling) {
                scrollToBottom();
              }
            }
            break;

          case "stream_complete":
            if (currentStreamingId) {
              setMessages((prev) => {
                const updatedMessages = [...prev];
                const streamingMsgIndex = updatedMessages.findIndex(
                  (msg) => msg.id === currentStreamingId
                );

                if (streamingMsgIndex !== -1) {
                  updatedMessages[streamingMsgIndex] = {
                    ...updatedMessages[streamingMsgIndex],
                    content: data.fullContent,
                    isLoading: false,
                    isStreaming: false,
                    timestamp: new Date(),
                  };
                }

                return updatedMessages;
              });
              streamingMessageIdRef.current = null;
              scrollToBottom();
            }
            break;

          case "error":
            console.error("WebSocket 스트리밍 오류:", data.message);
            if (currentStreamingId) {
              setMessages((prev) => {
                const updatedMessages = [...prev];
                const streamingMsgIndex = updatedMessages.findIndex(
                  (msg) => msg.id === currentStreamingId
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
              streamingMessageIdRef.current = null;
            }
            toast.error(data.message);
            break;

          default:
            console.log("알 수 없는 WebSocket 메시지 타입:", data.type);
        }
      } catch (error) {
        console.error("WebSocket 메시지 파싱 오류:", error);
      }
    };

    if (wsConnected) {
      addMessageListener(handleWebSocketMessage);
    }

    return () => {
      if (wsConnected) {
        removeMessageListener(handleWebSocketMessage);
      }
    };
  }, [wsConnected, addMessageListener, removeMessageListener, scrollToBottom]);

  /**
   * 스트리밍 응답 처리 함수
   */
  const handleStreamingResponse = useCallback(
    (chunk, metadata) => {
      const currentStreamingId = streamingMessageIdRef.current;

      console.log("청크 수신:", chunk, "스트리밍 ID:", currentStreamingId);

      if (!currentStreamingId) {
        console.error("스트리밍 ID가 없습니다!");
        return;
      }

      setMessages((prev) => {
        const updatedMessages = [...prev];
        const streamingMsgIndex = updatedMessages.findIndex(
          (msg) => msg.id === currentStreamingId
        );

        if (streamingMsgIndex !== -1) {
          // 기존 스트리밍 메시지 업데이트
          updatedMessages[streamingMsgIndex] = {
            ...updatedMessages[streamingMsgIndex],
            content: updatedMessages[streamingMsgIndex].content + chunk,
            isLoading: true,
            isStreaming: true,
          };
          console.log(
            "스트리밍 메시지 업데이트 성공:",
            updatedMessages[streamingMsgIndex].content
          );
        } else {
          console.error("스트리밍 메시지를 찾을 수 없음:", currentStreamingId);
        }

        return updatedMessages;
      });

      // 스크롤 조정 (사용자가 스크롤 중이 아닐 때만)
      if (!isUserScrolling) {
        scrollToBottom();
      }
    },
    [scrollToBottom, isUserScrolling]
  );

  /**
   * 스트리밍 완료 처리 함수
   */
  const handleStreamingComplete = useCallback(
    (result) => {
      const currentStreamingId = streamingMessageIdRef.current;

      console.log("스트리밍 완료:", result, "스트리밍 ID:", currentStreamingId);

      if (!currentStreamingId) {
        console.error("스트리밍 완료 처리 중 ID가 없습니다!");
        return;
      }

      setMessages((prev) => {
        const updatedMessages = [...prev];
        const streamingMsgIndex = updatedMessages.findIndex(
          (msg) => msg.id === currentStreamingId
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
          console.log(
            "스트리밍 완료 처리 성공:",
            updatedMessages[streamingMsgIndex].content
          );
        } else {
          console.error(
            "스트리밍 완료 처리 중 메시지를 찾을 수 없음:",
            currentStreamingId
          );
        }

        return updatedMessages;
      });

      // 스트리밍 ID 초기화
      streamingMessageIdRef.current = null;

      // 입력 활성화
      console.log("WebSocket 스트리밍 완료 - 입력 활성화");
      setCanSendMessage(true);

      // 스크롤 조정 (스트리밍 완료 시에는 항상 하단으로)
      scrollToBottom();
    },
    [scrollToBottom]
  );

  /**
   * 스트리밍 중단 함수
   */
  const handleStopGeneration = useCallback(() => {
    console.log("생성 중단 요청");

    // WebSocket 연결 종료
    if (currentWebSocketRef.current) {
      currentWebSocketRef.current.close();
      currentWebSocketRef.current = null;
    }

    // 현재 실행 중인 작업 중단
    if (currentExecutionIdRef.current) {
      // 여기서 실제 API 호출 중단 로직을 추가할 수 있습니다
      currentExecutionIdRef.current = null;
    }

    // 스트리밍 메시지 상태 업데이트
    const currentStreamingId = streamingMessageIdRef.current;
    if (currentStreamingId) {
      setMessages((prev) => {
        const updatedMessages = [...prev];
        const streamingMsgIndex = updatedMessages.findIndex(
          (msg) => msg.id === currentStreamingId
        );

        if (streamingMsgIndex !== -1) {
          updatedMessages[streamingMsgIndex] = {
            ...updatedMessages[streamingMsgIndex],
            content:
              updatedMessages[streamingMsgIndex].content +
              "\n\n[생성이 중단되었습니다]",
            isLoading: false,
            isStreaming: false,
            timestamp: new Date(),
          };
        }

        return updatedMessages;
      });

      streamingMessageIdRef.current = null;
    }

    // 입력 가능 상태로 복원
    setCanSendMessage(true);

    // orchestration 상태 리셋
    resetOrchestration();

    toast.success("생성이 중단되었습니다");
  }, [resetOrchestration]);

  /**
   * 입력창 높이 자동 조절
   */
  const adjustInputHeight = useCallback((value) => {
    if (!value.trim()) {
      setInputHeight(24); // 기본 높이
      return;
    }
    
    // 줄 수 계산 (대략적)
    const lines = value.split('\n').length;
    const charBasedLines = Math.ceil(value.length / 80); // 80자당 1줄로 추정
    const estimatedLines = Math.max(lines, charBasedLines);
    
    // 높이 계산 (lineHeight: 1.4, fontSize: 16px)
    let calculatedHeight;
    if (estimatedLines <= 3) {
      calculatedHeight = 24 + (estimatedLines - 1) * 22; // 기본 + 추가 줄
    } else if (estimatedLines <= 10) {
      calculatedHeight = 150 + (estimatedLines - 6) * 15; // 중간 범위
    } else {
      calculatedHeight = Math.min(400, 150 + (estimatedLines - 6) * 12); // 최대 400px
    }
    
    setInputHeight(Math.max(24, calculatedHeight));
  }, []);
  
  /**
   * 입력값 변경 처리
   */
  const handleInputChange = useCallback((value) => {
    setInputValue(value);
    adjustInputHeight(value);
  }, [adjustInputHeight]);

  /**
   * 메시지 전송
   */
  const handleSendMessage = useCallback(async () => {
    console.log("해들 전송 호출:", {
      inputValue: inputValue.trim(),
      isGenerating,
      canSendMessage,
    });

    if (!inputValue.trim() || isGenerating) {
      console.log("전송 중단: 조건 부족");
      return;
    }

    // 입력 비활성화
    console.log("입력 비활성화");
    setCanSendMessage(false);

    const userMessage = {
      id: "user-" + Date.now(),
      type: "user",
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    // 스트리밍 메시지 ID 생성
    const streamMsgId = "streaming-" + Date.now();
    streamingMessageIdRef.current = streamMsgId;

    console.log("새 스트리밍 메시지 ID 생성:", streamMsgId);

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
    setInputHeight(24); // 입력창 높이 초기화

    // 기존 메시지 + 현재 사용자 메시지를 포함한 대화 히스토리 생성
    const allMessages = [...messages, userMessage];
    const chatHistory = allMessages
      .filter((msg) => !msg.isLoading && !msg.isError && !msg.isStreaming)
      .map((msg) => ({
        role: msg.type === "user" ? "user" : "assistant",
        content: msg.content,
      }));

    // 최대 대화 기억 설정 (최근 50개 메시지로 최대 메모리 유지)
    const maxHistoryLength = 50;
    const trimmedChatHistory = chatHistory.slice(-maxHistoryLength);

    console.log("대화 히스토리 생성:", {
      totalMessages: allMessages.length,
      fullHistoryLength: chatHistory.length,
      trimmedHistoryLength: trimmedChatHistory.length,
      maxHistoryLength: maxHistoryLength,
      recentHistory: trimmedChatHistory.slice(-6), // 최근 6개만 로그에 표시
    });

    try {
      // 프롬프트 카드 정보 추가 - 활성화된 카드만 필터링하고 백엔드 형식에 맞게 변환
      const safePromptCards = Array.isArray(promptCards) ? promptCards : [];
      const activePromptCards = safePromptCards
        .filter((card) => card.isActive !== false && card.enabled !== false)
        .map((card) => ({
          promptId: card.promptId || card.prompt_id,
          title: card.title || "Untitled",
          prompt_text: card.prompt_text || card.content || "",
          tags: card.tags || [],
          isActive: card.isActive !== false,
          stepOrder: card.stepOrder || 0,
        }))
        .filter((card) => card.prompt_text.trim()) // 프롬프트 내용이 있는 것만
        .sort((a, b) => (a.stepOrder || 0) - (b.stepOrder || 0)); // stepOrder로 정렬

      console.log("대화 전송 데이터 확인:", {
        messageContent: userMessage.content,
        chatHistoryLength: trimmedChatHistory.length,
        promptCardsCount: activePromptCards.length,
        chatHistory: trimmedChatHistory,
        promptCards: activePromptCards.map((card) => ({
          id: card.promptId,
          title: card.title,
          contentLength: card.prompt_text.length,
          stepOrder: card.stepOrder,
          hasContent: !!card.prompt_text.trim(),
        })),
      });

      // WebSocket 연결 확인 및 실시간 스트리밍 시도
      if (wsConnected) {
        console.log("WebSocket을 통한 실시간 스트리밍 시작");

        const success = wsStartStreaming(
          userMessage.content,
          trimmedChatHistory,
          activePromptCards,
          selectedModel
        );

        if (success) {
          // WebSocket 스트리밍 성공, 나머지는 리스너에서 처리
          return;
        } else {
          console.log("WebSocket 전송 실패, SSE 폴백 모드로 전환");
        }
      } else {
        console.log("WebSocket 미연결, SSE 모드 사용");
      }

      // WebSocket 실패 시 기존 SSE 방식으로 폴백
      const orchestrationData = {
        userInput: userMessage.content,
        chat_history: trimmedChatHistory,
        prompt_cards: activePromptCards,
        modelId: selectedModel,
      };

      console.log("백엔드 전송 데이터 최종 확인:", orchestrationData);

      // 스트리밍 옵션 설정
      const streamingOptions = {
        useStreaming: true,
        chat_history: orchestrationData.chat_history,
        prompt_cards: orchestrationData.prompt_cards,
        modelId: orchestrationData.modelId,
        onChunk: handleStreamingResponse,
        onError: (error) => {
          console.error("스트리밍 오류:", error);

          const currentStreamingId = streamingMessageIdRef.current;
          console.log("에러 처리 스트리밍 ID:", currentStreamingId);

          // 오류 메시지로 변환
          setMessages((prev) => {
            const updatedMessages = [...prev];
            const streamingMsgIndex = updatedMessages.findIndex(
              (msg) => msg.id === currentStreamingId
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

          streamingMessageIdRef.current = null;
        },
        onComplete: handleStreamingComplete,
      };

      // SSE 스트리밍 방식으로 실행
      await executeOrchestration(userMessage.content, streamingOptions);

      // SSE 스트리밍 완료 후 입력 활성화
      console.log("SSE 스트리밍 완료 - 입력 활성화");
      setCanSendMessage(true);
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
        const currentStreamingId = streamingMessageIdRef.current;
        const filteredMessages = prev.filter(
          (msg) => msg.id !== currentStreamingId
        );
        return [...filteredMessages, errorMessage];
      });

      streamingMessageIdRef.current = null;

      // 오류 발생 시도 입력 활성화
      setCanSendMessage(true);
    }

    // 전체 전송 과정 완료 후 입력 활성화 (보험용)
    setCanSendMessage(true);
  }, [
    inputValue,
    isGenerating,
    executeOrchestration,
    handleStreamingResponse,
    handleStreamingComplete,
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
    setCanSendMessage(true);
    streamingMessageIdRef.current = null;
    currentWebSocketRef.current = null;
    currentExecutionIdRef.current = null;
    resetOrchestration();
  }, [resetOrchestration]);

  return {
    messages,
    inputValue,
    setInputValue,
    handleInputChange, // 새로운 입력 핸들러
    copiedMessage,
    isGenerating,
    isStreaming,
    canSendMessage,
    streamingMessageId: streamingMessageIdRef.current,
    messagesEndRef,
    inputRef,
    inputHeight, // 동적 높이
    handleSendMessage,
    handleStopGeneration,
    handleKeyPress,
    handleCopyMessage,
    handleCopyTitle,
    resetChat,
    scrollToBottom,
    // WebSocket 상태 추가
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
  };
};
