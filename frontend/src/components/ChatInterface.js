import React, { useState, useEffect, useRef, useCallback } from "react";
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
} from "@heroicons/react/24/outline";
import { chatAPI, handleAPIError } from "../services/api";

const ChatInterface = ({ projectId, projectName }) => {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionLoading, setSessionLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadChatHistory = useCallback(async (sessionId) => {
    try {
      const response = await chatAPI.getChatHistory(projectId, sessionId);

      // 메시지 포매팅
      const formattedMessages = response.messages.map((msg) => ({
        id: msg.sk,
        role: msg.role || "user",
        content: msg.content || msg.data?.content || "",
        timestamp: new Date(msg.timestamp || Date.now()).toISOString(),
        metadata: msg.metadata || {},
      }));

      setMessages(formattedMessages);
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`채팅 히스토리 로드 실패: ${errorInfo.message}`);
      setMessages([]);
    }
  }, [projectId]);

  const loadChatSessions = useCallback(async () => {
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
        loadChatHistory(latestSession.sessionId);
      }
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`세션 목록 로드 실패: ${errorInfo.message}`);
    } finally {
      setSessionLoading(false);
    }
  }, [projectId, loadChatHistory]);

  useEffect(() => {
    loadChatSessions();
  }, [loadChatSessions]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);


  const startNewSession = () => {
    const newSessionId = generateSessionId();
    setCurrentSessionId(newSessionId);
    setMessages([]);

    // 새 세션을 세션 목록에 추가
    const newSession = {
      sessionId: newSessionId,
      userId: "default",
      lastActivity: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      messageCount: 0,
    };

    setSessions((prev) => [newSession, ...prev]);
  };

  const generateSessionId = () => {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();

    if (!inputMessage.trim() || isLoading) return;

    if (!currentSessionId) {
      startNewSession();
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
      // 채팅 API 호출
      const response = await chatAPI.sendMessage(
        projectId,
        userMessage,
        currentSessionId
      );

      // AI 응답을 UI에 추가
      const aiMsgObj = {
        id: `ai_${Date.now()}`,
        role: "assistant",
        content: response.message,
        timestamp: response.timestamp,
        metadata: response.metadata || {},
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
      toast.error(`메시지 전송 실패: ${errorInfo.message}`);

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

  const handleDeleteSession = async (sessionId) => {
    if (!window.confirm("이 채팅 세션을 삭제하시겠습니까?")) return;

    try {
      await chatAPI.deleteChatSession(projectId, sessionId);
      setSessions((prev) => prev.filter((s) => s.sessionId !== sessionId));

      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }

      toast.success("채팅 세션이 삭제되었습니다");
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`세션 삭제 실패: ${errorInfo.message}`);
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
        return <SparklesIcon className="h-4 w-4" />;
      case "system":
        return <InformationCircleIcon className="h-4 w-4" />;
      default:
        return <ChatBubbleLeftRightIcon className="h-4 w-4" />;
    }
  };

  return (
    <div className="h-full flex bg-gray-50">
      {/* 세션 사이드바 */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <ChatBubbleLeftRightIcon className="h-5 w-5 mr-2" />
              채팅 세션
            </h3>
            <button
              onClick={startNewSession}
              className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              title="새 채팅 시작"
            >
              <PlusIcon className="h-4 w-4" />
            </button>
          </div>

          <div className="text-sm text-gray-600">
            프로젝트: <span className="font-medium">{projectName}</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {sessionLoading ? (
            <div className="p-4 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-sm text-gray-600 mt-2">세션 로딩 중...</p>
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <ChatBubbleLeftRightIcon className="h-12 w-12 mx-auto mb-2 text-gray-300" />
              <p>채팅 세션이 없습니다</p>
              <p className="text-sm">새 채팅을 시작해보세요!</p>
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
                    loadChatHistory(session.sessionId);
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        세션{" "}
                        {session.sessionId.split("_")[1] ||
                          session.sessionId.slice(-8)}
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
                        handleDeleteSession(session.sessionId);
                      }}
                      className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                      title="세션 삭제"
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
            <div className="text-center">
              <ChatBubbleLeftRightIcon className="h-24 w-24 mx-auto text-gray-300 mb-4" />
              <h3 className="text-xl font-medium text-gray-900 mb-2">
                AI 채팅 어시스턴트
              </h3>
              <p className="text-gray-600 mb-6 max-w-md">
                TITLE-NOMICS AI와 제목 생성, 편집 가이드라인에 대해
                대화해보세요. LangChain 메모리로 이전 대화를 기억합니다.
              </p>
              <button
                onClick={startNewSession}
                className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <PlusIcon className="h-5 w-5 mr-2" />새 채팅 시작
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* 메시지 영역 */}
            <div className="flex-1 overflow-y-auto p-6 bg-white">
              <div className="max-w-4xl mx-auto space-y-6">
                {messages.length === 0 ? (
                  <div className="text-center py-12">
                    <SparklesIcon className="h-12 w-12 mx-auto text-blue-600 mb-4" />
                    <p className="text-gray-600">
                      안녕하세요! 제목 생성과 편집에 대해 무엇이든 물어보세요.
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
                              : "bg-green-600 text-white mr-3"
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
                              : "bg-gray-100 text-gray-900"
                          }`}
                        >
                          <div className="whitespace-pre-wrap">
                            {message.content}
                          </div>

                          <div className="flex items-center justify-between mt-2 text-xs opacity-70">
                            <span>{formatTimestamp(message.timestamp)}</span>

                            {message.metadata &&
                              Object.keys(message.metadata).length > 0 && (
                                <div className="flex items-center space-x-2 ml-4">
                                  {message.metadata.memory_buffer_size && (
                                    <span className="flex items-center">
                                      <CpuChipIcon className="h-3 w-3 mr-1" />
                                      메모리:{" "}
                                      {message.metadata.memory_buffer_size}
                                    </span>
                                  )}
                                  {message.metadata.relevant_messages_count && (
                                    <span className="flex items-center">
                                      <DocumentTextIcon className="h-3 w-3 mr-1" />
                                      관련:{" "}
                                      {message.metadata.relevant_messages_count}
                                    </span>
                                  )}
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
              <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto">
                <div className="flex space-x-4">
                  <div className="flex-1">
                    <textarea
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      placeholder="제목 생성이나 편집에 대해 궁금한 것을 물어보세요..."
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      rows={3}
                      disabled={isLoading}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage(e);
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

export default ChatInterface;
