import React, { useState } from "react";
import {
  StarIcon,
  CheckCircleIcon,
  ClipboardDocumentIcon,
  ChartBarIcon,
  EyeIcon,
  TrophyIcon,
} from "@heroicons/react/24/outline";
import { toast } from "react-hot-toast";

const ResultDisplay = ({ result, projectName }) => {
  const [copiedTitle, setCopiedTitle] = useState(null);

  // JSON 파싱 처리
  const parseResult = () => {
    try {
      if (typeof result.result === "string") {
        return JSON.parse(result.result);
      }
      return result.result;
    } catch (error) {
      console.error("JSON parsing error:", error);
      return {
        analysis: {},
        titles: {},
        final_recommendation: {},
      };
    }
  };

  const parsedResult = parseResult();

  const copyToClipboard = (text, titleType) => {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        setCopiedTitle(titleType);
        toast.success("제목이 클립보드에 복사되었습니다!");
        setTimeout(() => setCopiedTitle(null), 2000);
      })
      .catch((err) => {
        console.error("복사 실패:", err);
        toast.error("복사에 실패했습니다.");
      });
  };

  const getScoreColor = (score) => {
    if (score >= 85) return "text-green-600";
    if (score >= 70) return "text-yellow-600";
    return "text-red-600";
  };

  const getScoreBackground = (score) => {
    if (score >= 85) return "bg-green-100";
    if (score >= 70) return "bg-yellow-100";
    return "bg-red-100";
  };

  return (
    <div className="space-y-8">
      {/* 결과 헤더 */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 flex items-center">
              <TrophyIcon className="h-8 w-8 text-yellow-500 mr-3" />
              제목 생성 결과
            </h2>
            <p className="text-gray-600 mt-1">
              {projectName} 프로젝트 •{" "}
              {new Date(result.timestamp).toLocaleString("ko-KR")}
            </p>
          </div>

          <div className="text-right">
            <p className="text-sm text-gray-500">생성 시간</p>
            <p className="text-lg font-semibold text-gray-900">
              {result.usage?.execution_time
                ? `${result.usage.execution_time.toFixed(1)}초`
                : "정보 없음"}
            </p>
          </div>
        </div>
      </div>

      {/* 기사 분석 결과 */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <ChartBarIcon className="h-5 w-5 mr-2" />
            기사 분석 결과
          </h3>

          {parsedResult.analysis && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-gray-700">핵심 주제</p>
                  <p className="text-base text-gray-900">
                    {parsedResult.analysis.main_topic || "정보 없음"}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-700">대상 독자</p>
                  <p className="text-base text-gray-900">
                    {parsedResult.analysis.target_audience || "정보 없음"}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-700">톤앤매너</p>
                  <p className="text-base text-gray-900">
                    {parsedResult.analysis.tone || "정보 없음"}
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-gray-700">긴급성</p>
                  <p className="text-base text-gray-900">
                    {parsedResult.analysis.urgency || "정보 없음"}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-700">
                    핵심 키워드
                  </p>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {parsedResult.analysis.key_keywords?.map(
                      (keyword, index) => (
                        <span
                          key={index}
                          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                        >
                          {keyword}
                        </span>
                      )
                    ) || <span className="text-gray-500">정보 없음</span>}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 최종 추천 제목 */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg shadow-sm">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-4 flex items-center">
            <StarIcon className="h-5 w-5 mr-2 text-yellow-500" />
            최종 추천 제목
          </h3>

          {parsedResult.final_recommendation && (
            <div className="space-y-4">
              <div className="bg-white rounded-lg p-4 border border-blue-200">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xl font-bold text-gray-900">
                    {parsedResult.final_recommendation.title || "제목 없음"}
                  </h4>
                  <button
                    onClick={() =>
                      copyToClipboard(
                        parsedResult.final_recommendation.title,
                        "final"
                      )
                    }
                    className="p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-full"
                  >
                    {copiedTitle === "final" ? (
                      <CheckCircleIcon className="h-5 w-5 text-green-600" />
                    ) : (
                      <ClipboardDocumentIcon className="h-5 w-5" />
                    )}
                  </button>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center space-x-4">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                      {parsedResult.final_recommendation.type || "유형 없음"}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700">
                    <strong>선정 이유:</strong>{" "}
                    {parsedResult.final_recommendation.reason || "정보 없음"}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 카테고리별 제목 */}
      <div className="space-y-6">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center">
          <EyeIcon className="h-5 w-5 mr-2" />
          카테고리별 제목
        </h3>

        {parsedResult.titles &&
          Object.entries(parsedResult.titles).map(([category, titles]) => (
            <div
              key={category}
              className="bg-white border border-gray-200 rounded-lg shadow-sm"
            >
              <div className="p-6">
                <h4 className="text-md font-semibold text-gray-900 mb-4 capitalize">
                  {category === "straight"
                    ? "직설적 제목"
                    : category === "question"
                    ? "질문형 제목"
                    : category === "impact"
                    ? "임팩트 제목"
                    : category}{" "}
                  제목
                </h4>

                <div className="space-y-3">
                  {titles.map((titleObj, index) => (
                    <div
                      key={index}
                      className="border border-gray-200 rounded-lg p-4"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h5 className="text-base font-medium text-gray-900">
                          {titleObj.title || "제목 없음"}
                        </h5>
                        <button
                          onClick={() =>
                            copyToClipboard(
                              titleObj.title,
                              `${category}-${index}`
                            )
                          }
                          className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded-full"
                        >
                          {copiedTitle === `${category}-${index}` ? (
                            <CheckCircleIcon className="h-4 w-4 text-green-600" />
                          ) : (
                            <ClipboardDocumentIcon className="h-4 w-4" />
                          )}
                        </button>
                      </div>

                      {titleObj.evaluation && (
                        <div className="flex space-x-4 text-sm">
                          {Object.entries(titleObj.evaluation).map(
                            ([metric, score]) => (
                              <div
                                key={metric}
                                className="flex items-center space-x-2"
                              >
                                <span className="text-gray-600 capitalize">
                                  {metric}:
                                </span>
                                <span
                                  className={`px-2 py-1 rounded-full text-xs font-medium ${getScoreBackground(
                                    score
                                  )} ${getScoreColor(score)}`}
                                >
                                  {score}점
                                </span>
                              </div>
                            )
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
      </div>

      {/* 사용 통계 */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">사용 통계</h3>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-600">
              {result.usage?.input_tokens?.toLocaleString() || "정보 없음"}
            </p>
            <p className="text-sm text-gray-600">입력 토큰</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-600">
              {result.usage?.output_tokens?.toLocaleString() || "정보 없음"}
            </p>
            <p className="text-sm text-gray-600">출력 토큰</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-600">
              {result.usage?.execution_time
                ? `${result.usage.execution_time.toFixed(1)}초`
                : "정보 없음"}
            </p>
            <p className="text-sm text-gray-600">실행 시간</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResultDisplay;
