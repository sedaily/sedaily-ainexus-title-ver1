import React, { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  EllipsisHorizontalIcon,
  TrashIcon,
  PencilIcon,
  CalendarIcon,
  DocumentTextIcon,
  TagIcon,
  SparklesIcon,
} from "@heroicons/react/24/outline";
import {
  formatTokenCount,
  formatFileSize,
  getCategoryColorClasses,
} from "../../services/api";

const ProjectCard = ({
  project,
  stats,
  onDelete,
  onEdit,
  onCategoryChange,
  onDragStart,
  onDragEnd,
  viewMode,
  userCategories,
  isDragging,
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef(null);

  // 외부 클릭 시 메뉴 닫기
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleCardClick = (e) => {
    // 메뉴 버튼이나 드롭다운 클릭 시 카드 클릭 이벤트 방지
    if (
      e.target.closest(".menu-button") ||
      e.target.closest(".dropdown-menu")
    ) {
      e.preventDefault();
      e.stopPropagation();
    }
  };

  const categoryInfo = userCategories.find(
    (cat) => cat.id === project.category
  ) || { name: project.category || "기본", color: "blue" };

  const cardContent = (
    <div
      className={`bg-white rounded-xl border transition-all duration-300 hover:shadow-lg group ${
        isDragging ? "opacity-50 scale-95" : "hover:border-blue-300"
      } ${viewMode === "list" ? "p-4" : "p-6"}`}
      draggable
      onDragStart={(e) => onDragStart(e, project)}
      onDragEnd={onDragEnd}
      onClick={handleCardClick}
    >
      {/* 카드 헤더 */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-2">
            <span
              className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getCategoryColorClasses(
                categoryInfo.color
              )}`}
            >
              <TagIcon className="h-3 w-3 mr-1" />
              {categoryInfo.name}
            </span>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
            {project.name || project.title}
          </h3>
          {project.description && (
            <p className="text-gray-600 text-sm line-clamp-2">
              {project.description}
            </p>
          )}
        </div>

        {/* 메뉴 버튼 */}
        <div className="relative ml-4" ref={menuRef}>
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setShowMenu(!showMenu);
            }}
            className="menu-button opacity-0 group-hover:opacity-100 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-all"
          >
            <EllipsisHorizontalIcon className="h-5 w-5" />
          </button>

          {/* 드롭다운 메뉴 */}
          {showMenu && (
            <div className="dropdown-menu absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-20">
              <Link
                to={`/projects/${project.projectId}`}
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(false);
                }}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center"
              >
                <PencilIcon className="h-4 w-4 mr-2" />
                편집
              </Link>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onDelete(project.projectId, project.name || project.title);
                  setShowMenu(false);
                }}
                className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center"
              >
                <TrashIcon className="h-4 w-4 mr-2" />
                삭제
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 프로젝트 통계 */}
      {stats && (
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center">
            <div className="flex items-center justify-center mb-1">
              <DocumentTextIcon className="h-4 w-4 text-blue-500 mr-1" />
              <span className="text-xs text-gray-500">프롬프트</span>
            </div>
            <div className="text-lg font-semibold text-gray-900">
              {stats.totalCards || 0}
            </div>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center mb-1">
              <SparklesIcon className="h-4 w-4 text-purple-500 mr-1" />
              <span className="text-xs text-gray-500">토큰</span>
            </div>
            <div className="text-lg font-semibold text-gray-900">
              {formatTokenCount(stats.totalTokens || 0)}
            </div>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center mb-1">
              <TagIcon className="h-4 w-4 text-green-500 mr-1" />
              <span className="text-xs text-gray-500">활성</span>
            </div>
            <div className="text-lg font-semibold text-gray-900">
              {stats.enabledCards || 0}
            </div>
          </div>
        </div>
      )}

      {/* 카드 푸터 */}
      <div className="flex items-center justify-between text-xs text-gray-500 border-t border-gray-100 pt-3">
        <div className="flex items-center">
          <CalendarIcon className="h-3 w-3 mr-1" />
          {new Date(project.createdAt).toLocaleDateString("ko-KR")}
        </div>
        <div className="flex items-center space-x-3">
          {project.lastModified && (
            <span>
              수정: {new Date(project.lastModified).toLocaleDateString("ko-KR")}
            </span>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <Link
      to={`/projects/${project.projectId}`}
      className={`block transition-transform duration-200 ${
        isDragging ? "" : "hover:scale-[1.02]"
      }`}
    >
      {cardContent}
    </Link>
  );
};

export default ProjectCard;
