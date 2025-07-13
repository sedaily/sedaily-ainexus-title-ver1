import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { 
  PaperAirplaneIcon, 
  ArrowLeftIcon, 
  DocumentPlusIcon,
  XMarkIcon,
  BookmarkIcon,
  TrashIcon
} from "@heroicons/react/24/outline";
import { useChat } from "../hooks/useChat";
import ChatMessage from "./chat/ChatMessage";

const ChatInterface = ({ projectId, projectName, promptCards = [] }) => {
  const navigate = useNavigate();
  const [uploadedFile, setUploadedFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [savedChats, setSavedChats] = useState([]);
  
  const {
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
  } = useChat(projectId, projectName, promptCards);

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    if (file && file.type === 'text/plain') {
      const reader = new FileReader();
      reader.onload = (e) => {
        setInputValue(e.target?.result || '');
        setUploadedFile(file);
      };
      reader.readAsText(file);
    }
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragOver(false);
    const files = event.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      if (file.type === 'text/plain') {
        const reader = new FileReader();
        reader.onload = (e) => {
          setInputValue(e.target?.result || '');
          setUploadedFile(file);
        };
        reader.readAsText(file);
      }
    }
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const removeFile = () => {
    setUploadedFile(null);
    setInputValue('');
  };

  // 대화 저장
  const saveCurrentChat = () => {
    if (messages.length <= 1) {
      alert('저장할 대화가 없습니다.');
      return;
    }

    const chatTitle = `대화 ${new Date().toLocaleString()}`;
    const chatData = {
      id: Date.now(),
      title: chatTitle,
      messages: messages,
      timestamp: new Date().toISOString(),
      projectId: projectId
    };

    const existingChats = JSON.parse(localStorage.getItem('savedChats') || '[]');
    const updatedChats = [chatData, ...existingChats].slice(0, 10); // 최대 10개
    localStorage.setItem('savedChats', JSON.stringify(updatedChats));
    setSavedChats(updatedChats);
    alert('대화가 저장되었습니다!');
  };

  // 저장된 대화 로드
  const loadSavedChat = (chatData) => {
    if (window.confirm('현재 대화를 저장된 대화로 바꾸시겠습니까?')) {
      // messages를 직접 설정할 수 없으므로 useChat의 resetChat과 새로운 함수가 필요
      alert('대화 로드 기능은 페이지 새로고침 후 이용해주세요.');
    }
  };

  // 저장된 대화 삭제
  const deleteSavedChat = (chatId) => {
    if (window.confirm('저장된 대화를 삭제하시겠습니까?')) {
      const existingChats = JSON.parse(localStorage.getItem('savedChats') || '[]');
      const updatedChats = existingChats.filter(chat => chat.id !== chatId);
      localStorage.setItem('savedChats', JSON.stringify(updatedChats));
      setSavedChats(updatedChats);
    }
  };

  // 컴포넌트 마운트 시 저장된 대화 로드
  useEffect(() => {
    const existingChats = JSON.parse(localStorage.getItem('savedChats') || '[]');
    setSavedChats(existingChats.filter(chat => chat.projectId === projectId));
  }, [projectId]);

  return (
    <div className="flex flex-col h-full">
      {/* 헤더 */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate("/")}
              className="text-gray-600 hover:text-gray-900 transition-colors p-2 hover:bg-gray-100 rounded-lg"
            >
              <ArrowLeftIcon className="h-5 w-5" />
            </button>
            <div>
              <h1 className="text-xl font-semibold text-slate-800">
                {projectName}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={saveCurrentChat}
              className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
              title="대화 저장"
            >
              <BookmarkIcon className="h-4 w-4" />
              저장
            </button>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm text-slate-600">준비완료</span>
            </div>
          </div>
        </div>
        
      </div>

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto px-4 py-4 min-h-0">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message}
              onCopyMessage={handleCopyMessage}
              onCopyTitle={handleCopyTitle}
              copiedMessage={copiedMessage}
            />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 입력 영역 */}
      <div className="flex-shrink-0 bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-4xl mx-auto">
          {/* 업로드된 파일 표시 */}
          {uploadedFile && (
            <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-2">
                <DocumentPlusIcon className="h-4 w-4 text-blue-600" />
                <span className="text-sm text-blue-700">{uploadedFile.name}</span>
              </div>
              <button
                onClick={removeFile}
                className="text-blue-600 hover:text-blue-800 p-1"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>
          )}

          <div 
            className={`flex items-end space-x-4 ${dragOver ? 'opacity-60' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="기사 내용을 입력하거나 텍스트 파일을 드래그하세요..."
                className={`w-full px-3 py-3 border rounded-lg focus:outline-none resize-none transition-colors ${
                  dragOver 
                    ? 'border-blue-400 bg-blue-50 border-dashed' 
                    : 'border-gray-300 focus:border-blue-500 bg-white'
                }`}
                rows={3}
                disabled={isGenerating}
              />
              
              {/* 파일 업로드 버튼 */}
              <div className="absolute bottom-3 right-3 flex items-center gap-2">
                <label className="cursor-pointer p-1.5 text-gray-400 hover:text-gray-600 transition-colors">
                  <DocumentPlusIcon className="h-4 w-4" />
                  <input
                    type="file"
                    accept=".txt"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </label>
              </div>
            </div>
            
            <button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isGenerating}
              className="bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isGenerating ? (
                <div className="animate-spin rounded-full h-5 w-5 border-2 border-t-transparent border-white"></div>
              ) : (
                <PaperAirplaneIcon className="h-5 w-5" />
              )}
            </button>
          </div>

          {/* 도움말 텍스트 */}
          <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
            <span>Enter로 전송 • Shift+Enter로 줄바꿈</span>
            <span className="text-blue-600">.txt 파일 지원</span>
          </div>
          
          {/* 드래그 오버레이 */}
          {dragOver && (
            <div className="absolute inset-0 bg-blue-50 border-2 border-blue-400 border-dashed rounded-lg flex items-center justify-center">
              <div className="text-center">
                <DocumentPlusIcon className="h-12 w-12 text-blue-500 mx-auto mb-2" />
                <p className="text-blue-700 font-medium">파일을 여기에 놓으세요</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
