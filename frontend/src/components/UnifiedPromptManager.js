import React, { useState, useEffect } from "react";
import { toast } from "react-hot-toast";
import {
  DocumentTextIcon,
  PlusIcon,
  TrashIcon,
  PencilIcon,
  EyeIcon,
  EyeSlashIcon,
} from "@heroicons/react/24/outline";

const UnifiedPromptManager = ({ projectId, projectName }) => {
  const [document, setDocument] = useState({
    sections: [],
    content: "",
    version: 1,
  });
  const [metadata, setMetadata] = useState({
    created_at: "",
    updated_at: "",
    total_prompts: 0,
  });
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [newPromptTitle, setNewPromptTitle] = useState("");
  const [newPromptContent, setNewPromptContent] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);

  useEffect(() => {
    loadDocument();
  }, [projectId]);

  const loadDocument = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/unified-prompts/${projectId}`);
      const data = await response.json();

      if (response.ok) {
        setDocument(data.document);
        setMetadata(data.metadata);
      } else {
        toast.error(data.error || "문서 로드 실패");
      }
    } catch (error) {
      console.error("문서 로드 오류:", error);
      toast.error("문서를 불러올 수 없습니다");
    } finally {
      setLoading(false);
    }
  };

  const saveDocument = async () => {
    try {
      const response = await fetch(`/api/unified-prompts/${projectId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          content: document.content,
          sections: document.sections,
          version: document.version + 1,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        toast.success("문서가 저장되었습니다");
        setDocument((prev) => ({ ...prev, version: prev.version + 1 }));
        setEditing(false);
        loadDocument(); // 최신 상태로 새로고침
      } else {
        toast.error(data.error || "저장 실패");
      }
    } catch (error) {
      console.error("저장 오류:", error);
      toast.error("문서를 저장할 수 없습니다");
    }
  };

  const addNewPrompt = async () => {
    if (!newPromptTitle.trim() || !newPromptContent.trim()) {
      toast.error("제목과 내용을 모두 입력해주세요");
      return;
    }

    try {
      const response = await fetch(`/api/unified-prompts/${projectId}/prompt`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: newPromptTitle,
          content: newPromptContent,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        toast.success("프롬프트가 추가되었습니다");
        setNewPromptTitle("");
        setNewPromptContent("");
        setShowAddForm(false);
        loadDocument();
      } else {
        toast.error(data.error || "추가 실패");
      }
    } catch (error) {
      console.error("추가 오류:", error);
      toast.error("프롬프트를 추가할 수 없습니다");
    }
  };

  const removePrompt = async (promptId) => {
    if (!window.confirm("정말로 이 프롬프트를 삭제하시겠습니까?")) {
      return;
    }

    try {
      const response = await fetch(
        `/api/unified-prompts/${projectId}/prompt/${promptId}`,
        {
          method: "DELETE",
        }
      );

      const data = await response.json();

      if (response.ok) {
        toast.success("프롬프트가 삭제되었습니다");
        loadDocument();
      } else {
        toast.error(data.error || "삭제 실패");
      }
    } catch (error) {
      console.error("삭제 오류:", error);
      toast.error("프롬프트를 삭제할 수 없습니다");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white dark:bg-dark-secondary rounded-lg shadow-lg transition-colors duration-300">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <DocumentTextIcon className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {projectName}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              통합 프롬프트 문서 • {metadata.total_prompts}개 프롬프트
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowPreview(!showPreview)}
            className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
              showPreview
                ? "bg-gray-200 text-gray-800"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {showPreview ? (
              <EyeSlashIcon className="h-4 w-4" />
            ) : (
              <EyeIcon className="h-4 w-4" />
            )}
            {showPreview ? "편집" : "미리보기"}
          </button>

          <button
            onClick={() => setShowAddForm(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            <PlusIcon className="h-4 w-4 mr-1 inline" />
            프롬프트 추가
          </button>
        </div>
      </div>

      {/* 섹션 목록 */}
      {document.sections.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
            프롬프트 섹션
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {document.sections.map((section) => (
              <div
                key={section.id}
                className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 flex items-center justify-between transition-colors duration-200"
              >
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white">
                    {section.title}
                  </h4>
                  <p className="text-xs text-gray-500">
                    {new Date(section.created_at).toLocaleDateString("ko-KR")}
                  </p>
                </div>
                <button
                  onClick={() => removePrompt(section.id)}
                  className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                >
                  <TrashIcon className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 메인 에디터/미리보기 */}
      <div className="bg-gray-50 dark:bg-dark-tertiary rounded-lg transition-colors duration-200">
        <div className="bg-gray-50 dark:bg-dark-tertiary px-4 py-2 transition-colors duration-200">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-gray-900 dark:text-white">
              {showPreview ? "미리보기" : "편집 모드"}
            </h3>
            {!showPreview && (
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setEditing(!editing)}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  <PencilIcon className="h-4 w-4 mr-1 inline" />
                  {editing ? "편집 완료" : "편집"}
                </button>
                {editing && (
                  <button
                    onClick={saveDocument}
                    className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                  >
                    저장
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="p-4">
          {showPreview ? (
            <div className="prose max-w-none">
              <pre className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 font-mono">
                {document.content || "프롬프트 내용이 없습니다."}
              </pre>
            </div>
          ) : editing ? (
            <textarea
              value={document.content}
              onChange={(e) =>
                setDocument((prev) => ({ ...prev, content: e.target.value }))
              }
              className="w-full h-96 p-3 bg-white dark:bg-dark-primary text-gray-900 dark:text-white rounded-md font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors duration-200"
              placeholder="프롬프트 내용을 입력하세요..."
            />
          ) : (
            <div
              className="min-h-96 p-3 bg-gray-50 dark:bg-dark-primary rounded-md cursor-text transition-colors duration-200"
              onClick={() => setEditing(true)}
            >
              <pre className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 font-mono">
                {document.content || "클릭하여 프롬프트를 작성하세요..."}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* 메타데이터 */}
      <div className="mt-4 text-xs text-gray-500 dark:text-gray-400 flex items-center justify-between transition-colors duration-200">
        <span>버전 {document.version}</span>
        <span>
          마지막 수정:{" "}
          {metadata.updated_at
            ? new Date(metadata.updated_at).toLocaleString("ko-KR")
            : "없음"}
        </span>
      </div>

      {/* 프롬프트 추가 모달 */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-dark-secondary rounded-lg p-6 w-full max-w-md transition-colors duration-200">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              새 프롬프트 추가
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  제목
                </label>
                <input
                  type="text"
                  value={newPromptTitle}
                  onChange={(e) => setNewPromptTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-white dark:bg-dark-tertiary text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors duration-200"
                  placeholder="프롬프트 제목을 입력하세요"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  내용
                </label>
                <textarea
                  value={newPromptContent}
                  onChange={(e) => setNewPromptContent(e.target.value)}
                  className="w-full px-3 py-2 bg-white dark:bg-dark-tertiary text-gray-900 dark:text-white rounded-md h-32 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors duration-200"
                  placeholder="프롬프트 내용을 입력하세요"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 mt-6">
              <button
                onClick={() => {
                  setShowAddForm(false);
                  setNewPromptTitle("");
                  setNewPromptContent("");
                }}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors duration-200"
              >
                취소
              </button>
              <button
                onClick={addNewPrompt}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors duration-200"
              >
                추가
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UnifiedPromptManager;
