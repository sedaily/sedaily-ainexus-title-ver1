import { useState, useCallback } from "react";
import { toast } from "react-hot-toast";
import { orchestrationAPI } from "../services/api";

/**
 * 오케스트레이션 실행 및 결과 폴링을 위한 커스텀 훅
 * @param {string} projectId - 프로젝트 ID
 * @returns {Object} - 오케스트레이션 관련 상태와 함수들
 */
export const useOrchestration = (projectId) => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentExecution, setCurrentExecution] = useState(null);
  const [executionStatus, setExecutionStatus] = useState(null);

  /**
   * 오케스트레이션 실행
   * @param {string} content - 입력 내용
   * @param {Object} config - 오케스트레이션 설정
   * @returns {Promise<string>} - 실행 ID
   */
  const executeOrchestration = useCallback(
    async (content, config = {}) => {
      if (!content.trim()) {
        toast.error("내용을 입력해주세요");
        return null;
      }

      try {
        setIsExecuting(true);
        setExecutionStatus("STARTING");

        const defaultConfig = {
          useAllSteps: true,
          enabledSteps: [],
          maxRetries: 3,
          temperature: 0.7,
          ...config,
        };

        const response = await orchestrationAPI.executeOrchestration(
          projectId,
          content,
          defaultConfig
        );

        setCurrentExecution(response.executionId);
        setExecutionStatus("RUNNING");

        return response.executionId;
      } catch (error) {
        console.error("오케스트레이션 실행 실패:", error);
        setIsExecuting(false);
        setExecutionStatus("FAILED");
        throw error;
      }
    },
    [projectId]
  );

  /**
   * 오케스트레이션 결과 폴링
   * @param {string} executionId - 실행 ID
   * @param {Function} onComplete - 완료 시 콜백
   * @param {Function} onError - 에러 시 콜백
   */
  const pollOrchestrationResult = useCallback(
    async (executionId, onComplete, onError) => {
      const poll = async () => {
        try {
          const status = await orchestrationAPI.getOrchestrationStatus(
            projectId,
            executionId
          );

          setExecutionStatus(status.status);

          if (status.status === "COMPLETED") {
            const result = await orchestrationAPI.getOrchestrationResult(
              projectId,
              executionId
            );

            setIsExecuting(false);
            setExecutionStatus("COMPLETED");

            if (onComplete) {
              onComplete(result);
            }
          } else if (status.status === "FAILED") {
            setIsExecuting(false);
            setExecutionStatus("FAILED");

            if (onError) {
              onError(new Error("오케스트레이션 실패"));
            }
          } else if (status.status === "RUNNING") {
            // 3초 후 다시 폴링
            setTimeout(poll, 3000);
          }
        } catch (error) {
          console.error("결과 조회 실패:", error);
          setIsExecuting(false);
          setExecutionStatus("FAILED");

          if (onError) {
            onError(error);
          }
        }
      };

      poll();
    },
    [projectId]
  );

  /**
   * 오케스트레이션 상태 초기화
   */
  const resetOrchestration = useCallback(() => {
    setIsExecuting(false);
    setCurrentExecution(null);
    setExecutionStatus(null);
  }, []);

  return {
    isExecuting,
    currentExecution,
    executionStatus,
    executeOrchestration,
    pollOrchestrationResult,
    resetOrchestration,
  };
};
