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
  const streamingMessageIdRef = useRef(null);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

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

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // 메시지 추가 시 스크롤 하단으로
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // WebSocket 메시지 리스너 설정
  useEffect(() => {
    const handleWebSocketMessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket 메시지 수신:', data);

        const currentStreamingId = streamingMessageIdRef.current;

        switch (data.type) {
          case 'stream_start':
            console.log('WebSocket 스트리밍 시작');
            break;

          case 'progress':
            console.log(`진행 상황: ${data.step} (${data.progress}%)`);
            // 진행 상황을 UI에 표시
            if (currentStreamingId) {
              setMessages((prev) => {
                const updatedMessages = [...prev];
                const streamingMsgIndex = updatedMessages.findIndex(
                  (msg) => msg.id === currentStreamingId
                );

                if (streamingMsgIndex !== -1) {
                  // LoadingProgress 컴포넌트 형태로 변환
                  const stage = data.progress <= 25 ? 'initializing' : 
                               data.progress <= 50 ? 'analyzing' : 
                               data.progress <= 75 ? 'generating' : 'finalizing';
                  
                  updatedMessages[streamingMsgIndex] = {
                    ...updatedMessages[streamingMsgIndex],
                    content: data.step,
                    isLoading: true,
                    isStreaming: false, // progress 단계에서는 스트리밍 인디케이터 숨김
                    loadingProgress: {
                      stage: stage,
                      message: data.step,
                      percentage: data.progress
                    }
                  };
                }

                return updatedMessages;
              });
            }
            break;

          case 'stream_chunk':
            if (currentStreamingId) {
              setMessages((prev) => {
                const updatedMessages = [...prev];
                const streamingMsgIndex = updatedMessages.findIndex(
                  (msg) => msg.id === currentStreamingId
                );

                if (streamingMsgIndex !== -1) {
                  // 첫 번째 청크인 경우 progress 내용을 초기화
                  const isFirstChunk = updatedMessages[streamingMsgIndex].loadingProgress !== undefined;
                  const currentContent = isFirstChunk ? "" : updatedMessages[streamingMsgIndex].content;
                  
                  updatedMessages[streamingMsgIndex] = {
                    ...updatedMessages[streamingMsgIndex],
                    content: currentContent + data.content,
                    isLoading: true,
                    isStreaming: true,
                    loadingProgress: undefined, // progress 상태 제거
                  };
                }

                return updatedMessages;
              });
              scrollToBottom();
            }
            break;

          case 'stream_complete':
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
                    loadingProgress: undefined,
                    timestamp: new Date(),
                  };
                }

                return updatedMessages;
              });
              streamingMessageIdRef.current = null;
              scrollToBottom();
            }
            break;

          case 'error':
            console.error('WebSocket 스트리밍 오류:', data.message);
            if (currentStreamingId) {
              setMessages((prev) => {
                const updatedMessages = [...prev];
                const streamingMsgIndex = updatedMessages.findIndex(
                  (msg) => msg.id === currentStreamingId
                );

                if (streamingMsgIndex !== -1) {
                  updatedMessages[streamingMsgIndex] = {
                    ...updatedMessages[streamingMsgIndex],
                    content: '메시지 처리 중 오류가 발생했습니다. 다시 시도해주세요.',
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
            console.log('알 수 없는 WebSocket 메시지 타입:', data.type);
        }
      } catch (error) {
        console.error('WebSocket 메시지 파싱 오류:', error);
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
          console.log("스트리밍 메시지 업데이트 성공:", updatedMessages[streamingMsgIndex].content);
        } else {
          console.error("스트리밍 메시지를 찾을 수 없음:", currentStreamingId);
        }

        return updatedMessages;
      });

      // 스크롤 조정
      scrollToBottom();
    },
    [scrollToBottom]
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
          console.log("스트리밍 완료 처리 성공:", updatedMessages[streamingMsgIndex].content);
        } else {
          console.error("스트리밍 완료 처리 중 메시지를 찾을 수 없음:", currentStreamingId);
        }

        return updatedMessages;
      });

      // 스트리밍 ID 초기화
      streamingMessageIdRef.current = null;

      // 스크롤 조정
      scrollToBottom();
    },
    [scrollToBottom]
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

    const chatHistory = messages
      .filter((msg) => !msg.isLoading && !msg.isError)
      .map((msg) => ({
        role: msg.type === "user" ? "user" : "assistant",
        content: msg.content,
      }));

    try {
      // WebSocket 연결 확인 및 실시간 스트리밍 시도
      if (wsConnected) {
        console.log('WebSocket을 통한 실시간 스트리밍 시작');
        
        const success = wsStartStreaming(userMessage.content, chatHistory);
        
        if (success) {
          // WebSocket 스트리밍 성공, 나머지는 리스너에서 처리
          return;
        } else {
          console.log('WebSocket 전송 실패, SSE 폴백 모드로 전환');
        }
      } else {
        console.log('WebSocket 미연결, SSE 모드 사용');
      }

      // WebSocket 실패 시 기존 SSE 방식으로 폴백
      const orchestrationData = {
        userInput: userMessage.content,
        chat_history: chatHistory,
      };

      // 스트리밍 옵션 설정
      const streamingOptions = {
        useStreaming: true,
        chat_history: orchestrationData.chat_history,
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
    }
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
    streamingMessageIdRef.current = null;
    resetOrchestration();
  }, [resetOrchestration]);

  return {
    messages,
    inputValue,
    setInputValue,
    copiedMessage,
    isGenerating,
    isStreaming,
    streamingMessageId: streamingMessageIdRef.current,
    messagesEndRef,
    inputRef,
    handleSendMessage,
    handleKeyPress,
    handleCopyMessage,
    handleCopyTitle,
    resetChat,
    scrollToBottom,
    // WebSocket 상태 추가
    wsConnected,
    wsConnecting,
    wsError,
  };
};
