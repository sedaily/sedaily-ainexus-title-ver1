import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { PlusIcon, DocumentTextIcon, UserIcon, ChevronDownIcon } from "@heroicons/react/24/outline";
import { useAuth } from "../contexts/AuthContext";

const Header = () => {
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

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
            {isAuthenticated ? (
              <>
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
                
                {/* 사용자 메뉴 */}
                <div className="relative">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center space-x-2 text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    <UserIcon className="h-5 w-5" />
                    <span>{user?.name || user?.email || "사용자"}</span>
                    <ChevronDownIcon className="h-4 w-4" />
                  </button>
                  
                  {showUserMenu && (
                    <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5">
                      <div className="py-1">
                        <div className="px-4 py-2 text-sm text-gray-500 border-b">
                          {user?.email}
                        </div>
                        <button
                          onClick={() => {
                            logout();
                            setShowUserMenu(false);
                          }}
                          className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        >
                          로그아웃
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <Link
                to="/login"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                로그인
              </Link>
            )}
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header;
