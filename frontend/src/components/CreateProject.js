import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import {
  ArrowLeftIcon,
  PlusIcon,
  FolderIcon,
} from "@heroicons/react/24/outline";
import { projectAPI, handleAPIError } from "../services/api";

const CreateProject = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    category: "기본"
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error("프로젝트 이름을 입력해주세요.");
      return;
    }

    try {
      setLoading(true);
      const result = await projectAPI.createProject(formData);
      toast.success("프로젝트가 생성되었습니다!");
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
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 헤더 */}
        <div className="mb-8">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center text-gray-600 hover:text-gray-900 transition-colors mb-4"
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            <span>돌아가기</span>
          </button>
          
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-blue-100 rounded-lg">
              <FolderIcon className="h-8 w-8 text-blue-600" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">새 프로젝트 생성</h1>
              <p className="text-gray-600 mt-1">AI 제목 생성을 위한 새 프로젝트를 만들어보세요</p>
            </div>
          </div>
        </div>

        {/* 폼 */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
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
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
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
              <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-2">
                카테고리
              </label>
              <select
                id="category"
                name="category"
                value={formData.category}
                onChange={handleChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              >
                <option value="기본">기본</option>
                <option value="뉴스">뉴스</option>
                <option value="블로그">블로그</option>
                <option value="마케팅">마케팅</option>
              </select>
            </div>

            <div className="flex items-center justify-end space-x-4 pt-6 border-t border-gray-200">
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="px-6 py-3 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                disabled={loading}
              >
                취소
              </button>
              <button
                type="submit"
                disabled={loading || !formData.name.trim()}
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