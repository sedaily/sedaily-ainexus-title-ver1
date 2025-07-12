import React, { useState, useEffect, useRef } from "react";
import { toast } from "react-hot-toast";
import {
  ChatBubbleLeftRightIcon,
  PaperAirplaneIcon,
  TrashIcon,
  PlusIcon,
  ClockIcon,
  CpuChipIcon,
  DocumentTextIcon,
  UserIcon,
  SparklesIcon,
  InformationCircleIcon,
  BeakerIcon,
  CogIcon,
} from "@heroicons/react/24/outline";
import { chatAPI, handleAPIError } from "../services/api";

const BedrockAgentChat = ({ projectId, projectName, projectInfo }) => {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionLoading, setSessionLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadAgentChatSessions();
  }, [projectId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadAgentChatSessions = async () => {
    try {
      setSessionLoading(true);
      const response = await chatAPI.getChatSessions(projectId);
      setSessions(response.sessions || []);

      // 가장 최근 세션을 자동 선택
      if (response.sessions && response.sessions.length > 0) {
        const latestSession = response.sessions.sort(
          (a, b) => new Date(b.lastActivity) - new Date(a.lastActivity)
        )[0];
        setCurrentSessionId(latestSession.sessionId);
        loadAgentChatHistory(latestSession.sessionId);
      }
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`Agent 세션 목록 로드 실패: ${errorInfo.message}`);
    } finally {
      setSessionLoading(false);
    }
  };

  const loadAgentChatHistory = async (sessionId) => {
    try {
      const response = await chatAPI.getChatHistory(projectId, sessionId);
      
      // Bedrock Agent는 세션 히스토리를 내부적으로 관리하므로
      // 여기서는 UI 상태만 초기화
      setMessages([]);
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`Agent 채팅 히스토리 로드 실패: ${errorInfo.message}`);
      setMessages([]);
    }
  };

  const startNewAgentSession = () => {
    const newSessionId = generateSessionId();
    setCurrentSessionId(newSessionId);
    setMessages([]);

    // 새 세션을 세션 목록에 추가
    const newSession = {
      sessionId: newSessionId,
      userId: "default",
      lastActivity: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      agentSession: true,
      messageCount: 0,
    };

    setSessions((prev) => [newSession, ...prev]);
  };

  const generateSessionId = () => {
    return `agent_session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  const handleSendAgentMessage = async (e) => {
    e.preventDefault();

    if (!inputMessage.trim() || isLoading) return;

    if (!currentSessionId) {
      startNewAgentSession();
      return;
    }

    const userMessage = inputMessage.trim();
    setInputMessage("");
    setIsLoading(true);

    // 사용자 메시지를 즉시 UI에 추가
    const userMsgObj = {
      id: `user_${Date.now()}`,
      role: "user",
      content: userMessage,
      timestamp: new Date().toISOString(),
      metadata: {},
    };

    setMessages((prev) => [...prev, userMsgObj]);

    try {
      // Bedrock Agent 채팅 API 호출
      const response = await chatAPI.sendMessage(
        projectId,
        userMessage,
        currentSessionId
      );

      // AI 응답을 UI에 추가
      const aiMsgObj = {
        id: `agent_${Date.now()}`,
        role: "assistant",
        content: response.message,
        timestamp: response.timestamp,
        metadata: {
          ...response.metadata,
          agentResponse: true,
          agentId: response.agentResponse?.sessionId,
        },
      };

      setMessages((prev) => [...prev, aiMsgObj]);

      // 세션 정보 업데이트
      setSessions((prev) =>
        prev.map((session) =>
          session.sessionId === currentSessionId
            ? {
                ...session,
                lastActivity: response.timestamp,
                messageCount: (session.messageCount || 0) + 2,
              }
            : session
        )
      );
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`Agent 메시지 전송 실패: ${errorInfo.message}`);

      // 오류 메시지 추가
      const errorMsgObj = {
        id: `error_${Date.now()}`,
        role: "system",
        content: `오류: ${errorInfo.message}`,
        timestamp: new Date().toISOString(),
        metadata: { error: true },
      };

      setMessages((prev) => [...prev, errorMsgObj]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteAgentSession = async (sessionId) => {
    if (!window.confirm("이 Agent 채팅 세션을 삭제하시겠습니까?")) return;

    try {
      await chatAPI.deleteChatSession(projectId, sessionId);
      setSessions((prev) => prev.filter((s) => s.sessionId !== sessionId));

      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }

      toast.success("Agent 채팅 세션이 삭제되었습니다");
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`Agent 세션 삭제 실패: ${errorInfo.message}`);
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString("ko-KR", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getMessageIcon = (role) => {
    switch (role) {
      case "user":
        return <UserIcon className="h-4 w-4" />;
      case "assistant":
        return <BeakerIcon className="h-4 w-4" />;
      case "system":
        return <InformationCircleIcon className="h-4 w-4" />;
      default:
        return <ChatBubbleLeftRightIcon className="h-4 w-4" />;
    }
  };

  // 프로젝트 AI 커스터마이징 정보 표시
  const ProjectCustomizationInfo = () => (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
      <div className="flex items-center mb-2">
        <CogIcon className="h-5 w-5 text-blue-600 mr-2" />
        <h4 className="font-medium text-blue-900">프로젝트 AI 설정</h4>
      </div>
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-blue-700 font-medium">AI 역할:</span>
          <p className="text-blue-600">{projectInfo?.aiRole || "제목 생성 전문가"}</p>
        </div>
        <div>
          <span className="text-blue-700 font-medium">타겟 독자:</span>
          <p className="text-blue-600">{projectInfo?.targetAudience || "일반독자"}</p>
        </div>
        <div>
          <span className="text-blue-700 font-medium">출력 형식:</span>
          <p className="text-blue-600">
            {projectInfo?.outputFormat === "single" ? "단일 제목" : 
             projectInfo?.outputFormat === "detailed" ? "상세 설명 포함" : "다중 제목"}
          </p>
        </div>
        {projectInfo?.styleGuidelines && (
          <div className="col-span-2">
            <span className="text-blue-700 font-medium">스타일 가이드:</span>
            <p className="text-blue-600 text-xs">{projectInfo.styleGuidelines}</p>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="h-full flex bg-gray-50">
      {/* 세션 사이드바 */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <BeakerIcon className="h-5 w-5 mr-2 text-blue-600" />
              Bedrock Agent
            </h3>
            <button
              onClick={startNewAgentSession}
              className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              title="새 Agent 채팅 시작"
            >
              <PlusIcon className="h-4 w-4" />
            </button>
          </div>

          <div className="text-sm text-gray-600">
            프로젝트: <span className="font-medium">{projectName}</span>
          </div>
          
          <div className="mt-2 text-xs text-blue-600 bg-blue-50 p-2 rounded">
            🔬 동적 프롬프트 적용된 AI 어시스턴트
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {sessionLoading ? (
            <div className="p-4 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-sm text-gray-600 mt-2">Agent 세션 로딩 중...</p>
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <BeakerIcon className="h-12 w-12 mx-auto mb-2 text-gray-300" />
              <p>Agent 채팅 세션이 없습니다</p>
              <p className="text-sm">새 Agent 채팅을 시작해보세요!</p>
            </div>
          ) : (
            <div className="space-y-2 p-4">
              {sessions.map((session) => (
                <div
                  key={session.sessionId}
                  className={`p-3 rounded-lg cursor-pointer transition-colors ${
                    currentSessionId === session.sessionId
                      ? "bg-blue-100 border border-blue-300"
                      : "bg-gray-50 hover:bg-gray-100"
                  }`}
                  onClick={() => {
                    setCurrentSessionId(session.sessionId);
                    loadAgentChatHistory(session.sessionId);
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate flex items-center">
                        <BeakerIcon className="h-3 w-3 mr-1 text-blue-600" />
                        Agent {session.sessionId.split("_")[2] || session.sessionId.slice(-8)}
                      </p>
                      <div className="flex items-center text-xs text-gray-500 mt-1">
                        <ClockIcon className="h-3 w-3 mr-1" />
                        {formatTimestamp(session.lastActivity)}
                      </div>
                      {session.messageCount && (
                        <div className="text-xs text-blue-600 mt-1">
                          {session.messageCount}개 메시지
                        </div>
                      )}
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteAgentSession(session.sessionId);
                      }}
                      className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                      title="Agent 세션 삭제"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 채팅 영역 */}
      <div className="flex-1 flex flex-col">
        {!currentSessionId ? (
          <div className="flex-1 flex items-center justify-center bg-gray-50">
            <div className="text-center max-w-lg">
              <BeakerIcon className="h-24 w-24 mx-auto text-blue-300 mb-4" />
              <h3 className="text-xl font-medium text-gray-900 mb-2">
                Bedrock Agent AI 어시스턴트
              </h3>
              <p className="text-gray-600 mb-6">
                프로젝트별 AI 커스터마이징이 적용된 Bedrock Agent와 대화해보세요. 
                동적 프롬프트를 통해 프로젝트 설정에 맞는 맞춤형 답변을 제공합니다.
              </p>
              
              {projectInfo && <ProjectCustomizationInfo />}
              
              <button
                onClick={startNewAgentSession}
                className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <PlusIcon className="h-5 w-5 mr-2" />새 Agent 채팅 시작
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* 메시지 영역 */}
            <div className="flex-1 overflow-y-auto p-6 bg-white">
              <div className="max-w-4xl mx-auto space-y-6">
                {projectInfo && <ProjectCustomizationInfo />}
                
                {messages.length === 0 ? (
                  <div className="text-center py-12">
                    <BeakerIcon className="h-12 w-12 mx-auto text-blue-600 mb-4" />
                    <p className="text-gray-600">
                      안녕하세요! 프로젝트 설정에 맞춰 제목 생성과 편집에 대해 도움드리겠습니다.
                    </p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${
                        message.role === "user"
                          ? "justify-end"
                          : "justify-start"
                      }`}
                    >
                      <div
                        className={`max-w-3xl flex ${
                          message.role === "user"
                            ? "flex-row-reverse"
                            : "flex-row"
                        }`}
                      >
                        <div
                          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                            message.role === "user"
                              ? "bg-blue-600 text-white ml-3"
                              : message.role === "system"
                              ? "bg-gray-400 text-white mr-3"
                              : "bg-purple-600 text-white mr-3"
                          }`}
                        >
                          {getMessageIcon(message.role)}
                        </div>

                        <div
                          className={`rounded-lg px-4 py-3 ${
                            message.role === "user"
                              ? "bg-blue-600 text-white"
                              : message.role === "system"
                              ? "bg-gray-100 text-gray-900"
                              : "bg-purple-50 text-gray-900 border border-purple-200"
                          }`}
                        >
                          <div className="whitespace-pre-wrap">
                            {message.content}
                          </div>

                          <div className="flex items-center justify-between mt-2 text-xs opacity-70">
                            <span>{formatTimestamp(message.timestamp)}</span>

                            {message.metadata?.agentResponse && (
                              <div className="flex items-center space-x-2 ml-4">
                                <span className="flex items-center text-purple-600">
                                  <BeakerIcon className="h-3 w-3 mr-1" />
                                  Bedrock Agent
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
              <div ref={messagesEndRef} />
            </div>

            {/* 입력 영역 */}
            <div className="border-t border-gray-200 bg-white p-6">
              <form onSubmit={handleSendAgentMessage} className="max-w-4xl mx-auto">
                <div className="flex space-x-4">
                  <div className="flex-1">
                    <textarea
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      placeholder="프로젝트 설정에 맞는 제목 생성이나 편집 조언을 요청해보세요..."
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      rows={3}
                      disabled={isLoading}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleSendAgentMessage(e);
                        }
                      }}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={!inputMessage.trim() || isLoading}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center"
                  >
                    {isLoading ? (
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    ) : (
                      <PaperAirplaneIcon className="h-5 w-5" />
                    )}
                  </button>
                </div>

                <div className="flex items-center justify-between mt-2 text-sm text-gray-500">
                  <span>Enter로 전송, Shift+Enter로 줄바꿈</span>
                  {inputMessage && <span>{inputMessage.length}자</span>}
                </div>
              </form>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default BedrockAgentChat;