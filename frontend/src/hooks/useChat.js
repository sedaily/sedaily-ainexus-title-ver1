import { useState, useEffect, useRef, useCallback } from "react";
import { toast } from "react-hot-toast";
import { copyToClipboard } from "../utils/clipboard";
import { useOrchestration } from "./useOrchestration";
import { useWebSocket } from "./useWebSocket";
import { crewAPI, handleAPIError, promptCardAPI } from "../services/api";
import { useAuth } from "../contexts/AuthContext";

/**
 * 멀티-에이전트 AI 응답을 파싱하고 UI에 맞는 메시지 객체로 변환
 */
const processMultiAgentResponse = (result) => {
  if (!result) {
    console.error("멀티-에이전트 응답 오류: 결과가 없습니다", result);
    return {
      id: "error-" + Date.now(),
      type: "assistant",
      content: "처리 중 오류가 발생했습니다. 다시 시도해주세요.",
      timestamp: new Date().toISOString(),
      isError: true,
    };
  }

  // 멀티-에이전트 결과 구성
  const agentResults = result.agentResults || {};
  const finalTitles = result.finalTitles || {};
  const tokenUsage = result.tokenUsage || 0;

  // 에이전트별 결과를 포맷팅
  const agentSummary = Object.keys(agentResults).map((agentType) => {
    const agentResult = agentResults[agentType];
    const titles = finalTitles[agentType] || [];

    return {
      agentType,
      agentName: getAgentName(agentType),
      result: agentResult?.content || "결과 없음",
      titles: titles,
      tokenCount: agentResult?.tokenCount || 0,
    };
  });

  // 전체 제목 목록 생성
  const allTitles = Object.values(finalTitles).flat();

  return {
    id: "multi-agent-" + Date.now(),
    type: "assistant",
    content: formatMultiAgentContent(agentSummary, allTitles),
    timestamp: new Date(),
    // 멀티-에이전트 특화 데이터
    isMultiAgent: true,
    agentResults: agentSummary,
    allTitles: allTitles,
    tokenUsage: tokenUsage,
  };
};

/**
 * 에이전트 타입을 한국어 이름으로 변환
 */
const getAgentName = (agentType) => {
  const agentNames = {
    journalism: "📰 저널리즘 충실형 (Journalism Type)",
    balanced: "⚖️ 균형잡힌 후킹형 (Balanced Hook Type)",
    click: "🎯 클릭유도형 (Click-bait Type)",
    seo: "🔍 SEO/AEO 최적화형 (SEO/AEO Type)",
    social: "📱 소셜미디어 공유형 (Social Media Type)",
  };
  return agentNames[agentType] || `🤖 ${agentType}`;
};

/**
 * 멀티-에이전트 결과를 UI 표시용 텍스트로 포맷팅
 */
const formatMultiAgentContent = (agentSummary, allTitles) => {
  let content = "🚀 **멀티-에이전트 분석 완료**\n\n";

  // 전체 제목 요약
  if (allTitles.length > 0) {
    content += "📋 **생성된 제목 목록:**\n";
    allTitles.forEach((title, index) => {
      content += `${index + 1}. ${title}\n`;
    });
    content += "\n";
  }

  // 에이전트별 상세 결과
  content += "🔍 **에이전트별 분석 결과:**\n\n";
  agentSummary.forEach((agent) => {
    content += `### ${agent.agentName}\n`;
    if (agent.titles.length > 0) {
      content += "**생성 제목:**\n";
      agent.titles.forEach((title) => {
        content += `• ${title}\n`;
      });
    }
    content += `**토큰 사용량:** ${agent.tokenCount}개\n\n`;
  });

  return content;
};

/**
 * 채팅 기능을 위한 커스텀 훅
 * @param {Array} promptCards - 프롬프트 카드 배열
 * @returns {Object} - 채팅 관련 상태와 함수들
 */
export const useChat = (
  promptCards = [],
  conversationId = null,
  createConversationFn = null,
  setCurrentConversationFn = null,
  addConversationFn = null,
  enableStepwise = false,
  onThoughtProcess = null,
  onStepResult = null,
  onStepwiseStart = null,
  onStepwiseComplete = null
) => {
  const { user } = useAuth(); // Add user from AuthContext

  // 디버깅 로그 (첫 번째 렌더링에만)
  const isFirstRender = useRef(true);
  if (isFirstRender.current) {
    console.log("🔍 [DEBUG] useChat 초기화:", {
      promptCardsLength: promptCards?.length,
      conversationId,
      conversationIdType: typeof conversationId,
      isConversationIdNull: conversationId === null,
      isConversationIdUndefined: conversationId === undefined,
      userId: user?.id,
    });
    isFirstRender.current = false;
  }

  // conversationId 변경 감지
  useEffect(() => {
    console.log("🔍 [DEBUG] useChat - conversationId 변경:", {
      newConversationId: conversationId,
      conversationIdType: typeof conversationId,
      isNull: conversationId === null,
      isUndefined: conversationId === undefined,
    });
  }, [conversationId]);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [copiedMessage, setCopiedMessage] = useState(null);
  const [canSendMessage, setCanSendMessage] = useState(true);
  const [inputHeight, setInputHeight] = useState(24); // 동적 높이 관리
  const [selectedModel, setSelectedModel] = useState(
    "apac.anthropic.claude-sonnet-4-20250514-v1:0"  // Claude 4.0 기본 모델
  );
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
    resetOrchestration,
  } = useOrchestration();

  // WebSocket 훅 추가
  const {
    isConnected: wsConnected,
    isConnecting: wsConnecting,
    error: wsError,
    startStreaming: wsStartStreaming,
    addMessageListener,
    removeMessageListener,
  } = useWebSocket();

  // 초기 메시지 설정 - conversationId 변경시 초기화
  useEffect(() => {
    console.log("🔍 [DEBUG] useChat 메시지 초기화:", {
      conversationId,
      previousMessages: messages.length,
    });
    setMessages([]); // 빈 배열로 시작
  }, [conversationId]); // conversationId 추가

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
            
          case "start":
            // 단계별 실행 시작
            if (onStepwiseStart) {
              onStepwiseStart();
            }
            break;
            
          case "thought_process":
            // AI 사고과정
            if (onThoughtProcess) {
              onThoughtProcess({
                step: data.step,
                thought: data.thought,
                reasoning: data.reasoning,
                confidence: data.confidence,
                decision: data.decision,
                timestamp: new Date().toISOString()
              });
            }
            break;
            
          case "step_result":
            // 단계별 실행 결과
            if (onStepResult) {
              onStepResult({
                step: data.step,
                response: data.response,
                confidence: data.confidence,
                threshold: data.threshold,
                completed: true,
                timestamp: new Date().toISOString()
              });
            }
            break;

          case "stream_chunk":
            if (currentStreamingId) {
              setMessages((prev) => {
                const updatedMessages = [...prev];
                const streamingMsgIndex = updatedMessages.findIndex(
                  (msg) => msg.id === currentStreamingId
                );

                console.log("스트림 청크 처리:", {
                  currentStreamingId,
                  streamingMsgIndex,
                  messagesLength: prev.length,
                  content: data.content,
                });

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

                  console.log(
                    "메시지 업데이트됨:",
                    updatedMessages[streamingMsgIndex]
                  );
                } else {
                  console.log(
                    "스트리밍 메시지를 찾을 수 없음, 메시지 ID들:",
                    prev.map((m) => m.id)
                  );
                }

                return updatedMessages;
              });
              // 스트리밍 중에는 사용자가 스크롤 중이 아닐 때만 자동 스크롤
              if (!isUserScrolling) {
                scrollToBottom();
              }
            } else {
              console.log("currentStreamingId가 null임");
            }
            break;

          case "stream_complete":
          case "complete":
            if (onStepwiseComplete) {
              onStepwiseComplete();
            }
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
                    timestamp: new Date().toISOString(),
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
                  // 오류 유형에 따른 사용자 메시지 결정
                  let errorContent =
                    "메시지 처리 중 오류가 발생했습니다. 다시 시도해주세요.";

                  if (
                    data.message?.includes("401") ||
                    data.message?.includes("Unauthorized")
                  ) {
                    errorContent =
                      "인증이 만료되었습니다. 다시 로그인해주세요.";
                  } else if (
                    data.message?.includes("timeout") ||
                    data.message?.includes("시간 초과")
                  ) {
                    errorContent =
                      "처리 시간이 초과되었습니다. 요청을 단순화하거나 잠시 후 다시 시도해주세요.";
                  } else if (
                    data.message?.includes("rate limit") ||
                    data.message?.includes("제한")
                  ) {
                    errorContent =
                      "요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요.";
                  }

                  updatedMessages[streamingMsgIndex] = {
                    ...updatedMessages[streamingMsgIndex],
                    content: errorContent,
                    isLoading: false,
                    isStreaming: false,
                    isError: true,
                    timestamp: new Date().toISOString(),
                  };
                }

                return updatedMessages;
              });
              streamingMessageIdRef.current = null;
            }

            // 사용자 친화적인 토스트 메시지
            const toastMessage = data.message?.includes("401")
              ? "인증이 만료되었습니다"
              : "처리 중 오류가 발생했습니다";
            toast.error(toastMessage);
            break;

          // LangGraph 관련 메시지 타입들
          case "workflow_start":
            console.log("🚀 [DEBUG] LangGraph 워크플로우 시작:", data);
            break;
            
          case "step_start":
            console.log("🧠 [DEBUG] LangGraph 단계 시작:", data);
            break;
            
          case "step_complete":
            console.log("✅ [DEBUG] LangGraph 단계 완료:", data);
            break;
            
          case "step_error":
            console.log("❌ [DEBUG] LangGraph 단계 오류:", data);
            break;
            
          case "final_synthesis":
            console.log("🎯 [DEBUG] LangGraph 최종 합성:", data);
            break;
            
          case "workflow_complete":
            console.log("🎉 [DEBUG] LangGraph 워크플로우 완료:", data);
            break;
            
          case "workflow_error":
            console.log("⚠️ [DEBUG] LangGraph 워크플로우 오류:", data);
            break;
            
          case "content":
            // LangGraph에서 전송하는 최종 답변 내용
            console.log("📝 [DEBUG] LangGraph 콘텐츠:", data);
            if (currentStreamingId && data.delta) {
              setMessages((prev) => {
                const updatedMessages = [...prev];
                const streamingMsgIndex = updatedMessages.findIndex(
                  (msg) => msg.id === currentStreamingId
                );

                if (streamingMsgIndex !== -1) {
                  const currentContent = updatedMessages[streamingMsgIndex].content || "";
                  updatedMessages[streamingMsgIndex] = {
                    ...updatedMessages[streamingMsgIndex],
                    content: currentContent + data.delta,
                    isStreaming: !data.finished,
                  };
                  
                  if (data.finished) {
                    streamingMessageIdRef.current = null;
                  }
                }
                return updatedMessages;
              });
            }
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
            timestamp: new Date().toISOString(),
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
              "\n\n---\n\n**⏹️ 생성이 사용자에 의해 중단되었습니다**",
            isLoading: false,
            isStreaming: false,
            timestamp: new Date().toISOString(),
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
    const lines = value.split("\n").length;
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
  const handleInputChange = useCallback(
    (value) => {
      setInputValue(value);
      adjustInputHeight(value);
    },
    [adjustInputHeight]
  );

  // 사용자 입력으로부터 대화 제목 생성
  const generateConversationTitle = useCallback((userInput) => {
    const firstLine = userInput.split("\n")[0];
    const title =
      firstLine.length > 50 ? firstLine.substring(0, 47) + "..." : firstLine;
    return title.trim() || "새 대화";
  }, []);

  /**
   * 메시지 전송
   */
  const handleSendMessage = useCallback(async (inputOverride, attachedFiles = []) => {
    // inputOverride가 있으면 그것을 사용, 아니면 state의 inputValue 사용
    const messageContent = typeof inputOverride === 'string' ? inputOverride : inputValue;
    
    console.log("🚀 [DEBUG] useChat handleSendMessage 호출:", {
      messageContent: messageContent.trim(),
      attachedFilesCount: attachedFiles.length,
      isGenerating,
      canSendMessage,
      conversationId,
      hasCreateConversationFn: !!createConversationFn,
    });

    if (!messageContent.trim() && attachedFiles.length === 0) {
      console.log("🚨 [DEBUG] 전송 중단: 내용 없음");
      return;
    }
    
    if (isGenerating) {
      console.log("🚨 [DEBUG] 전송 중단: 이미 생성 중");
      return;
    }

    // 현재 대화 ID가 없고 생성 함수가 있으면 새 대화 생성
    let conversationIdToUse = conversationId;
    if (
      !conversationIdToUse &&
      createConversationFn &&
      setCurrentConversationFn
    ) {
      // 첨부파일이 있으면 그 이름으로, 아니면 메시지 내용으로 제목 생성
      const titleSource = attachedFiles.length > 0 ? 
        `[첨부] ${attachedFiles[0].name}` : 
        messageContent;
      
      console.log(
        "🔍 [DEBUG] 새 대화 생성 시작 - 제목:",
        generateConversationTitle(titleSource)
      );

      try {
        const newTitle = generateConversationTitle(titleSource);
        const newConversation = await createConversationFn(newTitle);
        console.log("🔍 [DEBUG] 새 대화 생성 완료:", newConversation);

        conversationIdToUse = newConversation.id;
        setCurrentConversationFn(conversationIdToUse);

        // ConversationContext에도 새 대화 추가 (실시간 UI 업데이트)
        if (addConversationFn) {
          console.log(
            "🎉 [DEBUG] ConversationContext에 새 대화 추가:",
            newConversation
          );
          addConversationFn(newConversation);
        }

        // 상태 업데이트 대기
        await new Promise((resolve) => setTimeout(resolve, 100));
      } catch (error) {
        console.error("🔍 [DEBUG] 대화 생성 실패:", error);
      }
    }

    // 입력 비활성화
    console.log("입력 비활성화");
    setCanSendMessage(false);

    // 첨부파일 내용을 메시지에 추가
    let fullContent = messageContent.trim();
    if (attachedFiles.length > 0) {
      const fileContents = attachedFiles.map(file => {
        return `[첨부 파일: ${file.name}]\n${file.content}`;
      }).join('\n\n');
      
      if (fullContent) {
        fullContent = fullContent + '\n\n' + fileContents;
      } else {
        fullContent = fileContents;
      }
    }

    const userMessage = {
      id: "user-" + Date.now(),
      type: "user",
      content: messageContent.trim(), // 화면에는 원본 메시지만 표시
      timestamp: new Date().toISOString(),
      attachedFiles: attachedFiles.length > 0 ? attachedFiles.map(f => ({ 
        name: f.name, 
        type: f.type,
        size: f.size 
      })) : undefined // 첨부파일 메타데이터 저장
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
      timestamp: new Date().toISOString(),
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

    // 프롬프트 카드 처리를 위한 변수 초기화
    let activePromptCards = [];
    
    try {
      // 프롬프트 카드 정보 추가 - 활성화된 카드만 필터링하고 백엔드 형식에 맞게 변환
      console.log("🔍 [DEBUG] useChat - 프롬프트 카드 처리 시작");
      console.log("🔍 [DEBUG] useChat - 원본 promptCards:", promptCards);
      console.log("🔍 [DEBUG] useChat - promptCards 타입:", typeof promptCards);
      console.log("🔍 [DEBUG] useChat - promptCards는 배열인가?:", Array.isArray(promptCards));
      const safePromptCards = Array.isArray(promptCards) ? promptCards : [];
      console.log("🔍 [DEBUG] useChat - safePromptCards:", safePromptCards);
      
      // 모든 프롬프트 카드 변환
      activePromptCards = safePromptCards.map((card) => {
        // DynamoDB에서 이미 content를 포함하여 로드됨
        if (!card.prompt_text && !card.content) {
          console.warn(`🔍 [WARNING] 프롬프트 카드 '${card.title}'에 내용이 없습니다!`);
        }
        
        return {
          promptId: card.promptId || card.prompt_id,
          title: card.title || "Untitled",
          prompt_text: card.prompt_text || card.content || "",
          tags: card.tags || [],
          isActive: true,
          stepOrder: card.stepOrder || 0,
        };
      });
      
      console.log("🔍 [DEBUG] useChat - 원본 카드:", safePromptCards);
      console.log("🔍 [DEBUG] useChat - 변환 후 카드:", activePromptCards);
      console.log("🔍 [DEBUG] useChat - 최종 activePromptCards:", activePromptCards.length, activePromptCards);
    } catch (promptError) {
      console.error("🔍 [DEBUG] useChat - 프롬프트 카드 처리 오류:", promptError);
      activePromptCards = []; // 오류 시 빈 배열로 설정
    }

    try {
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
        fullPromptCards: activePromptCards,
      });

      // 대용량 텍스트 확인 로그
      console.log("🔍 [DEBUG] 입력 텍스트 크기 확인:", {
        textLength: userMessage.content.length,
        textSizeKB: (userMessage.content.length / 1024).toFixed(2) + "KB",
        isLargeText: userMessage.content.length > 100000,
        willBeChunked: userMessage.content.length > 100000
      });

      // WebSocket 연결 확인 및 실시간 스트리밍 시도
      if (wsConnected) {
        console.log("WebSocket을 통한 실시간 스트리밍 시작");
        console.log("🔍 [DEBUG] 스트리밍 매개변수 상세 확인:", {
          userInput: userMessage.content.substring(0, 100) + "...",
          userInputLength: userMessage.content.length,
          conversationId: conversationIdToUse,
          userSub: user?.id,
          historyLength: trimmedChatHistory.length,
          promptCardsLength: activePromptCards.length,
          promptCardsDetails: activePromptCards,
          conversationIdType: typeof conversationIdToUse,
          conversationIdValue: conversationIdToUse,
          isConversationIdNull: conversationIdToUse === null,
          isConversationIdUndefined: conversationIdToUse === undefined,
        });

        const success = wsStartStreaming(
          fullContent, // 첨부파일 내용이 포함된 전체 콘텐츠
          trimmedChatHistory,
          activePromptCards,
          selectedModel,
          conversationIdToUse, // 새로 생성된 conversationId 사용
          user?.id, // Add userSub from AuthContext
          enableStepwise // 단계별 실행 모드 전달
        );

        if (success) {
          // WebSocket 스트리밍 성공, 나머지는 리스너에서 처리
          console.log(
            "🎉 [DEBUG] WebSocket 스트리밍 요청 성공 - conversationId:",
            conversationIdToUse
          );
          return;
        } else {
          console.log("🚨 [DEBUG] WebSocket 전송 실패, SSE 폴백 모드로 전환");
        }
      } else {
        console.log("WebSocket 미연결, SSE 모드 사용");
      }

      // 🌟 간단한 AI 응답 시스템 실행
      console.log("AI 응답 생성 시작");

      // 간단한 AI 응답 생성
      const { generateAPI } = await import("../services/api");
      const aiResult = await generateAPI.generateTitle({
        userInput: fullContent, // 첨부파일 내용이 포함된 전체 콘텐츠
        chat_history: trimmedChatHistory,
        prompt_cards: activePromptCards,
      });

      console.log("AI 응답 생성 완료:", aiResult);

      // 결과를 UI 메시지로 변환
      const assistantMessage = {
        id: "ai-" + Date.now(),
        type: "assistant",
        content: aiResult.result || aiResult.response || "응답을 생성했습니다.",
        timestamp: new Date().toISOString(),
      };

      // 스트리밍 메시지를 최종 결과로 교체
      setMessages((prev) => {
        const updatedMessages = [...prev];
        const streamingMsgIndex = updatedMessages.findIndex(
          (msg) => msg.id === streamingMessageIdRef.current
        );

        if (streamingMsgIndex !== -1) {
          updatedMessages[streamingMsgIndex] = assistantMessage;
        } else {
          updatedMessages.push(assistantMessage);
        }

        return updatedMessages;
      });

      streamingMessageIdRef.current = null;
      setCanSendMessage(true);

      // 성공 토스트
      toast.success("AI 응답이 생성되었습니다!");
    } catch (error) {
      console.error("메시지 전송 실패:", error);

      // API 오류 처리 위임
      const { userMessage: errorUserMessage, shouldRedirect } =
        await handleAPIError(error);

      // 인증 오류로 리다이렉트가 필요한 경우
      if (shouldRedirect) {
        return;
      }

      const errorMessage = {
        id: "error-" + Date.now(),
        type: "assistant",
        content: errorUserMessage,
        timestamp: new Date().toISOString(),
        isError: true,
        errorDetails: {
          message: error.message,
          status: error.response?.status,
          code: error.code,
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
    conversationId,
    createConversationFn,
    setCurrentConversationFn,
    addConversationFn,
    generateConversationTitle,
    executeOrchestration,
    handleStreamingResponse,
    handleStreamingComplete,
    messages,
    wsConnected,
    wsStartStreaming,
    selectedModel,
    user?.id,
    enableStepwise,
  ]);

  /**
   * Enter 키로 전송
   */
  const handleKeyPress = useCallback(
    (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage(); // 기본 동작 - 첨부파일이 있는 경우 ChatWindow에서 처리
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
    console.log("🔍 [DEBUG] useChat 완전 초기화 실행");
    setMessages([]);
    setInputValue("");
    setCopiedMessage(null);
    setCanSendMessage(true);
    setInputHeight(24);
    setIsUserScrolling(false);
    streamingMessageIdRef.current = null;
    currentWebSocketRef.current = null;
    currentExecutionIdRef.current = null;
    resetOrchestration();
  }, [resetOrchestration]);

  // conversationId가 null로 변경될 때 자동으로 초기화
  useEffect(() => {
    if (conversationId === null) {
      console.log(
        "🔍 [DEBUG] conversationId가 null로 변경됨 - 채팅 완전 초기화"
      );
      resetChat();
    }
  }, [conversationId, resetChat]);

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
