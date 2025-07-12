import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { FolderPlusIcon, ArrowLeftIcon } from "@heroicons/react/24/outline";
import { projectAPI, handleAPIError } from "../services/api";

const CreateProject = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    tags: [],
    aiRole: "",
    aiInstructions: "",
    targetAudience: "일반독자",
    outputFormat: "multiple",
    styleGuidelines: "",
  });
  const [loading, setLoading] = useState(false);
  const [tagInput, setTagInput] = useState("");

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleAddTag = (e) => {
    if (e.key === "Enter" && tagInput.trim()) {
      e.preventDefault();
      if (!formData.tags.includes(tagInput.trim())) {
        setFormData((prev) => ({
          ...prev,
          tags: [...prev.tags, tagInput.trim()],
        }));
      }
      setTagInput("");
    }
  };

  const handleRemoveTag = (tagToRemove) => {
    setFormData((prev) => ({
      ...prev,
      tags: prev.tags.filter((tag) => tag !== tagToRemove),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      toast.error("프로젝트 이름을 입력해주세요");
      return;
    }

    try {
      setLoading(true);
      const newProject = await projectAPI.createProject(formData);

      toast.success("프로젝트가 생성되었습니다!");
      navigate(`/projects/${newProject.projectId}`);
    } catch (err) {
      const errorInfo = handleAPIError(err);
      toast.error(errorInfo.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* 헤더 */}
      <div className="mb-8">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-5 w-5 mr-2" />
          뒤로 가기
        </button>

        <div className="flex items-center space-x-3">
          <FolderPlusIcon className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              새 프로젝트 생성
            </h1>
            <p className="text-gray-600 mt-1">
              TITLE-NOMICS 제목 생성 프로젝트를 새로 만들어보세요
            </p>
          </div>
        </div>
      </div>

      {/* 프로젝트 생성 폼 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* 프로젝트 이름 */}
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
                onChange={handleInputChange}
                placeholder="예: 경제섹션 제목 최적화"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>

            {/* 프로젝트 설명 */}
            <div>
              <label
                htmlFor="description"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                프로젝트 설명
              </label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                placeholder="이 프로젝트의 목적과 사용 방법을 설명해주세요"
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* 태그 */}
            <div>
              <label
                htmlFor="tags"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                태그
              </label>
              <input
                type="text"
                id="tags"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={handleAddTag}
                placeholder="태그를 입력하고 Enter를 누르세요"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />

              {/* 태그 목록 */}
              {formData.tags.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {formData.tags.map((tag, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800"
                    >
                      {tag}
                      <button
                        type="button"
                        onClick={() => handleRemoveTag(tag)}
                        className="ml-2 text-blue-600 hover:text-blue-800"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* AI 어시스턴트 커스터마이징 섹션 */}
            <div className="border-t border-gray-200 pt-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                AI 어시스턴트 커스터마이징
              </h3>
              <p className="text-sm text-gray-600 mb-6">
                프로젝트별로 AI의 역할, 작업 방식, 출력 형식을 세부적으로 조정할 수 있습니다.
              </p>

              {/* AI 역할 */}
              <div className="mb-6">
                <label
                  htmlFor="aiRole"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  AI 역할 정의
                </label>
                <textarea
                  id="aiRole"
                  name="aiRole"
                  value={formData.aiRole}
                  onChange={handleInputChange}
                  placeholder="예: 당신은 서울경제신문의 경험 많은 편집자입니다. 경제 전문 지식과 독자 친화적인 제목 작성 능력을 가지고 있습니다."
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* AI 작업 지시사항 */}
              <div className="mb-6">
                <label
                  htmlFor="aiInstructions"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  작업 지시사항
                </label>
                <textarea
                  id="aiInstructions"
                  name="aiInstructions"
                  value={formData.aiInstructions}
                  onChange={handleInputChange}
                  placeholder="예: 기사의 핵심 내용을 파악하고, 독자의 관심을 끌 수 있는 제목을 생성하세요. 클릭베이트는 피하되, 호기심을 자극하는 요소는 포함하세요."
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* 대상 독자층 */}
              <div className="mb-6">
                <label
                  htmlFor="targetAudience"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  대상 독자층
                </label>
                <select
                  id="targetAudience"
                  name="targetAudience"
                  value={formData.targetAudience}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="일반독자">일반독자</option>
                  <option value="경제전문가">경제전문가</option>
                  <option value="투자자">투자자</option>
                  <option value="기업인">기업인</option>
                  <option value="정책입안자">정책입안자</option>
                  <option value="젊은층">젊은층 (2030)</option>
                  <option value="중장년층">중장년층 (4050)</option>
                </select>
              </div>

              {/* 출력 형식 */}
              <div className="mb-6">
                <label
                  htmlFor="outputFormat"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  출력 형식
                </label>
                <select
                  id="outputFormat"
                  name="outputFormat"
                  value={formData.outputFormat}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="multiple">다양한 스타일의 제목 5개</option>
                  <option value="ranking">우선순위별 제목 3개</option>
                  <option value="single">최적화된 제목 1개</option>
                  <option value="analysis">제목 + 선택 이유 분석</option>
                </select>
              </div>

              {/* 스타일 가이드라인 */}
              <div className="mb-6">
                <label
                  htmlFor="styleGuidelines"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  스타일 가이드라인
                </label>
                <textarea
                  id="styleGuidelines"
                  name="styleGuidelines"
                  value={formData.styleGuidelines}
                  onChange={handleInputChange}
                  placeholder="예: 제목 길이는 20-30자로 제한, 숫자와 구체적 수치 활용, 감정적 표현보다는 팩트 중심, 전문용어 사용 시 쉬운 설명 병기"
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            {/* 프로젝트 생성 안내 */}
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
              <h3 className="text-sm font-medium text-blue-900 mb-2">
                새로운 프로젝트 생성 방식 안내
              </h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• AI 커스터마이징 설정이 저장되어 프로젝트별 맞춤 제목 생성</li>
                <li>• 공용 Bedrock Agent가 프로젝트 설정에 따라 동적으로 작동</li>
                <li>• 기존 프롬프트 업로드 방식도 여전히 지원됩니다</li>
                <li>• 생성 후 기사를 입력하여 즉시 맞춤형 제목 생성 가능</li>
              </ul>
            </div>

            {/* 버튼 */}
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                취소
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center">
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    생성 중...
                  </span>
                ) : (
                  "프로젝트 생성"
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
