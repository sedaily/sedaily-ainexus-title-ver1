import React, { useState, useEffect } from "react";
import { promptCardAPI } from "../services/api";
import ChatInterface from "./ChatInterface";
import LoadingSpinner from "./LoadingSpinner";

const UserView = ({ projectId, projectName }) => {
  const [promptCards, setPromptCards] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadPromptCards = async () => {
      try {
        setLoading(true);
        const promptCardsData = await promptCardAPI.getPromptCards(projectId);
        setPromptCards(promptCardsData);
      } catch (error) {
        console.warn("프롬프트 카드 로드 실패:", error);
        setPromptCards([]);
      } finally {
        setLoading(false);
      }
    };

    loadPromptCards();
  }, [projectId]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <LoadingSpinner />
        <div className="ml-4 text-gray-600">
          채팅 화면을 준비하고 있습니다...
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-white">
      <ChatInterface
        projectId={projectId}
        projectName={projectName}
        promptCards={promptCards}
      />
    </div>
  );
};

export default UserView;
