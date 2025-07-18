import React from "react";
import { Link } from "react-router-dom";
import { DocumentTextIcon } from "@heroicons/react/24/outline";
import DarkModeToggle from "./DarkModeToggle";

const Header = () => {
  return (
    <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* 로고 */}
          <Link to="/" className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-blue-600 dark:bg-blue-500 rounded-lg flex items-center justify-center">
              <DocumentTextIcon className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">TITLE-NOMICS</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">AI 제목 생성기</p>
            </div>
          </Link>
          
          {/* 다크모드 토글 */}
          <DarkModeToggle />
        </div>
      </div>
    </header>
  );
};

export default Header;
