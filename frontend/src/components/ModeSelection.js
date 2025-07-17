import React from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../contexts/AppContext";

const ModeSelection = () => {
  const navigate = useNavigate();
  const { setMode } = useApp();

  const handleModeSelect = (selectedMode) => {
    setMode(selectedMode);
    navigate("/projects");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex flex-col items-center justify-center p-4">
      <div className="text-center mb-16">
        <h1 className="text-6xl font-bold text-gray-800 mb-4">
          AI 제목 생성기
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed">
          원하시는 모드를 선택하여 시작해보세요
        </p>
      </div>

      <div className="flex flex-col md:flex-row gap-8 w-full max-w-4xl">
        {/* 사용자 모드 카드 - 정사각형 디자인 */}
        <div className="flex-1 group">
          <button
            onClick={() => handleModeSelect("user")}
            className="w-full aspect-square relative overflow-hidden bg-gradient-to-br from-blue-500 to-blue-700 rounded-3xl shadow-xl hover:shadow-2xl transform hover:-translate-y-2 transition-all duration-300 ease-out p-8 text-white"
          >
            {/* 배경 장식 효과 */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-white opacity-10 rounded-full -translate-y-16 translate-x-16"></div>
            <div className="absolute bottom-0 left-0 w-24 h-24 bg-white opacity-10 rounded-full translate-y-12 -translate-x-12"></div>
            <div className="absolute -bottom-20 -right-20 w-64 h-64 bg-white opacity-5 rounded-full"></div>

            <div className="relative z-10 h-full flex flex-col items-center justify-center">
              <div className="text-7xl mb-6 transform group-hover:scale-110 transition-transform duration-300">
                👥
              </div>
              <h2 className="text-3xl font-bold mb-3">사용자 모드</h2>
              <p className="text-blue-100 text-lg text-center leading-relaxed px-4">
                깔끔한 채팅 화면으로
                <br />
                바로 대화를 시작하세요
              </p>
            </div>
          </button>
        </div>

        {/* 관리자 모드 카드 - 정사각형 디자인 */}
        <div className="flex-1 group">
          <button
            onClick={() => handleModeSelect("admin")}
            className="w-full aspect-square relative overflow-hidden bg-gradient-to-br from-green-500 to-green-700 rounded-3xl shadow-xl hover:shadow-2xl transform hover:-translate-y-2 transition-all duration-300 ease-out p-8 text-white"
          >
            {/* 배경 장식 효과 */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-white opacity-10 rounded-full -translate-y-16 translate-x-16"></div>
            <div className="absolute bottom-0 left-0 w-24 h-24 bg-white opacity-10 rounded-full translate-y-12 -translate-x-12"></div>
            <div className="absolute -bottom-20 -right-20 w-64 h-64 bg-white opacity-5 rounded-full"></div>

            <div className="relative z-10 h-full flex flex-col items-center justify-center">
              <div className="text-7xl mb-6 transform group-hover:scale-110 transition-transform duration-300">
                ⚙️
              </div>
              <h2 className="text-3xl font-bold mb-3">관리자 모드</h2>
              <p className="text-green-100 text-lg text-center leading-relaxed px-4">
                프롬프트를 관리하고
                <br />
                시스템을 설정하세요
              </p>
            </div>
          </button>
        </div>
      </div>

      {/* 부가 정보 */}
      <div className="mt-16 text-center">
        <p className="text-gray-500 text-sm">
          모드는 언제든지 변경할 수 있습니다
        </p>
      </div>
    </div>
  );
};

export default ModeSelection;
