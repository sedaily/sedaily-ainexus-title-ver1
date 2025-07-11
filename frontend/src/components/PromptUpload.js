import React, { useState } from "react";
import { useDropzone } from "react-dropzone";
import {
  CloudArrowUpIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";

const PromptUpload = ({ categories, promptStatus, onUpload }) => {
  const [uploadingCategory, setUploadingCategory] = useState(null);

  const handleFileUpload = async (categoryId, files) => {
    if (files.length === 0) return;

    const file = files[0];
    if (!file.name.endsWith(".txt")) {
      alert("txt 파일만 업로드 가능합니다.");
      return;
    }

    try {
      setUploadingCategory(categoryId);
      await onUpload(categoryId, file);
    } catch (error) {
      console.error("Upload failed:", error);
    } finally {
      setUploadingCategory(null);
    }
  };

  const getStatusIcon = (categoryId) => {
    const status = promptStatus[categoryId];
    if (!status) return null;

    if (status.indexed) {
      return <CheckCircleIcon className="h-5 w-5 text-green-600" />;
    } else if (status.uploaded) {
      return <ClockIcon className="h-5 w-5 text-yellow-600 animate-spin" />;
    } else {
      return <DocumentTextIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusText = (categoryId) => {
    const status = promptStatus[categoryId];
    if (!status) return "업로드 대기";

    if (status.indexed) {
      return "색인 완료";
    } else if (status.uploaded) {
      return "색인 중...";
    } else {
      return "업로드 대기";
    }
  };

  const getRequiredCategories = () => categories.filter((cat) => cat.required);
  const getOptionalCategories = () => categories.filter((cat) => !cat.required);

  return (
    <div className="space-y-8">
      {/* 프롬프트 업로드 안내 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">
          프롬프트 파일 업로드 안내
        </h3>
        <div className="space-y-2 text-sm text-blue-800">
          <p>• 각 카테고리별로 txt 파일을 업로드하세요</p>
          <p>• 파일 업로드 후 자동으로 임베딩 생성 및 색인이 진행됩니다</p>
          <p>• 필수 프롬프트를 모두 업로드해야 제목 생성이 가능합니다</p>
          <p>
            • 기존 프롬프트 파일들을 활용하여 각 카테고리에 맞게 업로드하세요
          </p>
        </div>
      </div>

      {/* 필수 프롬프트 카테고리 */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-500 mr-2" />
          필수 프롬프트 카테고리
        </h3>
        <div className="grid gap-4 md:grid-cols-2">
          {getRequiredCategories().map((category) => (
            <PromptUploadCard
              key={category.id}
              category={category}
              status={promptStatus[category.id]}
              isUploading={uploadingCategory === category.id}
              onUpload={(files) => handleFileUpload(category.id, files)}
              getStatusIcon={() => getStatusIcon(category.id)}
              getStatusText={() => getStatusText(category.id)}
            />
          ))}
        </div>
      </div>

      {/* 선택 프롬프트 카테고리 */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <DocumentTextIcon className="h-5 w-5 text-gray-500 mr-2" />
          선택 프롬프트 카테고리
        </h3>
        <div className="grid gap-4 md:grid-cols-2">
          {getOptionalCategories().map((category) => (
            <PromptUploadCard
              key={category.id}
              category={category}
              status={promptStatus[category.id]}
              isUploading={uploadingCategory === category.id}
              onUpload={(files) => handleFileUpload(category.id, files)}
              getStatusIcon={() => getStatusIcon(category.id)}
              getStatusText={() => getStatusText(category.id)}
            />
          ))}
        </div>
      </div>

      {/* 업로드 진행 상황 */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          업로드 진행 상황
        </h3>
        <div className="space-y-3">
          {categories.map((category) => {
            const status = promptStatus[category.id];
            const isComplete = status?.indexed;

            return (
              <div
                key={category.id}
                className="flex items-center justify-between"
              >
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    {getStatusIcon(category.id)}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {category.name}
                      {category.required && (
                        <span className="text-red-500 ml-1">*</span>
                      )}
                    </p>
                    <p className="text-sm text-gray-500">
                      {status?.fileName || "파일 없음"}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <span
                    className={`text-sm font-medium ${
                      isComplete ? "text-green-600" : "text-gray-500"
                    }`}
                  >
                    {getStatusText(category.id)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

const PromptUploadCard = ({
  category,
  status,
  isUploading,
  onUpload,
  getStatusIcon,
  getStatusText,
}) => {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: onUpload,
    accept: {
      "text/plain": [".txt"],
    },
    maxFiles: 1,
    disabled: isUploading,
  });

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-6 transition-colors ${
        isDragActive
          ? "border-blue-400 bg-blue-50"
          : status?.indexed
          ? "border-green-300 bg-green-50"
          : "border-gray-300 hover:border-gray-400"
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-gray-900 mb-1">
            {category.name}
            {category.required && <span className="text-red-500 ml-1">*</span>}
          </h4>
          <p className="text-xs text-gray-600">{category.description}</p>
        </div>
        <div className="flex-shrink-0 ml-3">{getStatusIcon()}</div>
      </div>

      <div {...getRootProps()} className="cursor-pointer">
        <input {...getInputProps()} />

        {isUploading ? (
          <div className="text-center py-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="text-sm text-gray-600 mt-2">업로드 중...</p>
          </div>
        ) : (
          <div className="text-center py-4">
            <CloudArrowUpIcon className="mx-auto h-8 w-8 text-gray-400" />
            <p className="text-sm text-gray-600 mt-2">
              {isDragActive
                ? "파일을 여기에 드롭하세요"
                : "txt 파일을 드래그하거나 클릭하여 업로드"}
            </p>
          </div>
        )}
      </div>

      {status?.fileName && (
        <div className="mt-3 p-2 bg-gray-100 rounded text-sm">
          <p className="font-medium text-gray-900">{status.fileName}</p>
          <p className="text-gray-600">{getStatusText()}</p>
        </div>
      )}
    </div>
  );
};

export default PromptUpload;
