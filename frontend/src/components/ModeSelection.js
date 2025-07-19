import React from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../contexts/AppContext";
import DarkModeToggle from "./DarkModeToggle";

const ModeSelection = () => {
  const navigate = useNavigate();
  const { setMode } = useApp();

  const handleModeSelect = (selectedMode) => {
    setMode(selectedMode);
    navigate("/projects");
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-dark-primary flex flex-col items-center justify-center p-4 transition-all duration-500 relative">
      {/* 다크모드 토글 - 상단 우측에 고정 */}
      <div className="absolute top-8 right-8 z-20">
        <DarkModeToggle size="md" />
      </div>

      {/* 메인 컨텐츠 */}
      <div className="relative z-10">
        {/* 헤더 섹션 */}
        <div className="text-center mb-20">
          <div className="mb-8">
            <h1 className="text-7xl md:text-8xl font-bold text-gray-900 dark:text-white mb-6 animate-fade-in">
              AI 제목 생성기
            </h1>
            <div className="w-32 h-1 bg-blue-500 mx-auto rounded-full" />
          </div>
          <p className="text-xl md:text-2xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto leading-relaxed font-light">
            원하시는 모드를 선택하여
            <span className="text-blue-600 dark:text-blue-400 font-medium">
              {" "}
              효율적인 AI 경험
            </span>
            을 시작해보세요
          </p>
        </div>

        {/* 모드 선택 카드들 */}
        <div className="flex flex-col lg:flex-row gap-8 w-full max-w-5xl mx-auto items-stretch">
          {/* 사용자 모드 카드 */}
          <div className="flex-1 group">
            <button
              onClick={() => handleModeSelect("user")}
              className="w-full h-96 relative overflow-hidden card-neo group-hover:scale-105 transition-all duration-300 p-8 text-gray-900 dark:text-white"
            >
              <div className="relative z-10 h-full flex flex-col items-center justify-center">
                <div className="text-8xl mb-8 transform group-hover:scale-110 transition-all duration-300">
                  👥
                </div>
                <h2 className="text-4xl font-bold mb-4 text-blue-600 dark:text-blue-400">
                  사용자 모드
                </h2>
                <p className="text-gray-600 dark:text-gray-300 text-lg text-center leading-relaxed px-6 whitespace-nowrap">
                  <span className="font-semibold">직관적인 채팅으로 바로 시작하세요</span>
                </p>
              </div>
            </button>
          </div>

          {/* 관리자 모드 카드 */}
          <div className="flex-1 group">
            <button
              onClick={() => handleModeSelect("admin")}
              className="w-full h-96 relative overflow-hidden card-neo group-hover:scale-105 transition-all duration-300 p-8 text-gray-900 dark:text-white"
            >
              <div className="relative z-10 h-full flex flex-col items-center justify-center">
                <div className="text-8xl mb-8 transform group-hover:scale-110 transition-all duration-300">
                  ⚙️
                </div>
                <h2 className="text-4xl font-bold mb-4 text-emerald-600 dark:text-emerald-400">
                  관리자 모드
                </h2>
                <p className="text-gray-600 dark:text-gray-300 text-lg text-center leading-relaxed px-6 whitespace-nowrap">
                  <span className="font-semibold">고급 관리 기능으로 시스템 최적화</span>
                </p>
              </div>
            </button>
          </div>
        </div>

        {/* 부가 정보 */}
        <div className="mt-20 text-center">
          <div className="card-neo px-8 py-4 rounded-2xl inline-block">
            <p className="text-gray-600 dark:text-gray-300 text-sm font-medium">
              💡 모드는 언제든지 변경할 수 있습니다
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModeSelection;
