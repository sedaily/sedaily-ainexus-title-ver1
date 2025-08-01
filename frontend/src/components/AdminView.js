import React, { useState, useEffect } from "react";
import ChatWindow from "./chat/ChatWindow";
import PromptCardManager from "./PromptCardManager";
import { promptCardAPI } from "../services/api";
import { ChatInterfaceSkeleton } from "./skeleton/SkeletonComponents";
import { useApp } from "../contexts/AppContext";

const AdminView = ({ projectId: propProjectId, projectName: propProjectName }) => {
  const { currentProject } = useApp();
  
  // props로 받은 값이 있으면 우선 사용, 없으면 컨텍스트에서 가져옴
  const projectId = propProjectId || currentProject?.projectId || "default-admin-project";
  const projectName = propProjectName || currentProject?.name || "관리자 프로젝트";
  const [promptCards, setPromptCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rightSidebarCollapsed, setRightSidebarCollapsed] = useState(false);

  const loadPromptCards = async () => {
    try {
      setLoading(true);
      console.log("🔄 AdminView - 프롬프트 카드 로드 시작");
      const response = await promptCardAPI.getPromptCards(projectId, true);
      setPromptCards(response.promptCards || []);
      console.log("✅ AdminView - 프롬프트 카드 로드 완료:", response.promptCards?.length || 0);
    } catch (error) {
      console.warn("프롬프트 카드 로드 실패:", error);
      setPromptCards([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPromptCards();
  }, [projectId]);

  if (loading) {
    return <ChatInterfaceSkeleton />;
  }

  return (
    <div className="h-screen bg-gray-50 dark:bg-dark-primary transition-colors duration-300 overflow-hidden">
      <ChatWindow
        projectId={projectId}
        projectName={projectName}
        promptCards={promptCards}
        isAdminMode={true}
        rightSidebarCollapsed={rightSidebarCollapsed}
      />

      {/* 우측 프롬프트 카드 사이드바 */}
      <div className={`fixed right-0 top-16 h-[calc(100vh-4rem)] bg-gray-50 dark:bg-dark-secondary border-l border-gray-200 dark:border-gray-700 transition-all duration-500 ease-out z-30 ${
        rightSidebarCollapsed ? "w-0 overflow-hidden" : "w-80"
      }`}>
        <div className="h-full flex flex-col">
          {/* 프롬프트 카드 매니저 */}
          <div className="flex-1 overflow-y-auto">
            <PromptCardManager 
              projectId={projectId} 
              projectName={projectName}
              promptCards={promptCards}
              onPromptCardsUpdate={loadPromptCards}
              onClose={() => setRightSidebarCollapsed(true)}
            />
          </div>
        </div>
      </div>

      {/* 우측 사이드바 토글 버튼 (사이드바가 닫혀있을 때만 표시) */}
      {rightSidebarCollapsed && (
        <button
          onClick={() => setRightSidebarCollapsed(false)}
          className="fixed right-4 top-20 z-40 p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-lg transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      )}
    </div>
  );
};

export default AdminView;
