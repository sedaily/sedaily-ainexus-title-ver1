import React from "react";
import { Link, useLocation } from "react-router-dom";
import { PlusIcon, DocumentTextIcon } from "@heroicons/react/24/outline";

const Header = () => {
  const location = useLocation();

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* 로고 및 제목 */}
          <div className="flex items-center">
            <Link
              to="/"
              className="flex items-center space-x-2 text-gray-900 hover:text-blue-600"
            >
              <DocumentTextIcon className="h-8 w-8 text-blue-600" />
              <h1 className="text-xl font-bold">TITLE-NOMICS</h1>
            </Link>
            <span className="ml-2 text-sm text-gray-500">
              AWS Bedrock DIY 제목 생성기
            </span>
          </div>

          {/* 네비게이션 */}
          <nav className="flex items-center space-x-4">
            <Link
              to="/"
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                location.pathname === "/"
                  ? "bg-blue-100 text-blue-700"
                  : "text-gray-700 hover:text-blue-600 hover:bg-gray-100"
              }`}
            >
              프로젝트 목록
            </Link>
            <Link
              to="/create"
              className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 ${
                location.pathname === "/create" ? "bg-blue-700" : ""
              }`}
            >
              <PlusIcon className="h-4 w-4 mr-2" />새 프로젝트
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header;
