import React, { useState, useEffect, memo } from "react";
import {
  StarIcon,
  CheckCircleIcon,
  ClipboardDocumentIcon,
} from "@heroicons/react/24/outline";
import { toast } from "react-hot-toast";

const ResultDisplay = ({ result, projectName }) => {
  const [copiedTitle, setCopiedTitle] = useState(null);
  const [visibleSections, setVisibleSections] = useState({});
  const [typingEffect, setTypingEffect] = useState({});

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

  // 애니메이션 효과를 위한 useEffect
  useEffect(() => {
    const sections = ['recommendation', 'categories'];
    
    sections.forEach((section, index) => {
      setTimeout(() => {
        setVisibleSections(prev => ({ ...prev, [section]: true }));
      }, index * 300);
    });
  }, []);

  // 타이핑 효과 훅
  const useTypingEffect = (text, speed = 50) => {
    const [displayText, setDisplayText] = useState('');
    const [isComplete, setIsComplete] = useState(false);

    useEffect(() => {
      setDisplayText('');
      setIsComplete(false);
      
      if (!text) return;

      let i = 0;
      const timer = setInterval(() => {
        if (i < text.length) {
          setDisplayText(prev => prev + text.charAt(i));
          i++;
        } else {
          setIsComplete(true);
          clearInterval(timer);
        }
      }, speed);

      return () => clearInterval(timer);
    }, [text, speed]);

    return { displayText, isComplete };
  };

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


  // 최종 추천 제목의 타이핑 효과
  const finalTitle = parsedResult.final_recommendation?.title || '';
  const { displayText: typedTitle, isComplete: titleComplete } = useTypingEffect(
    visibleSections.recommendation ? finalTitle : '', 
    30
  );

  return (
    <div className="space-y-6">

      {/* 최종 추천 제목 */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <StarIcon className="h-5 w-5 mr-2 text-yellow-500" />
            추천 제목
          </h3>
          <span className="text-sm text-gray-500">
            {new Date(result.timestamp).toLocaleString("ko-KR", {
              timeZone: "Asia/Seoul",
              year: "numeric",
              month: "2-digit", 
              day: "2-digit",
              hour: "2-digit",
              minute: "2-digit"
            })}
          </span>
        </div>

        {parsedResult.final_recommendation && (
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xl font-medium text-gray-900 flex-1 mr-4">
                {visibleSections.recommendation ? typedTitle : ""}
                {visibleSections.recommendation && !titleComplete && (
                  <span className="animate-pulse text-gray-400">|</span>
                )}
              </h4>
              {titleComplete && (
                <button
                  onClick={() =>
                    copyToClipboard(
                      parsedResult.final_recommendation.title,
                      "final"
                    )
                  }
                  className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  {copiedTitle === "final" ? (
                    <CheckCircleIcon className="h-5 w-5 text-green-600" />
                  ) : (
                    <ClipboardDocumentIcon className="h-5 w-5" />
                  )}
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 다른 제목 옵션 */}
      {parsedResult.titles && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            다른 제목 옵션
          </h3>
          
          <div className="space-y-3">
            {Object.entries(parsedResult.titles).map(([category, titles]) => 
              titles.map((titleObj, index) => (
                <div
                  key={`${category}-${index}`}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <span className="text-gray-900 flex-1">
                    {titleObj.title || "제목 없음"}
                  </span>
                  <button
                    onClick={() =>
                      copyToClipboard(
                        titleObj.title,
                        `${category}-${index}`
                      )
                    }
                    className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-lg transition-colors ml-3"
                  >
                    {copiedTitle === `${category}-${index}` ? (
                      <CheckCircleIcon className="h-4 w-4 text-green-600" />
                    ) : (
                      <ClipboardDocumentIcon className="h-4 w-4" />
                    )}
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default memo(ResultDisplay);
