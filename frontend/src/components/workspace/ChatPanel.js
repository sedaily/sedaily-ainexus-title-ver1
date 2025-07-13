import React, { useState, useRef, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import {
  PaperAirplaneIcon,
  ArrowPathIcon,
  DocumentDuplicateIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { orchestrationAPI } from '../../services/api';

const ChatPanel = ({ 
  projectId, 
  projectName,
  promptCards = [],
  onToggleCardPanel,
  cardPanelVisible,
  className = "" 
}) => {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      type: 'assistant',
      content: `안녕하세요! 저는 ${projectName}의 AI 제목 작가입니다. 🎯\n\n기사 내용을 입력해주시면 다양한 스타일의 제목을 제안해드릴게요. 제목을 수정하거나 다른 스타일로 바꾸고 싶으시면 언제든 말씀해주세요!`,
      timestamp: new Date(),
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentExecution, setCurrentExecution] = useState(null);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // 메시지 끝으로 스크롤
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 키보드 단축키 처리
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ctrl/Cmd + B: 카드 패널 토글
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault();
        onToggleCardPanel();
        inputRef.current?.focus();
      }
      
      // /: 카드 빠른 검색 (추후 구현)
      if (e.key === '/' && !e.ctrlKey && !e.metaKey && document.activeElement !== inputRef.current) {
        e.preventDefault();
        onToggleCardPanel();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onToggleCardPanel]);

  // 메시지 전송
  const handleSendMessage = async () => {
    if (!inputValue.trim() || isGenerating) return;

    const userMessage = {
      id: Date.now() + Math.random(),
      type: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsGenerating(true);

    try {
      // 오케스트레이션 실행
      const response = await orchestrationAPI.executeOrchestration(
        projectId,
        inputValue,
        {
          useAllSteps: true,
          enabledSteps: promptCards.filter(card => card.enabled).map(card => card.category),
          maxRetries: 3,
          temperature: 0.7
        }
      );

      setCurrentExecution(response.executionId);

      // 임시 로딩 메시지
      const loadingMessage = {
        id: 'loading-' + Date.now(),
        type: 'assistant',
        content: '🎯 AI가 제목을 생성하고 있습니다...\n\n단계별로 처리 중이니 잠시만 기다려주세요!',
        timestamp: new Date(),
        isLoading: true,
      };

      setMessages(prev => [...prev, loadingMessage]);

      // 결과 폴링
      pollOrchestrationResult(response.executionId);

    } catch (error) {
      console.error('메시지 전송 오류:', error);
      
      const errorMessage = {
        id: 'error-' + Date.now(),
        type: 'assistant',
        content: '죄송합니다. 제목 생성 중 오류가 발생했습니다. 다시 시도해주세요.',
        timestamp: new Date(),
        isError: true,
      };

      setMessages(prev => [...prev, errorMessage]);
      setIsGenerating(false);
    }
  };

  // 오케스트레이션 결과 폴링
  const pollOrchestrationResult = async (executionId) => {
    const poll = async () => {
      try {
        const status = await orchestrationAPI.getOrchestrationStatus(projectId, executionId);
        
        if (status.status === 'COMPLETED') {
          const result = await orchestrationAPI.getOrchestrationResult(projectId, executionId);
          
          // 최종 결과에서 제목들 추출
          const titles = result.steps
            ?.filter(step => step.output)
            ?.map(step => step.output)
            ?.slice(-3) || ['제목 생성 완료'];

          const responseMessage = {
            id: 'response-' + Date.now(),
            type: 'assistant',
            content: `✨ **생성된 제목 후보들입니다:**\n\n${titles.map((title, i) => `**${i + 1}.** ${title}`).join('\n\n')}\n\n원하시는 제목이 있으시거나 수정이 필요하시면 말씀해주세요!`,
            timestamp: new Date(),
            titles: titles,
          };

          // 로딩 메시지 제거하고 결과 메시지 추가
          setMessages(prev => 
            prev.filter(msg => !msg.isLoading).concat([responseMessage])
          );
          setIsGenerating(false);
          
        } else if (status.status === 'FAILED') {
          throw new Error('오케스트레이션 실패');
        } else if (status.status === 'RUNNING') {
          // 3초 후 다시 폴링
          setTimeout(poll, 3000);
        }
      } catch (error) {
        console.error('결과 조회 오류:', error);
        
        const errorMessage = {
          id: 'error-' + Date.now(),
          type: 'assistant',
          content: '제목 생성 중 문제가 발생했습니다. 다시 시도해주세요.',
          timestamp: new Date(),
          isError: true,
        };

        setMessages(prev => 
          prev.filter(msg => !msg.isLoading).concat([errorMessage])
        );
        setIsGenerating(false);
      }
    };

    poll();
  };

  // 메시지 복사
  const copyMessage = (content) => {
    navigator.clipboard.writeText(content);
    toast.success('메시지가 복사되었습니다');
  };

  // 채팅 초기화
  const clearChat = () => {
    if (window.confirm('채팅 기록을 모두 삭제하시겠습니까?')) {
      setMessages([
        {
          id: 'welcome',
          type: 'assistant',
          content: `안녕하세요! 저는 ${projectName}의 AI 제목 작가입니다. 🎯\n\n기사 내용을 입력해주시면 다양한 스타일의 제목을 제안해드릴게요. 제목을 수정하거나 다른 스타일로 바꾸고 싶으시면 언제든 말씀해주세요!`,
          timestamp: new Date(),
        }
      ]);
      toast.success('채팅 기록이 초기화되었습니다');
    }
  };

  return (
    <div className={`flex flex-col h-full bg-white ${className}`}>
      {/* 채팅 헤더 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center space-x-3">
          <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
          <h3 className="font-semibold text-gray-900">AI 제목 작가</h3>
          {!cardPanelVisible && (
            <button
              onClick={onToggleCardPanel}
              className="text-xs text-blue-600 hover:text-blue-800 ml-2"
            >
              카드 보기 ({promptCards.filter(c => c.enabled).length}개 활성)
            </button>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={clearChat}
            className="p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors"
            title="채팅 초기화"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] p-4 rounded-lg ${
                message.type === 'user'
                  ? 'bg-blue-600 text-white'
                  : message.isError
                  ? 'bg-red-50 text-red-800 border border-red-200'
                  : message.isLoading
                  ? 'bg-yellow-50 text-yellow-800 border border-yellow-200'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              <div className="whitespace-pre-wrap break-words">
                {message.content}
              </div>
              
              {/* 제목 복사 버튼들 */}
              {message.titles && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {message.titles.map((title, index) => (
                    <button
                      key={index}
                      onClick={() => copyMessage(title)}
                      className="flex items-center px-2 py-1 bg-gray-200 hover:bg-gray-300 rounded text-xs text-gray-700 transition-colors"
                    >
                      <DocumentDuplicateIcon className="h-3 w-3 mr-1" />
                      제목 {index + 1} 복사
                    </button>
                  ))}
                </div>
              )}
              
              <div className="text-xs opacity-70 mt-2">
                {message.timestamp.toLocaleTimeString('ko-KR', {
                  hour: 'numeric',
                  minute: '2-digit'
                })}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* 입력 영역 */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="flex space-x-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="기사 내용을 입력하거나 제목 수정 요청을 해주세요..."
              rows={3}
              className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              disabled={isGenerating}
            />
            <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
              <span>{inputValue.length}/2000</span>
              <span>Shift + Enter로 줄바꿈, Enter로 전송</span>
            </div>
          </div>
          
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isGenerating}
            className={`flex items-center justify-center w-12 h-12 rounded-lg font-medium transition-colors ${
              !inputValue.trim() || isGenerating
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isGenerating ? (
              <ArrowPathIcon className="h-5 w-5 animate-spin" />
            ) : (
              <PaperAirplaneIcon className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;