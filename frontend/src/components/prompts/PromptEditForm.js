import React, { useState } from "react";
import { XMarkIcon, DocumentPlusIcon, CloudArrowUpIcon } from "@heroicons/react/24/outline";
import { AVAILABLE_MODELS } from "../../services/api";

const PromptEditForm = ({
  onSubmit,
  onCancel,
  initialData,
  isModal = false,
}) => {
  const [formData, setFormData] = useState({
    title: initialData?.title || "",
    category: initialData?.category || "instruction",
    model_name: initialData?.model_name || "claude-3-5-sonnet-20241022",
    temperature: initialData?.temperature || 0.7,
    prompt_text: initialData?.prompt_text || "",
    enabled: initialData?.enabled !== undefined ? initialData.enabled : true,
    step_order: initialData?.step_order || 1,
  });
  
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    await onSubmit(formData);
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };
  
  // 파일 업로드 핸들러들
  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };
  
  const handleDrop = (event) => {
    event.preventDefault();
    setDragOver(false);
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
      processFile(files[0]);
    }
  };
  
  const handleDragOver = (event) => {
    event.preventDefault();
    setDragOver(true);
  };
  
  const handleDragLeave = () => {
    setDragOver(false);
  };
  
  const processFile = (file) => {
    // 파일 크기 체크 (10MB)
    if (file.size > 10 * 1024 * 1024) {
      alert('파일 크기는 10MB 이하여야 합니다.');
      return;
    }
    
    // 파일 타입 체크
    const allowedTypes = ['text/plain', 'text/markdown'];
    const fileExtension = file.name.toLowerCase().split('.').pop();
    const allowedExtensions = ['txt', 'md'];
    
    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
      alert('TXT 또는 MD 파일만 업로드 가능합니다.');
      return;
    }
    
    // 파일 읽기
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result || '';
      handleChange('prompt_text', content);
      setUploadedFile(file);
    };
    reader.onerror = () => {
      alert('파일 읽기 중 오류가 발생했습니다.');
    };
    reader.readAsText(file);
  };
  
  const removeFile = () => {
    setUploadedFile(null);
    // 프롬프트 텍스트는 유지 (사용자가 편집했을 수 있음)
  };

  const categories = [
    { id: "instruction", name: "지시사항" },
    { id: "knowledge", name: "지식 베이스" },
    { id: "secondary", name: "보조 지침" },
    { id: "style_guide", name: "스타일 가이드" },
    { id: "validation", name: "검증 기준" },
    { id: "enhancement", name: "최적화" },
  ];

  const containerClass = isModal
    ? "p-6"
    : "bg-white rounded-lg border border-gray-200 p-6";

  return (
    <div className={containerClass}>
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          {initialData ? "프롬프트 카드 편집" : "새 프롬프트 카드"}
        </h3>
        {isModal && (
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">

        {/* 모델 및 설정 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              AI 모델
            </label>
            <select
              value={formData.model_name}
              onChange={(e) => handleChange("model_name", e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {AVAILABLE_MODELS.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              온도 (Temperature)
            </label>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-700">창의성 수준</span>
                <span className="text-lg font-bold text-blue-600 bg-white px-3 py-1 rounded-full border">
                  {formData.temperature.toFixed(1)}
                </span>
              </div>
              <div className="relative">
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.temperature}
                  onChange={(e) => handleChange("temperature", parseFloat(e.target.value))}
                  className="w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer slider-thumb"
                  style={{
                    background: `linear-gradient(to right, #60a5fa 0%, #3b82f6 ${(formData.temperature * 100)}%, #e5e7eb ${(formData.temperature * 100)}%, #e5e7eb 100%)`
                  }}
                />
                <div className="flex justify-between text-xs text-gray-500 mt-2">
                  <span className="flex items-center">
                    <span className="w-2 h-2 bg-blue-300 rounded-full mr-1"></span>
                    보수적 (0.0)
                  </span>
                  <span className="flex items-center">
                    <span className="w-2 h-2 bg-blue-600 rounded-full mr-1"></span>
                    창의적 (1.0)
                  </span>
                </div>
              </div>
              <p className="text-xs text-gray-600 mt-2 leading-relaxed">
                낮은 값은 일관성 있고 예측 가능한 결과를, 높은 값은 창의적이고 다양한 결과를 생성합니다.
              </p>
            </div>
          </div>
        </div>


        {/* 프롬프트 내용 - 파일 업로드 지원 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            프롬프트 내용
          </label>
          
          {/* 파일 업로드 영역 */}
          <div className="mb-3">
            <div 
              className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
                dragOver 
                  ? 'border-blue-400 bg-blue-50' 
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
            >
              <div className="flex flex-col items-center">
                <CloudArrowUpIcon className="h-8 w-8 text-gray-400 mb-2" />
                <div className="text-sm text-gray-600 mb-2">
                  <span className="font-medium text-blue-600 hover:text-blue-500">
                    파일을 선택하거나
                  </span>
                  {" "}드래그하여 업로드하세요
                </div>
                <p className="text-xs text-gray-500">TXT, MD 파일 지원 (최대 10MB)</p>
                
                <input
                  type="file"
                  accept=".txt,.md"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                />
                <label
                  htmlFor="file-upload"
                  className="mt-2 px-3 py-1 bg-white border border-gray-300 rounded-md text-xs font-medium text-gray-700 hover:bg-gray-50 cursor-pointer"
                >
                  파일 선택
                </label>
              </div>
            </div>
            
            {/* 업로드된 파일 표시 */}
            {uploadedFile && (
              <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded-md flex items-center justify-between">
                <div className="flex items-center">
                  <DocumentPlusIcon className="h-4 w-4 text-green-600 mr-2" />
                  <span className="text-sm text-green-700">
                    {uploadedFile.name} ({(uploadedFile.size / 1024).toFixed(1)}KB)
                  </span>
                </div>
                <button
                  type="button"
                  onClick={removeFile}
                  className="text-green-600 hover:text-green-800"
                >
                  <XMarkIcon className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
          
          <textarea
            value={formData.prompt_text}
            onChange={(e) => handleChange("prompt_text", e.target.value)}
            rows={8}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="프롬프트 내용을 직접 입력하거나 위에서 파일을 업로드하세요..."
            required
          />
          <p className="text-xs text-gray-500 mt-1">
            현재 길이: {formData.prompt_text.length}자
          </p>
        </div>

        {/* 활성화 상태 및 업로드 팁 */}
        <div className="space-y-3">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="enabled"
              checked={formData.enabled}
              onChange={(e) => handleChange("enabled", e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="enabled" className="ml-2 text-sm text-gray-700">
              활성화 상태
            </label>
          </div>
          
          {/* 사용 팁 */}
          <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
            <h4 className="text-sm font-medium text-blue-800 mb-1">💡 사용 팁</h4>
            <ul className="text-xs text-blue-700 space-y-1">
              <li>• 파일 업로드: 기존 프롬프트 문서를 빠르게 가져올 수 있습니다</li>
              <li>• 직접 입력: 세밀한 조정이 필요한 경우 텍스트를 직접 편집하세요</li>
              <li>• 단계 순서: 1-6 단계로 구성된 워크플로우를 따릅니다</li>
            </ul>
          </div>
        </div>

        {/* 버튼들 */}
        <div className="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            취소
          </button>
          <button
            type="submit"
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            {initialData ? "수정" : "생성"}
          </button>
        </div>
      </form>
    </div>
  );
};

export default PromptEditForm;
