import React, { useState, useEffect, useMemo, useRef } from "react";
import { Link } from "react-router-dom";
import { toast } from "react-hot-toast";
import {
  FolderOpenIcon,
  PlusIcon,
  EllipsisHorizontalIcon,
  TrashIcon,
  PencilIcon,
  CalendarIcon,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  Squares2X2Icon,
  ListBulletIcon,
  TagIcon,
  SparklesIcon,
  ArrowPathIcon,
  Cog6ToothIcon,
} from "@heroicons/react/24/outline";
import {
  projectAPI,
  handleAPIError,
  DEFAULT_PROJECT_CATEGORIES,
  categoryAPI,
  projectCategoryAPI,
  getCategoryInfo,
  getCategoryColorClasses,
  filterProjects,
  formatTokenCount,
  formatFileSize,
  calculatePromptStats,
  promptCardAPI,
  COLOR_OPTIONS,
} from "../services/api";

const ProjectList = () => {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 필터링 상태
  const [activeCategory, setActiveCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("created");
  const [viewMode, setViewMode] = useState("grid");

  // 카테고리 상태
  const [userCategories, setUserCategories] = useState([]);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [showCategoryManager, setShowCategoryManager] = useState(false);

  // 드래그앤드롭 상태
  const [draggedProject, setDraggedProject] = useState(null);
  const [dropTargetCategory, setDropTargetCategory] = useState(null);

  // 통계 상태
  const [projectStats, setProjectStats] = useState({});
  const [overallStats, setOverallStats] = useState({
    totalProjects: 0,
    totalPrompts: 0,
    totalTokens: 0,
    categoriesUsed: 0,
  });

  useEffect(() => {
    loadProjects();
    loadUserCategories();
  }, []);

  const loadUserCategories = async () => {
    try {
      const data = await categoryAPI.getUserCategories();
      setUserCategories(data.categories || []);
    } catch (error) {
      console.error("카테고리 로드 실패:", error);
      setUserCategories(DEFAULT_PROJECT_CATEGORIES);
    }
  };

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await projectAPI.getProjects();
      const projectsWithStats = data.projects || [];

      // 각 프로젝트별 프롬프트 통계 로드
      const statsPromises = projectsWithStats.map(async (project) => {
        try {
          const promptsData = await promptCardAPI.getPromptCards(
            project.projectId,
            true,
            true
          );
          const stats = calculatePromptStats(promptsData.promptCards || []);
          return { projectId: project.projectId, stats };
        } catch (err) {
          console.error(`프로젝트 ${project.projectId} 통계 로드 실패:`, err);
          return { projectId: project.projectId, stats: null };
        }
      });

      const statsResults = await Promise.all(statsPromises);
      const statsMap = {};
      statsResults.forEach(({ projectId, stats }) => {
        statsMap[projectId] = stats;
      });

      setProjectStats(statsMap);
      setProjects(projectsWithStats);

      // 전체 통계 계산
      const overall = {
        totalProjects: projectsWithStats.length,
        totalPrompts: Object.values(statsMap).reduce(
          (sum, stats) => sum + (stats?.totalCards || 0),
          0
        ),
        totalTokens: Object.values(statsMap).reduce(
          (sum, stats) => sum + (stats?.totalTokens || 0),
          0
        ),
        categoriesUsed: new Set(
          projectsWithStats.map((p) => p.category).filter(Boolean)
        ).size,
      };
      setOverallStats(overall);
    } catch (err) {
      const errorInfo = handleAPIError(err);
      setError(errorInfo.message);
      toast.error(errorInfo.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteProject = async (projectId, projectName) => {
    if (!window.confirm(`"${projectName}" 프로젝트를 삭제하시겠습니까?`)) {
      return;
    }

    try {
      await projectAPI.deleteProject(projectId);
      toast.success("프로젝트가 삭제되었습니다");
      loadProjects();
    } catch (err) {
      const errorInfo = handleAPIError(err);
      toast.error(errorInfo.message);
    }
  };

  // 프로젝트 카테고리 변경
  const changeProjectCategory = async (projectId, categoryId) => {
    try {
      await projectCategoryAPI.updateProjectCategory(projectId, categoryId);
      toast.success("카테고리가 변경되었습니다");
      loadProjects();
    } catch (err) {
      toast.error("카테고리 변경에 실패했습니다");
    }
  };

  // 드래그앤드롭 핸들러들
  const handleDragStart = (e, project) => {
    setDraggedProject(project);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/html", e.target);
  };

  const handleDragOver = (e, categoryId) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDropTargetCategory(categoryId);
  };

  const handleDragLeave = (e) => {
    // 드래그가 카테고리 영역을 벗어날 때
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setDropTargetCategory(null);
    }
  };

  const handleDrop = async (e, categoryId) => {
    e.preventDefault();
    setDropTargetCategory(null);
    
    if (draggedProject && categoryId !== draggedProject.category) {
      await changeProjectCategory(draggedProject.projectId, categoryId);
    }
    setDraggedProject(null);
  };

  const handleDragEnd = () => {
    setDraggedProject(null);
    setDropTargetCategory(null);
  };

  // 필터링된 프로젝트 목록
  const filteredProjects = useMemo(() => {
    return filterProjects(projects, {
      category: activeCategory,
      searchQuery,
      sortBy,
    });
  }, [projects, activeCategory, searchQuery, sortBy]);

  // 카테고리별 프로젝트 수
  const categoryStats = useMemo(() => {
    const stats = { all: projects.length };
    userCategories.forEach((category) => {
      stats[category.id] = projects.filter(
        (p) => p.category === category.id
      ).length;
    });
    return stats;
  }, [projects, userCategories]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">프로젝트 목록을 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">⚠️ 오류가 발생했습니다</div>
        <p className="text-gray-600 mb-6">{error}</p>
        <button
          onClick={loadProjects}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
        >
          다시 시도
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 헤더 & 전체 통계 */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">프로젝트 목록</h2>
          <p className="text-gray-600 mt-1">
            AI 제목 생성 프로젝트를 관리하고 새로운 프로젝트를 생성하세요
          </p>
        </div>

        {/* 전체 통계 */}
        <div className="flex items-center space-x-6 bg-white rounded-xl border border-gray-200 px-6 py-4 shadow-sm">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {overallStats.totalProjects}
            </div>
            <div className="text-xs text-gray-500">프로젝트</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {overallStats.totalPrompts}
            </div>
            <div className="text-xs text-gray-500">프롬프트</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {formatTokenCount(overallStats.totalTokens)}
            </div>
            <div className="text-xs text-gray-500">토큰</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {overallStats.categoriesUsed}
            </div>
            <div className="text-xs text-gray-500">카테고리</div>
          </div>
        </div>
      </div>

      {/* 드래그 안내 메시지 */}
      {draggedProject && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            <p className="text-blue-700 font-medium">
              "{draggedProject.name}" 프로젝트를 원하는 카테고리에 드래그해서 놓으세요
            </p>
          </div>
        </div>
      )}

      {/* 필터링 바 */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        {/* 카테고리 탭 */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveCategory("all")}
              onDragOver={(e) => handleDragOver(e, "all")}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, "all")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeCategory === "all"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              } ${
                dropTargetCategory === "all" && draggedProject
                  ? "ring-2 ring-blue-400 bg-blue-100 scale-105"
                  : ""
              }`}
            >
              전체 ({categoryStats.all})
              {dropTargetCategory === "all" && draggedProject && (
                <span className="ml-2 text-xs">← 여기에 놓기</span>
              )}
            </button>
            {userCategories.map((category) => (
              <button
                key={category.id}
                onClick={() => setActiveCategory(category.id)}
                onDragOver={(e) => handleDragOver(e, category.id)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, category.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
                  activeCategory === category.id
                    ? `bg-${category.color}-600 text-white`
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                } ${
                  dropTargetCategory === category.id && draggedProject
                    ? `ring-2 ring-${category.color}-400 bg-${category.color}-100 scale-105`
                    : ""
                }`}
              >
                <div
                  className={`w-2 h-2 rounded-full bg-${category.color}-500`}
                ></div>
                <span>{category.name}</span>
                <span className="bg-white bg-opacity-20 px-2 py-0.5 rounded-full text-xs">
                  {categoryStats[category.id] || 0}
                </span>
                {dropTargetCategory === category.id && draggedProject && (
                  <span className="text-xs">← 놓기</span>
                )}
              </button>
            ))}
          </div>

          <button
            onClick={() => setShowCategoryManager(true)}
            className="flex items-center px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-colors"
          >
            <Cog6ToothIcon className="h-4 w-4 mr-1" />
            카테고리 관리
          </button>
        </div>

        {/* 검색 및 정렬 */}
        <div className="flex flex-col sm:flex-row gap-4">
          {/* 검색바 */}
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="프로젝트 이름, 설명, 태그로 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* 정렬 옵션 */}
          <div className="flex items-center space-x-3">
            <FunnelIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="pl-4 pr-8 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-0 whitespace-nowrap"
            >
              <option value="created">생성일순</option>
              <option value="updated">수정일순</option>
              <option value="name">이름순</option>
            </select>
          </div>

          {/* 뷰 모드 */}
          <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode("grid")}
              className={`p-2 rounded-md ${
                viewMode === "grid" ? "bg-white shadow-sm" : "hover:bg-gray-200"
              }`}
            >
              <Squares2X2Icon className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode("list")}
              className={`p-2 rounded-md ${
                viewMode === "list" ? "bg-white shadow-sm" : "hover:bg-gray-200"
              }`}
            >
              <ListBulletIcon className="h-4 w-4" />
            </button>
          </div>

          {/* 새 프로젝트 버튼 */}
          <Link
            to="/create"
            className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            <PlusIcon className="h-4 w-4 mr-2" />새 프로젝트
          </Link>
        </div>
      </div>

      {/* 프로젝트 목록 */}
      {filteredProjects.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <FolderOpenIcon className="mx-auto h-16 w-16 text-gray-400 mb-4" />
          <h3 className="text-xl font-medium text-gray-900 mb-2">
            {searchQuery || activeCategory !== "all"
              ? "조건에 맞는 프로젝트가 없습니다"
              : "프로젝트가 없습니다"}
          </h3>
          <p className="text-gray-500 mb-8">
            {searchQuery || activeCategory !== "all"
              ? "다른 조건으로 검색해보세요"
              : "첫 번째 프로젝트를 생성해보세요"}
          </p>
          <Link
            to="/create"
            className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            <PlusIcon className="h-4 w-4 mr-2" />새 프로젝트 생성
          </Link>
        </div>
      ) : (
        <div
          className={
            viewMode === "grid"
              ? "grid gap-6 md:grid-cols-2 lg:grid-cols-3"
              : "space-y-4"
          }
        >
          {filteredProjects.map((project) => (
            <ProjectCard
              key={project.projectId}
              project={project}
              stats={projectStats[project.projectId]}
              onDelete={deleteProject}
              onCategoryChange={changeProjectCategory}
              onDragStart={handleDragStart}
              onDragEnd={handleDragEnd}
              viewMode={viewMode}
              userCategories={userCategories}
              isDragging={draggedProject?.projectId === project.projectId}
            />
          ))}
        </div>
      )}

      {/* 카테고리 관리 모달 */}
      {showCategoryManager && (
        <CategoryManager
          onClose={() => setShowCategoryManager(false)}
          onSave={loadUserCategories}
          categories={userCategories}
        />
      )}
    </div>
  );
};

const ProjectCard = ({
  project,
  stats,
  onDelete,
  onCategoryChange,
  onDragStart,
  onDragEnd,
  viewMode,
  userCategories,
  isDragging,
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const [showCategoryMenu, setShowCategoryMenu] = useState(false);
  const menuRef = useRef(null);
  const categoryMenuRef = useRef(null);
  const categoryInfo = getCategoryInfo(project.category, userCategories);

  // 외부 클릭 시 메뉴 닫기
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowMenu(false);
      }
      if (
        categoryMenuRef.current &&
        !categoryMenuRef.current.contains(event.target)
      ) {
        setShowCategoryMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  if (viewMode === "list") {
    return (
      <div 
        draggable
        onDragStart={(e) => onDragStart(e, project)}
        onDragEnd={onDragEnd}
        className={`bg-white rounded-xl border border-gray-200 hover:shadow-md transition-all cursor-move ${
          isDragging ? "opacity-50 scale-95 shadow-lg" : ""
        }`}
      >
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4 flex-1">
              <div className="flex-shrink-0">
                <DocumentTextIcon className="h-12 w-12 text-blue-600" />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-3 mb-2">
                  <h3 className="text-xl font-semibold text-gray-900 truncate">
                    {project.name}
                  </h3>
                  <div className="relative" ref={categoryMenuRef}>
                    <button
                      onClick={() => setShowCategoryMenu(!showCategoryMenu)}
                      className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border cursor-pointer hover:shadow-sm transition-all ${getCategoryColorClasses(
                        categoryInfo.color
                      )}`}
                    >
                      <div
                        className={`w-2 h-2 rounded-full bg-${categoryInfo.color}-500 mr-2`}
                      ></div>
                      {categoryInfo.name}
                    </button>

                    {showCategoryMenu && (
                      <div className="absolute left-0 mt-2 w-48 bg-white rounded-lg shadow-lg ring-1 ring-black ring-opacity-5 z-10">
                        <div className="py-1">
                          {userCategories.map((category) => (
                            <button
                              key={category.id}
                              onClick={() => {
                                onCategoryChange(
                                  project.projectId,
                                  category.id
                                );
                                setShowCategoryMenu(false);
                              }}
                              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                            >
                              <div
                                className={`w-2 h-2 rounded-full bg-${category.color}-500 mr-3`}
                              ></div>
                              {category.name}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                <p className="text-gray-500 truncate mb-3">
                  {project.description || "설명 없음"}
                </p>
                <div className="flex items-center space-x-6 text-sm text-gray-500">
                  <div className="flex items-center space-x-1">
                    <CalendarIcon className="h-4 w-4" />
                    <span>
                      {new Date(project.createdAt).toLocaleDateString("ko-KR")}
                    </span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <DocumentTextIcon className="h-4 w-4" />
                    <span>{stats?.totalCards || 0}개 프롬프트</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <SparklesIcon className="h-4 w-4" />
                    <span>
                      {formatTokenCount(stats?.totalTokens || 0)} 토큰
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Link
                to={`/projects/${project.projectId}`}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                열기
              </Link>

              <div className="relative" ref={menuRef}>
                <button
                  onClick={() => setShowMenu(!showMenu)}
                  className="text-gray-400 hover:text-gray-600 p-2 rounded-lg hover:bg-gray-100"
                >
                  <EllipsisHorizontalIcon className="h-5 w-5" />
                </button>

                {showMenu && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg ring-1 ring-black ring-opacity-5 z-10">
                    <div className="py-1">
                      <Link
                        to={`/projects/${project.projectId}`}
                        className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                        onClick={() => setShowMenu(false)}
                      >
                        <PencilIcon className="h-4 w-4 mr-3" />
                        편집
                      </Link>
                      <button
                        onClick={() => {
                          onDelete(project.projectId, project.name);
                          setShowMenu(false);
                        }}
                        className="flex items-center w-full px-4 py-2 text-sm text-red-700 hover:bg-red-50"
                      >
                        <TrashIcon className="h-4 w-4 mr-3" />
                        삭제
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      draggable
      onDragStart={(e) => onDragStart(e, project)}
      onDragEnd={onDragEnd}
      className={`bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-all cursor-move ${
        isDragging ? "opacity-50 scale-95 shadow-lg" : ""
      }`}
    >
      <div className="p-6">
        <div className="flex justify-between items-start mb-4">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <DocumentTextIcon className="h-8 w-8 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 truncate">
                {project.name}
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                {project.description || "설명 없음"}
              </p>
            </div>
          </div>

          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100"
            >
              <EllipsisHorizontalIcon className="h-5 w-5" />
            </button>

            {showMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg ring-1 ring-black ring-opacity-5 z-10">
                <div className="py-1">
                  <Link
                    to={`/projects/${project.projectId}`}
                    className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    onClick={() => setShowMenu(false)}
                  >
                    <PencilIcon className="h-4 w-4 mr-3" />
                    편집
                  </Link>
                  <button
                    onClick={() => {
                      onDelete(project.projectId, project.name);
                      setShowMenu(false);
                    }}
                    className="flex items-center w-full px-4 py-2 text-sm text-red-700 hover:bg-red-50"
                  >
                    <TrashIcon className="h-4 w-4 mr-3" />
                    삭제
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 카테고리 배지 */}
        <div className="flex items-center justify-between mb-4">
          <div className="relative" ref={categoryMenuRef}>
            <button
              onClick={() => setShowCategoryMenu(!showCategoryMenu)}
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border cursor-pointer hover:shadow-sm transition-all ${getCategoryColorClasses(
                categoryInfo.color
              )}`}
            >
              <div
                className={`w-2 h-2 rounded-full bg-${categoryInfo.color}-500 mr-2`}
              ></div>
              {categoryInfo.name}
            </button>

            {showCategoryMenu && (
              <div className="absolute left-0 mt-2 w-48 bg-white rounded-lg shadow-lg ring-1 ring-black ring-opacity-5 z-10">
                <div className="py-1">
                  {userCategories.map((category) => (
                    <button
                      key={category.id}
                      onClick={() => {
                        onCategoryChange(project.projectId, category.id);
                        setShowCategoryMenu(false);
                      }}
                      className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <div
                        className={`w-2 h-2 rounded-full bg-${category.color}-500 mr-3`}
                      ></div>
                      {category.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              project.status === "active"
                ? "bg-green-100 text-green-800"
                : "bg-gray-100 text-gray-800"
            }`}
          >
            {project.status === "active" ? "활성" : "비활성"}
          </span>
        </div>

        {/* 통계 정보 */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="bg-blue-50 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-blue-600 font-medium">
                프롬프트
              </span>
              <DocumentTextIcon className="h-4 w-4 text-blue-600" />
            </div>
            <div className="text-lg font-bold text-blue-700 mt-1">
              {stats?.totalCards || 0}개
            </div>
          </div>

          <div className="bg-purple-50 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-purple-600 font-medium">토큰</span>
              <SparklesIcon className="h-4 w-4 text-purple-600" />
            </div>
            <div className="text-lg font-bold text-purple-700 mt-1">
              {formatTokenCount(stats?.totalTokens || 0)}
            </div>
          </div>
        </div>

        {/* 세부 정보 */}
        <div className="space-y-2 mb-4">
          <div className="flex items-center text-sm text-gray-500">
            <CalendarIcon className="h-4 w-4 mr-2" />
            생성일: {new Date(project.createdAt).toLocaleDateString("ko-KR")}
          </div>

          {project.tags && project.tags.length > 0 && (
            <div className="flex items-center text-sm text-gray-500">
              <TagIcon className="h-4 w-4 mr-2" />
              <div className="flex flex-wrap gap-1">
                {project.tags.slice(0, 3).map((tag, index) => (
                  <span
                    key={index}
                    className="bg-gray-100 px-2 py-0.5 rounded text-xs"
                  >
                    {tag}
                  </span>
                ))}
                {project.tags.length > 3 && (
                  <span className="text-xs text-gray-400">
                    +{project.tags.length - 3}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* 프롬프트 용량 바 */}
        {stats && stats.totalTokens > 0 && (
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
              <span>프롬프트 용량</span>
              <span>{formatFileSize(stats.totalSize)}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300"
                style={{
                  width: `${Math.min((stats.totalTokens / 10000) * 100, 100)}%`,
                }}
              ></div>
            </div>
          </div>
        )}

        <div className="mt-6">
          <Link
            to={`/projects/${project.projectId}`}
            className="w-full inline-flex justify-center items-center px-4 py-2 border border-blue-600 text-sm font-medium rounded-lg text-blue-600 bg-white hover:bg-blue-50"
          >
            프로젝트 열기
          </Link>
        </div>
      </div>
    </div>
  );
};

// 카테고리 관리 모달
const CategoryManager = ({ onClose, onSave, categories }) => {
  const [userCategories, setUserCategories] = useState(categories);
  const [editingCategory, setEditingCategory] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  const handleDeleteCategory = async (categoryId) => {
    if (!window.confirm("정말로 이 카테고리를 삭제하시겠습니까?")) {
      return;
    }

    try {
      await categoryAPI.deleteCategory(categoryId);
      toast.success("카테고리가 삭제되었습니다");
      const updatedCategories = userCategories.filter(
        (cat) => cat.id !== categoryId
      );
      setUserCategories(updatedCategories);
      onSave();
    } catch (error) {
      toast.error(error.message || "카테고리 삭제에 실패했습니다");
    }
  };

  const handleUpdateCategory = async (categoryId, data) => {
    try {
      await categoryAPI.updateCategory(categoryId, data);
      toast.success("카테고리가 수정되었습니다");

      // 로컬 상태 업데이트
      const updatedCategories = userCategories.map((cat) =>
        cat.id === categoryId ? { ...cat, ...data } : cat
      );
      setUserCategories(updatedCategories);
      setEditingCategory(null);
      onSave();
    } catch (error) {
      toast.error("카테고리 수정에 실패했습니다");
    }
  };

  const handleCreateCategory = async (data) => {
    try {
      const newCategory = await categoryAPI.createCategory(data);
      toast.success("카테고리가 생성되었습니다");

      // 로컬 상태 업데이트
      setUserCategories([...userCategories, newCategory]);
      setShowCreateForm(false);
      onSave();
    } catch (error) {
      toast.error("카테고리 생성에 실패했습니다");
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-gray-200 sticky top-0 bg-white">
          <h3 className="text-lg font-semibold text-gray-900">카테고리 관리</h3>
        </div>

        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h4 className="font-medium text-gray-900">카테고리 목록</h4>
            <button
              onClick={() => setShowCreateForm(true)}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <PlusIcon className="h-4 w-4 mr-2" />새 카테고리
            </button>
          </div>

          {/* 새 카테고리 생성 폼 */}
          {showCreateForm && (
            <div className="mb-6 p-4 border-2 border-blue-200 rounded-lg bg-blue-50">
              <h5 className="font-medium text-gray-900 mb-4">
                새 카테고리 생성
              </h5>
              <CategoryForm
                onSubmit={handleCreateCategory}
                onCancel={() => setShowCreateForm(false)}
              />
            </div>
          )}

          {/* 카테고리 목록 */}
          <div className="space-y-4">
            {userCategories.map((category) => (
              <div key={category.id}>
                {editingCategory?.id === category.id ? (
                  // 편집 모드
                  <div className="p-4 border-2 border-orange-200 rounded-lg bg-orange-50">
                    <h5 className="font-medium text-gray-900 mb-4">
                      카테고리 편집
                    </h5>
                    <CategoryForm
                      category={editingCategory}
                      onSubmit={(data) =>
                        handleUpdateCategory(editingCategory.id, data)
                      }
                      onCancel={() => setEditingCategory(null)}
                    />
                  </div>
                ) : (
                  // 일반 표시 모드
                  <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                    <div className="flex items-center space-x-4">
                      <div
                        className={`w-4 h-4 rounded-full bg-${category.color}-500 flex-shrink-0`}
                      ></div>
                      <div>
                        <h5 className="font-medium text-gray-900">
                          {category.name}
                        </h5>
                        <p className="text-sm text-gray-500">
                          {category.description || "설명 없음"}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {category.isDefault && (
                        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                          기본 카테고리
                        </span>
                      )}
                      <button
                        onClick={() => setEditingCategory(category)}
                        className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="편집"
                      >
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteCategory(category.id)}
                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title={category.isDefault ? "기본 카테고리도 삭제 가능합니다" : "삭제"}
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end bg-gray-50">
          <button
            onClick={onClose}
            className="px-6 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
};

// 카테고리 폼 컴포넌트
const CategoryForm = ({ category, onSubmit, onCancel }) => {
  const [formData, setFormData] = useState({
    name: category?.name || "",
    description: category?.description || "",
    color: category?.color || "blue",
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error("카테고리 이름을 입력해주세요");
      return;
    }
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          카테고리 이름 *
        </label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          설명
        </label>
        <textarea
          value={formData.description}
          onChange={(e) =>
            setFormData({ ...formData, description: e.target.value })
          }
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          색상
        </label>
        <div className="flex flex-wrap gap-2">
          {COLOR_OPTIONS.map((color) => (
            <button
              key={color.id}
              type="button"
              onClick={() => setFormData({ ...formData, color: color.id })}
              className={`w-8 h-8 rounded-full ${color.class} ${
                formData.color === color.id
                  ? "ring-2 ring-offset-2 ring-blue-500"
                  : ""
              }`}
              title={color.name}
            />
          ))}
        </div>
      </div>

      <div className="flex justify-end space-x-3">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          취소
        </button>
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          {category ? "수정" : "생성"}
        </button>
      </div>
    </form>
  );
};

export default ProjectList;
