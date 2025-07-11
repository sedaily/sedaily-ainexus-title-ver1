import React, { useState } from "react";
import {
  SparklesIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  Cog8ToothIcon,
} from "@heroicons/react/24/outline";

const ArticleInput = ({ canGenerate, isGenerating, onGenerate }) => {
  const [article, setArticle] = useState("");
  const [wordCount, setWordCount] = useState(0);
  const [executionStatus, setExecutionStatus] = useState(null);
  const [executionArn, setExecutionArn] = useState(null);

  const handleArticleChange = (e) => {
    const text = e.target.value;
    setArticle(text);
    setWordCount(
      text
        .trim()
        .split(/\s+/)
        .filter((word) => word.length > 0).length
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!article.trim()) {
      alert("기사 내용을 입력해주세요.");
      return;
    }
    if (article.length < 100) {
      alert("더 자세한 기사 내용을 입력해주세요. (최소 100자)");
      return;
    }

    // 진행 상황 콜백 함수
    const onProgress = (progress) => {
      setExecutionStatus(progress.status);
      setExecutionArn(progress.executionArn);
    };

    try {
      await onGenerate(article, onProgress);
      setExecutionStatus("completed");
    } catch (error) {
      setExecutionStatus("failed");
      console.error("제목 생성 실패:", error);
    }
  };

  const handleSampleLoad = () => {
    const sampleArticle = `
[경제] 국내 대형 테크 기업들의 AI 투자 경쟁이 치열해지고 있다. 

네이버는 올해 AI 연구개발에 1조원 규모의 투자를 발표했으며, 초거대 AI 모델 '하이퍼클로바X'를 기반으로 한 다양한 서비스를 출시할 예정이라고 밝혔다. 

카카오도 AI 기술 개발에 8000억원을 투입하기로 했으며, 자체 개발한 AI 모델 '칸나'를 활용한 새로운 비즈니스 모델을 구축하고 있다.

삼성전자는 AI 반도체 부문에서 글로벌 경쟁력을 강화하기 위해 차세대 AI 칩 개발에 집중하고 있으며, 2025년까지 AI 전용 칩 시장에서 20% 이상의 점유율을 목표로 하고 있다.

업계 관계자는 "AI 기술이 미래 경쟁력을 좌우할 핵심 요소가 되면서, 각 기업들이 선제적 투자에 나서고 있다"며 "향후 2-3년이 AI 시장에서의 주도권을 결정짓는 중요한 시기가 될 것"이라고 전망했다.

한편, 정부도 AI 산업 육성을 위해 2027년까지 10조원 규모의 'K-AI 벨트' 프로젝트를 추진하기로 했으며, 이를 통해 국내 AI 생태계를 한층 더 활성화할 계획이다.
`.trim();

    setArticle(sampleArticle);
    setWordCount(
      sampleArticle
        .trim()
        .split(/\s+/)
        .filter((word) => word.length > 0).length
    );
  };

  const getStatusIcon = () => {
    if (!executionStatus) return null;

    switch (executionStatus) {
      case "started":
        return <Cog8ToothIcon className="h-5 w-5 text-blue-600 animate-spin" />;
      case "completed":
        return <CheckCircleIcon className="h-5 w-5 text-green-600" />;
      case "failed":
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />;
      default:
        return <ClockIcon className="h-5 w-5 text-yellow-600 animate-pulse" />;
    }
  };

  const getStatusMessage = () => {
    if (!executionStatus) return "";

    switch (executionStatus) {
      case "started":
        return "Step Functions 실행이 시작되었습니다...";
      case "completed":
        return "제목 생성이 완료되었습니다!";
      case "failed":
        return "제목 생성에 실패했습니다.";
      default:
        return "처리 중...";
    }
  };

  return (
    <div className="space-y-6">
      {/* 제목 생성 안내 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3 flex items-center">
          <InformationCircleIcon className="h-5 w-5 mr-2" />
          제목 생성 안내
        </h3>
        <div className="space-y-2 text-sm text-blue-800">
          <p>
            • 기사 원문을 입력하시면 TITLE-NOMICS 시스템이 Step Functions
            워크플로우를 통해 최적의 제목을 생성합니다
          </p>
          <p>
            • AI가 프롬프트 조회 → 가드레일 검증 → 모델 호출 → 결과 저장 과정을
            거쳐 제목을 생성합니다
          </p>
          <p>• 최소 100자 이상의 기사 내용을 입력해주세요</p>
          <p>• 더 자세한 기사 내용일수록 더 정확한 제목이 생성됩니다</p>
        </div>
      </div>

      {/* 제목 생성 가능 여부 표시 */}
      {!canGenerate && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center">
            <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 mr-2" />
            <p className="text-sm font-medium text-yellow-800">
              제목 생성을 위해서는 먼저 필수 프롬프트를 모두 업로드해야 합니다.
            </p>
          </div>
        </div>
      )}

      {/* 기사 입력 폼 */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
        <div className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <DocumentTextIcon className="h-5 w-5 mr-2" />
                기사 원문 입력
              </h3>
              <button
                type="button"
                onClick={handleSampleLoad}
                className="text-sm text-blue-600 hover:text-blue-800 underline"
              >
                샘플 기사 불러오기
              </button>
            </div>

            <textarea
              value={article}
              onChange={handleArticleChange}
              placeholder="기사 원문을 입력하세요. 제목, 본문, 핵심 내용을 모두 포함해주세요."
              className="w-full h-96 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              disabled={isGenerating}
            />

            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <span>글자 수: {article.length.toLocaleString()}</span>
                <span>단어 수: {wordCount.toLocaleString()}</span>
                <span
                  className={`${
                    article.length < 100 ? "text-red-600" : "text-green-600"
                  }`}
                >
                  {article.length < 100 ? "최소 100자 필요" : "충분한 길이"}
                </span>
              </div>

              <button
                type="submit"
                disabled={!canGenerate || isGenerating || article.length < 100}
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGenerating ? (
                  <>
                    <ClockIcon className="h-5 w-5 mr-2 animate-spin" />
                    제목 생성 중...
                  </>
                ) : (
                  <>
                    <SparklesIcon className="h-5 w-5 mr-2" />
                    제목 생성
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Step Functions 실행 상태 */}
      {executionStatus && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-center space-x-3 mb-4">
            {getStatusIcon()}
            <div>
              <h3 className="text-lg font-semibold text-blue-900">
                Step Functions 실행 상태
              </h3>
              <p className="text-sm text-blue-800">{getStatusMessage()}</p>
            </div>
          </div>

          {executionArn && (
            <div className="bg-white rounded-lg p-4 border border-blue-200">
              <p className="text-sm text-gray-600 mb-2">실행 ARN:</p>
              <p className="text-xs font-mono text-gray-800 bg-gray-100 p-2 rounded break-all">
                {executionArn}
              </p>
            </div>
          )}

          {isGenerating && (
            <div className="mt-4 space-y-2">
              <div className="text-sm text-blue-800">
                <div className="flex items-center space-x-2 mb-2">
                  <Cog8ToothIcon className="h-4 w-4 animate-spin" />
                  <span>워크플로우 진행 중...</span>
                </div>
                <div className="ml-6 space-y-1">
                  <p>1️⃣ 프롬프트 조회 중...</p>
                  <p>2️⃣ 입력 가드레일 검증 중...</p>
                  <p>3️⃣ AI 모델 호출 중...</p>
                  <p>4️⃣ 출력 가드레일 검증 중...</p>
                  <p>5️⃣ 결과 저장 중...</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 사용 팁 */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          더 나은 제목을 위한 팁
        </h3>
        <div className="space-y-2 text-sm text-gray-700">
          <p>
            • <strong>구체적인 정보:</strong> 수치, 날짜, 고유명사 등을
            포함하세요
          </p>
          <p>
            • <strong>핵심 메시지:</strong> 기사의 가장 중요한 내용을 명확히
            하세요
          </p>
          <p>
            • <strong>대상 독자:</strong> 누구를 위한 기사인지 명시하세요
          </p>
          <p>
            • <strong>긴급성/중요성:</strong> 시급성이나 중요도를 나타내는
            표현을 사용하세요
          </p>
          <p>
            • <strong>감정적 요소:</strong> 독자의 관심을 끌 수 있는 감정적
            포인트를 포함하세요
          </p>
        </div>
      </div>
    </div>
  );
};

export default ArticleInput;
