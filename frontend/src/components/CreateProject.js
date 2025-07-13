import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import {
  PlusIcon,
  FolderIcon,
  XMarkIcon,
  ChevronDownIcon,
  CheckIcon,
} from "@heroicons/react/24/outline";
import { projectAPI, handleAPIError, categoryAPI } from "../services/api";

const CreateProject = ({ isOpen, onClose, onSuccess }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [categoryDropdownOpen, setCategoryDropdownOpen] = useState(false);
  const [userCategories, setUserCategories] = useState([]);
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const categoryDropdownRef = useRef(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    category: "", // 빈 문자열로 초기화
  });

  // 사용자 카테고리 로드
  const loadUserCategories = async () => {
    try {
      setCategoriesLoading(true);
      const data = await categoryAPI.getUserCategories();
      const categories = data.categories || [];
      setUserCategories(categories);

      // 카테고리가 있으면 첫 번째 카테고리를 기본값으로 설정
      if (categories.length > 0 && !formData.category) {
        setFormData((prev) => ({
          ...prev,
          category: categories[0].id,
        }));
      }
    } catch (error) {
      console.error("카테고리 로드 실패:", error);
      toast.error(
        "카테고리를 불러오는데 실패했습니다. 먼저 카테고리를 생성해주세요."
      );
      setUserCategories([]);
    } finally {
      setCategoriesLoading(false);
    }
  };

  // 모달이 열릴 때 카테고리 로드
  useEffect(() => {
    if (isOpen) {
      loadUserCategories();
    }
  }, [isOpen]);

  // 현재 선택된 카테고리 정보
  const currentCategory = userCategories.find(
    (option) => option.id === formData.category
  );

  // 드롭다운 외부 클릭 감지
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        categoryDropdownRef.current &&
        !categoryDropdownRef.current.contains(event.target)
      ) {
        setCategoryDropdownOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      toast.error("프로젝트 이름을 입력해주세요.");
      return;
    }

    if (!formData.category) {
      toast.error("카테고리를 선택해주세요.");
      return;
    }

    try {
      setLoading(true);
      const result = await projectAPI.createProject(formData);
      toast.success("프로젝트가 생성되었습니다!");

      // 폼 초기화
      setFormData({
        name: "",
        description: "",
        category: userCategories[0]?.id || "",
      });

      // 성공 콜백 호출
      if (onSuccess) {
        onSuccess();
      }

      // 모달 닫기
      onClose();

      // 프로젝트 페이지로 이동
      navigate(`/projects/${result.projectId}`);
    } catch (error) {
      const errorInfo = handleAPIError(error);
      toast.error(`프로젝트 생성 실패: ${errorInfo.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleCategorySelect = (categoryId) => {
    setFormData((prev) => ({
      ...prev,
      category: categoryId,
    }));
    setCategoryDropdownOpen(false);
  };

  const handleClose = () => {
    // 폼 초기화
    setFormData({
      name: "",
      description: "",
      category: userCategories[0]?.id || "",
    });
    setCategoryDropdownOpen(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* 모달 헤더 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <FolderIcon className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                새 프로젝트 생성
              </h2>
              <p className="text-sm text-gray-600">
                AI 제목 생성을 위한 새 프로젝트를 만들어보세요
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {/* 폼 */}
        <div className="p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label
                htmlFor="name"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                프로젝트 이름 *
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="예: 서울경제신문 기사 제목"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
            </div>

            <div>
              <label
                htmlFor="description"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                설명 (선택사항)
              </label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                placeholder="프로젝트에 대한 간단한 설명을 입력해주세요"
                rows={4}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                카테고리 *
              </label>
              {userCategories.length === 0 && !categoriesLoading ? (
                <div className="text-center py-8 border-2 border-dashed border-gray-300 rounded-lg">
                  <p className="text-gray-500 mb-4">
                    사용할 수 있는 카테고리가 없습니다.
                  </p>
                  <p className="text-sm text-gray-400">
                    프로젝트 목록에서 카테고리를 먼저 생성해주세요.
                  </p>
                </div>
              ) : (
                <div className="relative" ref={categoryDropdownRef}>
                  <button
                    type="button"
                    onClick={() =>
                      setCategoryDropdownOpen(!categoryDropdownOpen)
                    }
                    className="w-full flex items-center justify-between px-4 py-3 bg-white border border-gray-300 rounded-lg hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200"
                    disabled={
                      loading ||
                      categoriesLoading ||
                      userCategories.length === 0
                    }
                  >
                    <div className="flex items-center space-x-2">
                      {currentCategory && (
                        <div
                          className={`w-3 h-3 rounded-full bg-${currentCategory.color}-500`}
                        ></div>
                      )}
                      <span className="text-gray-700 font-medium">
                        {categoriesLoading
                          ? "로딩 중..."
                          : currentCategory?.name || "카테고리 선택"}
                      </span>
                    </div>
                    <ChevronDownIcon
                      className={`h-4 w-4 text-gray-400 transition-transform duration-200 ${
                        categoryDropdownOpen ? "rotate-180" : ""
                      }`}
                    />
                  </button>

                  {/* 드롭다운 메뉴 */}
                  {categoryDropdownOpen && !categoriesLoading && (
                    <div className="absolute top-full left-0 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg z-50 overflow-hidden">
                      {userCategories.map((category) => (
                        <button
                          key={category.id}
                          type="button"
                          onClick={() => handleCategorySelect(category.id)}
                          className={`w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors duration-150 ${
                            formData.category === category.id
                              ? "bg-blue-50 text-blue-600"
                              : "text-gray-700"
                          }`}
                        >
                          <div className="flex items-center space-x-3">
                            <div
                              className={`w-3 h-3 rounded-full bg-${category.color}-500`}
                            ></div>
                            <span className="font-medium">{category.name}</span>
                          </div>
                          {formData.category === category.id && (
                            <CheckIcon className="h-4 w-4 text-blue-600" />
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end space-x-4 pt-6 border-t border-gray-200">
              <button
                type="button"
                onClick={handleClose}
                className="px-6 py-3 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                disabled={loading}
              >
                취소
              </button>
              <button
                type="submit"
                disabled={
                  loading ||
                  !formData.name.trim() ||
                  !formData.category ||
                  categoriesLoading
                }
                className="flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    생성 중...
                  </>
                ) : (
                  <>
                    <PlusIcon className="h-5 w-5 mr-2" />
                    프로젝트 생성
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CreateProject;
