import React, { useState, useEffect, useMemo, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
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
  XMarkIcon,
  ChevronDownIcon,
  CheckIcon,
} from "@heroicons/react/24/outline";
import { projectAPI, handleAPIError, filterProjects } from "../services/api";
import CreateProject from "./CreateProject";

const ProjectList = () => {
  const navigate = useNavigate();
  // 상태 관리
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("updated");
  const [viewMode, setViewMode] = useState("grid");
  const [sortDropdownOpen, setSortDropdownOpen] = useState(false);
  const sortDropdownRef = useRef(null);

  // 프로젝트 편집 상태
  const [editingProject, setEditingProject] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  // 드롭다운 외부 클릭 감지
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        sortDropdownRef.current &&
        !sortDropdownRef.current.contains(event.target)
      ) {
        setSortDropdownOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const loadProjects = async () => {
    try {
      console.log("🔄 loadProjects 시작");
      setLoading(true);
      setError(null);
      const data = await projectAPI.getProjects();
      const projectsWithStats = data.projects || [];
      console.log("📊 로드된 프로젝트 수:", projectsWithStats.length);
      console.log("📋 프로젝트 목록:", projectsWithStats);

      setProjects(projectsWithStats);
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

    // 낙관적 업데이트: 즉시 UI에서 프로젝트 제거
    const originalProjects = [...projects];
    const updatedProjects = projects.filter((p) => p.projectId !== projectId);
    setProjects(updatedProjects);

    // 즉시 성공 토스트 표시
    toast.success("프로젝트가 삭제되었습니다");

    try {
      // 백그라운드에서 실제 삭제 진행
      await projectAPI.deleteProject(projectId);
      console.log("프로젝트 삭제 성공:", projectId);
    } catch (err) {
      console.error("프로젝트 삭제 오류:", err);

      // 실패 시 원래 상태로 복원
      setProjects(originalProjects);

      let errorMessage = "프로젝트 삭제에 실패했습니다";

      if (err.response?.status === 403) {
        errorMessage =
          "삭제 권한이 없습니다. S3 파일 삭제 권한을 확인해주세요.";
      } else if (err.response?.status === 404) {
        errorMessage = "이미 삭제된 프로젝트입니다";
        // 404의 경우 실제로는 삭제된 것이므로 복원하지 않음
        return;
      } else if (err.response) {
        errorMessage =
          err.response.data?.message || `서버 오류 (${err.response.status})`;
      } else if (err.request) {
        errorMessage = "네트워크 오류: CORS 또는 연결 문제";
      }

      toast.error(errorMessage);
    }
  };

  // 프로젝트 편집 함수들
  const handleEditProject = (project) => {
    setEditingProject(project);
    setShowEditModal(true);
  };

  const handleUpdateProject = async (projectData) => {
    try {
      await projectAPI.updateProject(editingProject.projectId, projectData);
      toast.success("프로젝트가 수정되었습니다");
      setShowEditModal(false);
      setEditingProject(null);
      loadProjects();
    } catch (err) {
      const errorInfo = handleAPIError(err);
      toast.error(`프로젝트 수정 실패: ${errorInfo.message}`);
    }
  };

  const handleCancelEdit = () => {
    setShowEditModal(false);
    setEditingProject(null);
  };

  // 필터링된 프로젝트 목록
  const filteredProjects = useMemo(() => {
    return filterProjects(projects, {
      searchQuery,
      sortBy,
    });
  }, [projects, searchQuery, sortBy]);

  // 정렬 옵션 데이터
  const sortOptions = [
    { value: "created", label: "생성일순" },
    { value: "updated", label: "수정일순" },
    { value: "name", label: "이름순" },
  ];

  const currentSortOption = sortOptions.find(
    (option) => option.value === sortBy
  );

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

  const handleCreateSuccess = () => {
    console.log("📝 handleCreateSuccess 호출됨 - 프로젝트 목록 새로고침 시작");
    loadProjects(); // 프로젝트 목록 새로고침
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">프로젝트 목록</h2>
          <p className="text-gray-600 mt-1">
            AI 제목 생성 프로젝트를 관리하고 새로운 프로젝트를 생성하세요
          </p>
        </div>
      </div>

      {/* 필터링 바 */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
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

          {/* 정렬 옵션 - 커스텀 드롭다운 */}
          <div className="flex items-center space-x-3">
            <FunnelIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
            <div className="relative" ref={sortDropdownRef}>
              <button
                onClick={() => setSortDropdownOpen(!sortDropdownOpen)}
                className="flex items-center justify-between pl-4 pr-3 py-3 bg-white border border-gray-300 rounded-lg hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 min-w-[140px]"
              >
                <div className="flex items-center space-x-2">
                  <span className="text-gray-700 font-medium">
                    {currentSortOption?.label}
                  </span>
                </div>
                <ChevronDownIcon
                  className={`h-4 w-4 text-gray-400 transition-transform duration-200 ${
                    sortDropdownOpen ? "rotate-180" : ""
                  }`}
                />
              </button>

              {/* 드롭다운 메뉴 */}
              {sortDropdownOpen && (
                <div className="absolute top-full left-0 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg z-50 overflow-hidden">
                  {sortOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setSortBy(option.value);
                        setSortDropdownOpen(false);
                      }}
                      className={`w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors duration-150 ${
                        sortBy === option.value
                          ? "bg-blue-50 text-blue-600"
                          : "text-gray-700"
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        <span className="font-medium">{option.label}</span>
                      </div>
                      {sortBy === option.value && (
                        <CheckIcon className="h-4 w-4 text-blue-600" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
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
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            <PlusIcon className="h-4 w-4 mr-2" />새 프로젝트
          </button>
        </div>
      </div>

      {/* 프로젝트 목록 */}
      {filteredProjects.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <FolderOpenIcon className="mx-auto h-16 w-16 text-gray-400 mb-4" />
          <h3 className="text-xl font-medium text-gray-900 mb-2">
            {searchQuery
              ? "조건에 맞는 프로젝트가 없습니다"
              : "프로젝트가 없습니다"}
          </h3>
          <p className="text-gray-500 mb-8">
            {searchQuery
              ? "다른 조건으로 검색해보세요"
              : "첫 번째 프로젝트를 생성해보세요"}
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            <PlusIcon className="h-4 w-4 mr-2" />새 프로젝트 생성
          </button>
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
              onDelete={deleteProject}
              onEdit={handleEditProject}
              viewMode={viewMode}
              navigate={navigate}
            />
          ))}
        </div>
      )}

      {/* 새 프로젝트 생성 모달 */}
      <CreateProject
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={handleCreateSuccess}
      />

      {/* 프로젝트 편집 모달 */}
      <ProjectEditModal
        project={editingProject}
        isOpen={showEditModal}
        onSave={handleUpdateProject}
        onCancel={handleCancelEdit}
      />
    </div>
  );
};

const ProjectCard = ({ project, onDelete, onEdit, viewMode, navigate }) => {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef(null);

  // 카드 클릭 핸들러
  const handleCardClick = (e) => {
    // 메뉴 버튼을 클릭한 경우 무시
    if (e.target.closest("button") || e.target.closest("a")) {
      return;
    }
    // 프로젝트 상세 페이지로 이동
    navigate(`/projects/${project.projectId}`);
  };

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

  if (viewMode === "list") {
    return (
      <div
        onClick={handleCardClick}
        className="bg-white rounded-xl border border-gray-200 hover:shadow-md transition-all cursor-pointer"
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
                </div>
                <p className="text-gray-500 truncate mb-3">
                  {project.description || "설명 없음"}
                </p>

                {/* 날짜 */}
                <div className="flex items-center space-x-4 mb-3">
                  <div className="flex items-center text-sm text-gray-500">
                    <CalendarIcon className="h-4 w-4 mr-1.5" />
                    <span>
                      생성{" "}
                      {new Date(project.createdAt).toLocaleDateString("ko-KR")}
                    </span>
                  </div>
                  {project.updatedAt &&
                    project.updatedAt !== project.createdAt && (
                      <div className="flex items-center text-sm text-gray-500">
                        <span className="text-gray-300">•</span>
                        <span className="ml-1.5">
                          수정{" "}
                          {new Date(project.updatedAt).toLocaleDateString(
                            "ko-KR"
                          )}
                        </span>
                      </div>
                    )}
                </div>

                {/* 프롬프트 정보 */}
                <div className="flex items-center space-x-4 mb-3">
                  <div className="flex items-center text-sm text-gray-500">
                    <DocumentTextIcon className="h-4 w-4 mr-1.5" />
                    <span>프롬프트 클릭해 주세요</span>
                  </div>
                </div>

                {/* 태그 */}
                {project.tags && project.tags.length > 0 && (
                  <div className="mb-4">
                    <div className="flex items-center">
                      <TagIcon className="h-4 w-4 mr-1.5 text-gray-400" />
                      <div className="flex flex-wrap gap-1.5">
                        {project.tags.slice(0, 3).map((tag, index) => (
                          <span
                            key={index}
                            className="inline-flex items-center bg-gray-100 text-gray-600 px-2.5 py-1 rounded-full text-xs font-medium"
                          >
                            {tag}
                          </span>
                        ))}
                        {project.tags.length > 3 && (
                          <span className="inline-flex items-center text-xs text-gray-400 px-2">
                            +{project.tags.length - 3}개
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-3">
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
                      <button
                        onClick={() => {
                          onEdit(project);
                          setShowMenu(false);
                        }}
                        className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                      >
                        <PencilIcon className="h-4 w-4 mr-3" />
                        편집
                      </button>
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
      onClick={handleCardClick}
      className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-all cursor-pointer"
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
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
              title="프로젝트 옵션"
            >
              <EllipsisHorizontalIcon className="h-5 w-5" />
            </button>

            {showMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg ring-1 ring-black ring-opacity-5 z-10">
                <div className="py-1">
                  <button
                    onClick={() => {
                      onEdit(project);
                      setShowMenu(false);
                    }}
                    className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                  >
                    <PencilIcon className="h-4 w-4 mr-3" />
                    편집
                  </button>
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

        {/* 날짜 */}
        <div className="flex items-center space-x-4 mb-3">
          <div className="flex items-center text-sm text-gray-500">
            <CalendarIcon className="h-4 w-4 mr-1.5" />
            <span>
              생성 {new Date(project.createdAt).toLocaleDateString("ko-KR")}
            </span>
          </div>
          {project.updatedAt && project.updatedAt !== project.createdAt && (
            <div className="flex items-center text-sm text-gray-500">
              <span className="text-gray-300">•</span>
              <span className="ml-1.5">
                수정 {new Date(project.updatedAt).toLocaleDateString("ko-KR")}
              </span>
            </div>
          )}
        </div>

        {/* 프롬프트 정보 */}
        <div className="flex items-center space-x-4 mb-3">
          <div className="flex items-center text-sm text-gray-500">
            <DocumentTextIcon className="h-4 w-4 mr-1.5" />
            <span>프롬프트 클릭해 주세요</span>
          </div>
        </div>

        {/* 태그 */}
        {project.tags && project.tags.length > 0 && (
          <div className="mb-4">
            <div className="flex items-center">
              <TagIcon className="h-4 w-4 mr-1.5 text-gray-400" />
              <div className="flex flex-wrap gap-1.5">
                {project.tags.slice(0, 3).map((tag, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center bg-gray-100 text-gray-600 px-2.5 py-1 rounded-full text-xs font-medium"
                  >
                    {tag}
                  </span>
                ))}
                {project.tags.length > 3 && (
                  <span className="inline-flex items-center text-xs text-gray-400 px-2">
                    +{project.tags.length - 3}개
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// 프로젝트 편집 모달 컴포넌트
const ProjectEditModal = ({ project, isOpen, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    tags: [],
  });
  const [tagInput, setTagInput] = useState("");

  useEffect(() => {
    if (project) {
      setFormData({
        name: project.name || "",
        description: project.description || "",
        tags: Array.isArray(project.tags) ? [...project.tags] : [],
      });
    }
  }, [project]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error("프로젝트 이름을 입력해주세요");
      return;
    }
    onSave(formData);
  };

  const handleModalClose = () => {
    setTagInput("");
    onCancel();
  };

  // 태그 추가 함수
  const addTag = () => {
    const tag = tagInput.trim();
    if (tag && !formData.tags.includes(tag) && formData.tags.length < 10) {
      setFormData({
        ...formData,
        tags: [...formData.tags, tag],
      });
      setTagInput("");
    }
  };

  // 태그 제거 함수
  const removeTag = (tagToRemove) => {
    setFormData({
      ...formData,
      tags: formData.tags.filter((tag) => tag !== tagToRemove),
    });
  };

  // Enter 키로 태그 추가
  const handleTagKeyPress = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addTag();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg max-w-md w-full">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">프로젝트 편집</h3>
          <button
            onClick={handleModalClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              프로젝트 이름 *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="프로젝트 이름을 입력하세요"
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
              placeholder="프로젝트 설명을 입력하세요"
            />
          </div>

          {/* 태그 관리 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              태그 ({formData.tags.length}/10)
            </label>

            {/* 현재 태그들 */}
            {formData.tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {formData.tags.map((tag, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
                  >
                    {tag}
                    <button
                      type="button"
                      onClick={() => removeTag(tag)}
                      className="ml-2 text-blue-600 hover:text-blue-800"
                    >
                      <XMarkIcon className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* 태그 입력 */}
            <div className="flex gap-2">
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={handleTagKeyPress}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="태그를 입력하고 Enter를 누르세요"
                maxLength={20}
                disabled={formData.tags.length >= 10}
              />
              <button
                type="button"
                onClick={addTag}
                disabled={!tagInput.trim() || formData.tags.length >= 10}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                추가
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              태그는 최대 10개까지 추가할 수 있습니다. 각 태그는 20자 이내로
              입력하세요.
            </p>
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={handleModalClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={!formData.name.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              저장
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProjectList;
