import axios from "axios";

// API 기본 URL (환경 변수 또는 기본값)
const API_BASE_URL =
  process.env.REACT_APP_API_URL ||
  "https://your-api-gateway-url.amazonaws.com/prod";

// Axios 인스턴스 생성
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// 요청 인터셉터
api.interceptors.request.use(
  (config) => {
    console.log("API 요청:", config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터
api.interceptors.response.use(
  (response) => {
    console.log("API 응답:", response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error(
      "API 오류:",
      error.response?.status,
      error.response?.data || error.message
    );
    return Promise.reject(error);
  }
);

// 프로젝트 관련 API
export const projectAPI = {
  // 프로젝트 목록 조회
  getProjects: async (params = {}) => {
    const response = await api.get("/projects", { params });
    return response.data;
  },

  // 프로젝트 생성
  createProject: async (projectData) => {
    const response = await api.post("/projects", projectData);
    return response.data;
  },

  // 프로젝트 상세 조회
  getProject: async (projectId) => {
    const response = await api.get(`/projects/${projectId}`);
    return response.data;
  },

  // 프로젝트 업데이트
  updateProject: async (projectId, projectData) => {
    const response = await api.put(`/projects/${projectId}`, projectData);
    return response.data;
  },

  // 프로젝트 삭제
  deleteProject: async (projectId) => {
    const response = await api.delete(`/projects/${projectId}`);
    return response.data;
  },

  // 업로드 URL 요청
  getUploadUrl: async (projectId, category, filename) => {
    const response = await api.get(`/presign-url`, {
      params: { projectId, category, filename },
    });
    return response.data;
  },
};

// 제목 생성 API (Step Functions 기반)
export const generateAPI = {
  // 제목 생성 시작 (Step Functions 실행)
  startTitleGeneration: async (projectId, article) => {
    const response = await api.post(`/projects/${projectId}/generate`, {
      article,
    });
    return response.data;
  },

  // 실행 상태 조회
  getExecutionStatus: async (executionArn) => {
    const encodedArn = encodeURIComponent(executionArn);
    const response = await api.get(`/executions/${encodedArn}`);
    return response.data;
  },

  // 폴링을 통한 결과 대기
  pollForResult: async (executionArn, maxRetries = 30, interval = 2000) => {
    let retries = 0;

    while (retries < maxRetries) {
      try {
        const status = await generateAPI.getExecutionStatus(executionArn);

        if (status.status === "SUCCEEDED") {
          return {
            success: true,
            data: status,
          };
        } else if (status.status === "FAILED") {
          return {
            success: false,
            error: status.error || "실행이 실패했습니다",
          };
        } else if (status.status === "TIMED_OUT") {
          return {
            success: false,
            error: "실행 시간이 초과되었습니다",
          };
        } else if (status.status === "ABORTED") {
          return {
            success: false,
            error: "실행이 중단되었습니다",
          };
        }

        // 아직 실행 중이면 대기
        await new Promise((resolve) => setTimeout(resolve, interval));
        retries++;
      } catch (error) {
        console.error("폴링 중 오류:", error);
        retries++;

        if (retries >= maxRetries) {
          return {
            success: false,
            error: "상태 조회 중 오류가 발생했습니다",
          };
        }

        await new Promise((resolve) => setTimeout(resolve, interval));
      }
    }

    return {
      success: false,
      error: "실행 시간이 초과되었습니다",
    };
  },

  // 제목 생성 (시작 + 폴링)
  generateTitle: async (projectId, article, onProgress) => {
    try {
      // Step Functions 실행 시작
      const startResponse = await generateAPI.startTitleGeneration(
        projectId,
        article
      );

      if (onProgress) {
        onProgress({
          status: "started",
          message: "제목 생성이 시작되었습니다...",
          executionArn: startResponse.executionArn,
        });
      }

      // 폴링을 통한 결과 대기
      const pollResponse = await generateAPI.pollForResult(
        startResponse.executionArn
      );

      if (pollResponse.success) {
        return {
          conversationId: pollResponse.data.conversationId,
          projectId: projectId,
          result: pollResponse.data.result,
          usage: pollResponse.data.usage,
          timestamp: pollResponse.data.completedAt || new Date().toISOString(),
          executionArn: startResponse.executionArn,
        };
      } else {
        throw new Error(pollResponse.error);
      }
    } catch (error) {
      console.error("제목 생성 실패:", error);
      throw error;
    }
  },
};

// 🆕 채팅 API (LangChain 기반)
export const chatAPI = {
  // 채팅 메시지 전송
  sendMessage: async (
    projectId,
    message,
    sessionId = null,
    userId = "default"
  ) => {
    const response = await api.post(`/projects/${projectId}/chat`, {
      message,
      sessionId,
      userId,
    });
    return response.data;
  },

  // 채팅 세션 목록 조회
  getChatSessions: async (projectId) => {
    const response = await api.get(`/projects/${projectId}/chat/sessions`);
    return response.data;
  },

  // 채팅 히스토리 조회
  getChatHistory: async (projectId, sessionId) => {
    const response = await api.get(
      `/projects/${projectId}/chat/sessions/${sessionId}`
    );
    return response.data;
  },

  // 채팅 세션 삭제
  deleteChatSession: async (projectId, sessionId) => {
    const response = await api.delete(
      `/projects/${projectId}/chat/sessions/${sessionId}`
    );
    return response.data;
  },

  // 스트리밍 채팅 (WebSocket 대체용)
  streamingChat: async (projectId, message, sessionId, onMessage) => {
    try {
      const response = await chatAPI.sendMessage(projectId, message, sessionId);

      // 실제 스트리밍이 아니므로 즉시 완전한 응답 반환
      if (onMessage) {
        onMessage({
          type: "message",
          content: response.message,
          sessionId: response.sessionId,
          metadata: response.metadata,
        });
      }

      return response;
    } catch (error) {
      if (onMessage) {
        onMessage({
          type: "error",
          error: error.message,
        });
      }
      throw error;
    }
  },
};

// 파일 업로드 API
export const uploadAPI = {
  // S3 Pre-signed URL로 파일 업로드
  uploadFile: async (uploadUrl, file) => {
    const response = await axios.put(uploadUrl, file, {
      headers: {
        "Content-Type": "text/plain",
      },
    });
    return response;
  },
};

// 프롬프트 카테고리 정의
export const PROMPT_CATEGORIES = [
  {
    id: "title_type_guidelines",
    name: "제목 유형 가이드라인",
    description: "제목의 다양한 유형과 작성 원칙",
    required: true,
  },
  {
    id: "stylebook_guidelines",
    name: "스타일북 가이드라인",
    description: "서울경제신문의 스타일북 규정",
    required: true,
  },
  {
    id: "workflow",
    name: "워크플로우",
    description: "제목 생성 6단계 워크플로우",
    required: true,
  },
  {
    id: "audience_optimization",
    name: "독자 최적화",
    description: "대상 독자층별 최적화 전략",
    required: true,
  },
  {
    id: "seo_optimization",
    name: "SEO 최적화",
    description: "검색 엔진 최적화 가이드라인",
    required: false,
  },
  {
    id: "digital_elements_guidelines",
    name: "디지털 요소 가이드라인",
    description: "온라인 매체 특성에 맞는 제목 작성법",
    required: true,
  },
  {
    id: "quality_assessment",
    name: "품질 평가",
    description: "제목 품질 평가 기준",
    required: true,
  },
  {
    id: "uncertainty_handling",
    name: "불확실성 처리",
    description: "불확실한 정보 처리 가이드라인",
    required: true,
  },
  {
    id: "output_format",
    name: "출력 형식",
    description: "결과 출력 형식 정의",
    required: true,
  },
  {
    id: "description",
    name: "프로젝트 설명",
    description: "TITLE-NOMICS 시스템 설명",
    required: true,
  },
  {
    id: "knowledge",
    name: "핵심 지식",
    description: "제목 작성 핵심 지식",
    required: true,
  },
];

// 에러 핸들링 유틸리티
export const handleAPIError = (error) => {
  if (error.response) {
    // 서버 응답 오류
    const { status, data } = error.response;
    return {
      message: data?.error || `서버 오류 (${status})`,
      status,
    };
  } else if (error.request) {
    // 네트워크 오류
    return {
      message: "네트워크 연결을 확인해주세요",
      status: 0,
    };
  } else {
    // 기타 오류
    return {
      message: error.message || "알 수 없는 오류가 발생했습니다",
      status: -1,
    };
  }
};

export default api;
