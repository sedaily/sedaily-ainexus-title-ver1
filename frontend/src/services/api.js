import axios from "axios";

// API 기본 설정
const API_BASE_URL =
  process.env.REACT_APP_API_URL ||
  "https://gcm3qzoy04.execute-api.us-east-1.amazonaws.com/prod";

// Axios 인스턴스
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 900000, // 15분 타임아웃 (긴 텍스트 및 복잡한 대화 처리를 위해 대폭 연장)
});

// 요청 인터셉터
api.interceptors.request.use((config) => {
  console.log("API 요청:", config.method?.toUpperCase(), config.url);
  return config;
});

// 응답 인터셉터
api.interceptors.response.use(
  (response) => {
    console.log("API 응답:", response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error("API 오류 상세:", {
      status: error.response?.status,
      message: error.message,
      code: error.code,
      url: error.config?.url,
      data: error.response?.data,
    });
    return Promise.reject(error);
  }
);

// =============================================================================
// 1. 프로젝트 API
// =============================================================================

export const projectAPI = {
  getProjects: async () => {
    const response = await api.get("/projects");
    return response.data;
  },

  getProject: async (projectId) => {
    const response = await api.get(`/projects/${projectId}`);
    return response.data;
  },

  createProject: async (projectData) => {
    const response = await api.post("/projects", projectData);
    return response.data;
  },

  updateProject: async (projectId, projectData) => {
    const response = await api.put(`/projects/${projectId}`, projectData);
    return response.data;
  },

  deleteProject: async (projectId) => {
    const response = await api.delete(`/projects/${projectId}`);
    return response.data;
  },

  getUploadUrl: async (projectId, fileName) => {
    const response = await api.get(`/projects/${projectId}/upload-url`, {
      params: { fileName },
    });
    return response.data;
  },
};

// =============================================================================
// 2. 프롬프트 카드 API
// =============================================================================

export const promptCardAPI = {
  getPromptCards: async (
    projectId,
    includeContent = false,
    includeStats = false
  ) => {
    const response = await api.get(`/prompts/${projectId}`, {
      params: { includeContent, includeStats },
    });
    return response.data;
  },

  createPromptCard: async (projectId, promptData) => {
    const response = await api.post(`/prompts/${projectId}`, promptData);
    return response.data;
  },

  updatePromptCard: async (projectId, promptId, promptData) => {
    const response = await api.put(
      `/prompts/${projectId}/${promptId}`,
      promptData
    );
    return response.data;
  },

  getPromptContent: async (projectId, promptId) => {
    const response = await api.get(`/prompts/${projectId}/${promptId}/content`);
    return response.data;
  },

  deletePromptCard: async (projectId, promptId) => {
    const response = await api.delete(`/prompts/${projectId}/${promptId}`);
    return response.data;
  },

  reorderPromptCards: async (projectId, reorderData) => {
    // 백엔드에서 별도의 reorder API가 없으므로 개별 업데이트로 처리
    // reorderData = [{ promptId, stepOrder }, ...]
    const updatePromises = reorderData.map(({ promptId, stepOrder }) =>
      api.put(`/prompts/${projectId}/${promptId}`, { stepOrder })
    );

    const responses = await Promise.all(updatePromises);
    return {
      message: "프롬프트 카드 순서가 업데이트되었습니다.",
      updatedCards: responses.map((r) => r.data),
    };
  },
};

// =============================================================================
// 3. 제목 생성 API
// =============================================================================

export const generateAPI = {
  generateTitle: async (projectId, data) => {
    console.log("대화 생성 요청 시작:", {
      projectId,
      inputLength: data.userInput.length,
      historyLength: data.chat_history?.length || 0,
      timestamp: new Date().toISOString(),
    });

    try {
      const response = await api.post(`/projects/${projectId}/generate`, data);

      console.log("대화 생성 성공:", {
        status: response.status,
        mode: response.data.mode,
        message: response.data.message,
        timestamp: new Date().toISOString(),
      });

      return response.data;
    } catch (error) {
      console.error("대화 생성 실패:", {
        code: error.code,
        message: error.message,
        status: error.response?.status,
        responseData: error.response?.data,
        timestamp: new Date().toISOString(),
      });
      throw error;
    }
  },

  // 스트리밍 응답을 위한 새로운 메서드
  generateTitleStream: async (
    projectId,
    data,
    onChunk,
    onError,
    onComplete
  ) => {
    console.log("스트리밍 대화 생성 요청 시작:", {
      projectId,
      inputLength: data.userInput.length,
      historyLength: data.chat_history?.length || 0,
      timestamp: new Date().toISOString(),
    });

    try {
      // 스트리밍 응답을 받기 위해 API 호출
      const response = await api.post(
        `/projects/${projectId}/generate/stream`,
        data
      );

      if (!response || !response.data) {
        throw new Error("응답이 없습니다");
      }

      const responseData = response.data;

      // 청크 데이터가 있는 경우 각 청크에 대해 콜백 호출
      if (responseData.chunks && Array.isArray(responseData.chunks)) {
        for (const chunk of responseData.chunks) {
          if (chunk.content && onChunk) {
            onChunk(chunk.content, chunk);
          }
        }
      }

      // 완료 콜백 호출
      if (onComplete) {
        onComplete({
          result: responseData.result,
          model_info: responseData.model_info,
          performance_metrics: responseData.performance_metrics,
          timestamp: responseData.timestamp || new Date().toISOString(),
        });
      }

      return {
        result: responseData.result,
        model_info: responseData.model_info,
        performance_metrics: responseData.performance_metrics,
        timestamp: responseData.timestamp || new Date().toISOString(),
      };
    } catch (error) {
      console.error("스트리밍 대화 생성 실패:", {
        code: error.code,
        message: error.message,
        timestamp: new Date().toISOString(),
      });

      // 에러 콜백 호출
      if (onError) {
        onError(error);
      }

      throw error;
    }
  },

  getExecutionStatus: async (executionArn) => {
    // 현재 구현에서는 사용하지 않음
    return {
      status: "SUCCEEDED",
      output: "{}",
    };
  },
};

// =============================================================================
// 4. 채팅 API (generate API로 리다이렉트)
// =============================================================================

export const chatAPI = {
  sendMessage: async (projectId, message, sessionId, userId = "default") => {
    // 채팅은 generate API를 사용하여 처리
    console.log("채팅 메시지를 generate API로 전달:", {
      projectId,
      message,
      sessionId,
      userId,
    });

    try {
      const response = await generateAPI.generateTitle(projectId, {
        userInput: message,
        userRequest: "",
        chat_history: [], // 현재 채팅 히스토리는 비워둠
      });

      return {
        response: response.result,
        sessionId,
        userId,
        timestamp: new Date().toISOString(),
        mode: response.mode || "chat",
      };
    } catch (error) {
      console.error("채팅 메시지 처리 실패:", error);
      throw error;
    }
  },

  getChatHistory: async (projectId, sessionId, userId = "default") => {
    // 현재 백엔드에서 채팅 히스토리를 별도로 저장하지 않음
    console.log("채팅 히스토리 조회:", { projectId, sessionId, userId });

    return {
      messages: [],
      sessionId,
      userId,
      message:
        "채팅 히스토리는 현재 지원되지 않습니다. 각 메시지는 독립적으로 처리됩니다.",
    };
  },

  getChatSessions: async (projectId, userId = "default") => {
    // 현재 백엔드에서 세션을 별도로 관리하지 않음
    console.log("채팅 세션 목록 조회:", { projectId, userId });

    return {
      sessions: [],
      message:
        "채팅 세션은 현재 지원되지 않습니다. 각 대화는 독립적으로 처리됩니다.",
    };
  },

  deleteChatSession: async (projectId, sessionId, userId = "default") => {
    // 현재 백엔드에서 세션을 별도로 관리하지 않음
    console.log("채팅 세션 삭제:", { projectId, sessionId, userId });

    return {
      message: "채팅 세션 삭제가 완료되었습니다.",
      sessionId,
      userId,
    };
  },
};

// =============================================================================
// 5. 인증 API
// =============================================================================

export const authAPI = {
  isAuthenticated: () => {
    // 실제 토큰 검증 로직으로 대체 필요
    return true;
  },

  getCurrentUser: () => {
    // 실제 사용자 정보 가져오기 로직으로 대체 필요
    return {
      id: "user",
      email: "user@example.com",
      name: "사용자",
    };
  },

  signin: async (credentials) => {
    const response = await api.post("/auth/signin", credentials);
    return response.data;
  },

  signup: async (userData) => {
    const response = await api.post("/auth/signup", userData);
    return response.data;
  },

  signout: async () => {
    const response = await api.post("/auth/signout");
    return response.data;
  },

  verifyEmail: async (verificationData) => {
    const response = await api.post("/auth/verify-email", verificationData);
    return response.data;
  },

  forgotPassword: async (email) => {
    const response = await api.post("/auth/forgot-password", { email });
    return response.data;
  },

  confirmPassword: async (resetData) => {
    const response = await api.post("/auth/confirm-password", resetData);
    return response.data;
  },
};

// =============================================================================
// 공통 유틸리티
// =============================================================================

export const handleAPIError = (error) => {
  if (error.response) {
    // 서버에서 응답을 받았지만 오류 상태
    const status = error.response.status;
    const message =
      error.response.data?.message ||
      error.response.data?.error ||
      "서버 오류가 발생했습니다";

    switch (status) {
      case 400:
        return { message: `잘못된 요청: ${message}`, statusCode: 400 };
      case 401:
        return { message: "인증이 필요합니다", statusCode: 401 };
      case 403:
        return { message: "권한이 없습니다", statusCode: 403 };
      case 404:
        return { message: "요청한 리소스를 찾을 수 없습니다", statusCode: 404 };
      case 429:
        return {
          message: "요청이 너무 많습니다. 잠시 후 다시 시도해주세요",
          statusCode: 429,
        };
      case 500:
        return { message: "서버 내부 오류가 발생했습니다", statusCode: 500 };
      default:
        return {
          message: `서버 오류 (${status}): ${message}`,
          statusCode: status,
        };
    }
  } else if (error.request) {
    // 요청은 보냈지만 응답을 받지 못함
    return {
      message: "서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요",
      statusCode: 0,
    };
  } else {
    // 요청 설정 중 오류 발생
    return {
      message: `요청 오류: ${error.message}`,
      statusCode: -1,
    };
  }
};

// =============================================================================
// 6. 동적 프롬프트 시스템 - 기본 설정 및 헬퍼 함수들
// =============================================================================

export const DYNAMIC_PROMPT_SYSTEM = {
  message:
    "원하는 만큼 프롬프트 카드를 생성하여 나만의 AI 어시스턴트를 만들어보세요!",
  maxPromptCards: 50, // 최대 프롬프트 카드 개수 제한 (선택사항)
  supportedFormats: ["text", "markdown"],
  defaultStepOrder: 1,
};

export const COLOR_OPTIONS = [
  {
    id: "blue",
    name: "파랑",
    bgClass: "bg-blue-100",
    textClass: "text-blue-800",
    borderClass: "border-blue-200",
  },
  {
    id: "green",
    name: "초록",
    bgClass: "bg-green-100",
    textClass: "text-green-800",
    borderClass: "border-green-200",
  },
  {
    id: "purple",
    name: "보라",
    bgClass: "bg-purple-100",
    textClass: "text-purple-800",
    borderClass: "border-purple-200",
  },
  {
    id: "orange",
    name: "주황",
    bgClass: "bg-orange-100",
    textClass: "text-orange-800",
    borderClass: "border-orange-200",
  },
  {
    id: "red",
    name: "빨강",
    bgClass: "bg-red-100",
    textClass: "text-red-800",
    borderClass: "border-red-200",
  },
  {
    id: "indigo",
    name: "남색",
    bgClass: "bg-indigo-100",
    textClass: "text-indigo-800",
    borderClass: "border-indigo-200",
  },
  {
    id: "pink",
    name: "분홍",
    bgClass: "bg-pink-100",
    textClass: "text-pink-800",
    borderClass: "border-pink-200",
  },
  {
    id: "yellow",
    name: "노랑",
    bgClass: "bg-yellow-100",
    textClass: "text-yellow-800",
    borderClass: "border-yellow-200",
  },
  {
    id: "gray",
    name: "회색",
    bgClass: "bg-gray-100",
    textClass: "text-gray-800",
    borderClass: "border-gray-200",
  },
];

export const getPromptCardInfo = (promptCard) => {
  // 동적 프롬프트 카드 정보 반환
  return {
    id: promptCard.promptId || promptCard.id,
    title: promptCard.title || "새 프롬프트 카드",
    color: promptCard.color || "gray",
    description: promptCard.description || "",
    stepOrder: promptCard.stepOrder || 1,
    isActive: promptCard.isActive !== false,
  };
};

export const filterProjects = (projects, filters) => {
  let filtered = [...projects];

  // 검색어 필터
  if (filters.searchQuery) {
    const query = filters.searchQuery.toLowerCase();
    filtered = filtered.filter(
      (project) =>
        project.name?.toLowerCase().includes(query) ||
        project.description?.toLowerCase().includes(query) ||
        project.tags?.some((tag) => tag.toLowerCase().includes(query))
    );
  }

  // 정렬
  switch (filters.sortBy) {
    case "created":
      filtered.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
      break;
    case "updated":
      filtered.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
      break;
    case "name":
      filtered.sort((a, b) => a.name?.localeCompare(b.name));
      break;
    default:
      break;
  }

  return filtered;
};

export const formatTokenCount = (count) => {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  return count.toString();
};

export const formatFileSize = (bytes) => {
  if (bytes >= 1024) {
    return `${(bytes / 1024).toFixed(1)}KB`;
  }
  return `${bytes}B`;
};

export const calculatePromptStats = (promptCards) => {
  if (!promptCards || promptCards.length === 0) {
    return {
      totalCards: 0,
      totalTokens: 0,
      averageTokens: 0,
      activeCards: 0,
      maxStepOrder: 0,
      hasCustomOrder: false,
    };
  }

  const activeCards = promptCards.filter((card) => card.isActive !== false);
  const totalTokens = activeCards.reduce((sum, card) => {
    return sum + (card.tokenCount || card.contentLength || 0);
  }, 0);

  const stepOrders = activeCards
    .map((card) => card.stepOrder || 0)
    .filter((step) => step > 0);
  const hasCustomOrder = stepOrders.length > 0;
  const maxStepOrder = stepOrders.length > 0 ? Math.max(...stepOrders) : 0;

  return {
    totalCards: promptCards.length,
    activeCards: activeCards.length,
    totalTokens,
    averageTokens:
      activeCards.length > 0 ? Math.round(totalTokens / activeCards.length) : 0,
    maxStepOrder,
    hasCustomOrder,
    stepOrderRange: {
      min: stepOrders.length > 0 ? Math.min(...stepOrders) : 0,
      max: maxStepOrder,
    },
  };
};
