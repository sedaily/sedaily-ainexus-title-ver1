import { useState, useCallback } from "react";
import { toast } from "react-hot-toast";
import { generateAPI } from "../services/api";

/**
 * 제목 생성 실행 및 결과 폴링을 위한 커스텀 훅
 * @param {string} projectId - 프로젝트 ID
 * @returns {Object} - 제목 생성 관련 상태와 함수들
 */
export const useOrchestration = (projectId) => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentExecution, setCurrentExecution] = useState(null);
  const [executionStatus, setExecutionStatus] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);

  /**
   * 제목 생성 실행
   * @param {string} userInput - 사용자 입력
   * @param {Object} options - 추가 옵션 (예: chat_history, useStreaming)
   * @returns {Promise<Object>} - 생성 결과
   */
  const executeOrchestration = useCallback(
    async (userInput, options = {}) => {
      if (!userInput.trim()) {
        toast.error("메시지를 입력해주세요.");
        return null;
      }

      try {
        setIsExecuting(true);
        setExecutionStatus("STARTING");

        // chat_history와 userInput을 포함하는 data 객체 생성
        const data = {
          userInput: userInput,
          chat_history: options.chat_history || [],
        };

        console.log("🚀 대화 생성 요청 시작:", {
          projectId,
          inputLength: userInput.length,
          historyLength: data.chat_history.length,
          useStreaming: options.useStreaming === true,
          timestamp: new Date().toISOString(),
        });

        // 스트리밍 사용 여부 확인
        if (options.useStreaming === true) {
          setIsStreaming(true);

          // 스트리밍 콜백 함수 설정
          const onChunk = options.onChunk || (() => {});
          const onError = (error) => {
            setIsExecuting(false);
            setIsStreaming(false);
            setExecutionStatus("FAILED");
            if (options.onError) options.onError(error);
          };
          const onComplete = (response) => {
            setIsExecuting(false);
            setIsStreaming(false);
            setExecutionStatus("COMPLETED");
            if (options.onComplete) options.onComplete(response);
          };

          // 스트리밍 API 호출
          return await generateAPI.generateTitleStream(
            projectId,
            data,
            onChunk,
            onError,
            onComplete
          );
        }

        // 일반 API 호출 (스트리밍 미사용)
        const response = await generateAPI.generateTitle(projectId, data);

        console.log("✅ 대화 생성 완료:", {
          mode: response.mode,
          message: response.message,
          timestamp: new Date().toISOString(),
        });

        setIsExecuting(false);
        setExecutionStatus("COMPLETED");

        return response;
      } catch (error) {
        console.error("❌ 제목 생성 실패:", {
          error: error.message,
          code: error.code,
          status: error.response?.status,
          timestamp: new Date().toISOString(),
        });
        setIsExecuting(false);
        setIsStreaming(false);
        setExecutionStatus("FAILED");

        // 프롬프트 카드 관련 에러 처리
        if (
          error.response?.status === 400 &&
          error.response?.data?.setup_required
        ) {
          toast.error("프롬프트 카드를 먼저 설정해주세요!");
        } else if (error.code === "ECONNABORTED") {
          toast.error("요청 시간이 초과되었습니다. 다시 시도해주세요.");
        } else {
          toast.error("처리 중 오류가 발생했습니다.");
        }

        throw error;
      }
    },
    [projectId]
  );

  /**
   * 실행 상태 조회 (Step Functions 사용 시)
   * @param {string} executionArn - 실행 ARN
   * @param {Function} onComplete - 완료 시 콜백
   * @param {Function} onError - 에러 시 콜백
   */
  const pollOrchestrationResult = useCallback(
    async (executionArn, onComplete, onError) => {
      // 스트리밍 모드에서는 폴링이 필요 없음
      if (isStreaming) {
        return;
      }

      const poll = async () => {
        try {
          const result = await generateAPI.getExecutionStatus(executionArn);

          setExecutionStatus(result.status);

          if (result.status === "SUCCEEDED") {
            setIsExecuting(false);
            setExecutionStatus("COMPLETED");

            if (onComplete) {
              onComplete(result);
            }
          } else if (result.status === "FAILED") {
            setIsExecuting(false);
            setExecutionStatus("FAILED");

            if (onError) {
              onError(new Error("처리 실패"));
            }
          } else if (result.status === "RUNNING") {
            // 3초 후 다시 폴링
            setTimeout(poll, 3000);
          }
        } catch (error) {
          console.error("실행 상태 조회 실패:", error);
          setIsExecuting(false);
          setExecutionStatus("FAILED");

          if (onError) {
            onError(error);
          }
        }
      };

      poll();
    },
    [projectId, isStreaming]
  );

  /**
   * 오케스트레이션 상태 초기화
   */
  const resetOrchestration = useCallback(() => {
    setIsExecuting(false);
    setIsStreaming(false);
    setCurrentExecution(null);
    setExecutionStatus(null);
  }, []);

  return {
    isExecuting,
    isStreaming,
    currentExecution,
    executionStatus,
    executeOrchestration,
    pollOrchestrationResult,
    resetOrchestration,
  };
};
