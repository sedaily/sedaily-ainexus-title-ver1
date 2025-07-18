import axios from "axios";

// API 기본 설정
const API_BASE_URL =
  process.env.REACT_APP_API_URL ||
  "https://gcm3qzoy04.execute-api.us-east-1.amazonaws.com/prod";

// Axios 인스턴스
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 300000, // 5분
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
// 프로젝트 API (기존 유지)
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
// 프롬프트 카드 API (기존 유지)
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
// 🔧 완전 수정된 제목 생성 API
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

  // 🔧 실제 스트리밍 구현 - Server-Sent Events 사용
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
      // 1. 먼저 실제 스트리밍 API 시도
      const streamingUrl = `${API_BASE_URL}/projects/${projectId}/generate/stream`;
      
      console.log("🚀 실제 스트리밍 API 시도:", streamingUrl);

      const response = await fetch(streamingUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // 2. 응답이 스트리밍 형식인지 확인
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('text/event-stream')) {
        console.log("❌ 스트리밍 응답이 아님, 폴백 처리");
        throw new Error("스트리밍 응답이 아닙니다");
      }

      // 3. 실제 스트리밍 처리
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fullResponse = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const eventData = JSON.parse(line.slice(6));
                
                if (eventData.type === 'start') {
                  console.log("✅ 스트리밍 시작");
                } else if (eventData.type === 'chunk') {
                  fullResponse += eventData.response;
                  if (onChunk) {
                    onChunk(eventData.response, { content: eventData.response });
                  }
                } else if (eventData.type === 'complete') {
                  console.log("✅ 스트리밍 완료");
                  if (onComplete) {
                    onComplete({
                      result: eventData.fullResponse || fullResponse,
                      timestamp: new Date().toISOString(),
                    });
                  }
                  return { result: eventData.fullResponse || fullResponse };
                } else if (eventData.type === 'error') {
                  throw new Error(eventData.error);
                }
              } catch (parseError) {
                console.error("JSON 파싱 오류:", parseError);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }

      return { result: fullResponse };

    } catch (streamError) {
      console.log("⚠️ 스트리밍 실패, 폴백 처리:", streamError.message);
      
      // 4. 폴백: 일반 API 호출
      try {
        const fallbackResponse = await api.post(
          `/projects/${projectId}/generate`,
          data
        );

        console.log("✅ 폴백 API 성공:", {
          mode: fallbackResponse.data.mode,
          timestamp: new Date().toISOString(),
        });

        // 폴백 응답을 스트리밍처럼 시뮬레이션
        if (fallbackResponse.data.result && onChunk) {
          const fullText = fallbackResponse.data.result;
          const words = fullText.split(" ");

          for (let i = 0; i < words.length; i++) {
            const word = words[i] + (i < words.length - 1 ? " " : "");
            onChunk(word, { content: word });
            await new Promise((resolve) => setTimeout(resolve, 30));
          }
        }

        // 완료 콜백 호출
        if (onComplete) {
          onComplete({
            result: fallbackResponse.data.result,
            model_info: fallbackResponse.data.model_info,
            performance_metrics: fallbackResponse.data.performance_metrics,
            timestamp: new Date().toISOString(),
          });
        }

        return fallbackResponse.data;
      } catch (fallbackError) {
        console.error("❌ 폴백 API도 실패:", fallbackError);
        if (onError) {
          onError(
            new Error("서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.")
          );
        }
        throw new Error("서비스를 사용할 수 없습니다.");
      }
    }
  },

  getExecutionStatus: async (executionArn) => {
    return {
      status: "SUCCEEDED",
      output: "{}",
    };
  },
};

// =============================================================================
// 채팅 API (기존 유지)
// =============================================================================

export const chatAPI = {
  sendMessage: async (projectId, message, sessionId, userId = "default") => {
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
        chat_history: [],
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
    console.log("채팅 세션 목록 조회:", { projectId, userId });

    return {
      sessions: [],
      message:
        "채팅 세션은 현재 지원되지 않습니다. 각 대화는 독립적으로 처리됩니다.",
    };
  },

  deleteChatSession: async (projectId, sessionId, userId = "default") => {
    console.log("채팅 세션 삭제:", { projectId, sessionId, userId });

    return {
      message: "채팅 세션 삭제가 완료되었습니다.",
      sessionId,
      userId,
    };
  },
};

// =============================================================================
// 인증 API (기존 유지)
// =============================================================================

export const authAPI = {
  isAuthenticated: () => {
    return true;
  },

  getCurrentUser: () => {
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
// 🔧 개선된 오류 처리 함수
// =============================================================================

export const handleAPIError = (error) => {
  console.error("API 오류 상세 분석:", {
    message: error.message,
    code: error.code,
    status: error.response?.status,
    statusText: error.response?.statusText,
    data: error.response?.data,
    timestamp: new Date().toISOString(),
  });

  // 403 Forbidden 특별 처리
  if (error.response?.status === 403) {
    return {
      message: "API 접근이 차단되었습니다. 관리자에게 문의하세요.",
      statusCode: 403,
      errorType: "FORBIDDEN",
    };
  }

  // Gateway Timeout 특별 처리
  if (error.response?.status === 504) {
    return {
      message:
        "서버 응답 시간이 초과되었습니다. 요청을 간소화하거나 잠시 후 다시 시도해주세요.",
      statusCode: 504,
      errorType: "GATEWAY_TIMEOUT",
    };
  }

  // CORS 오류 특별 처리
  if (
    error.message?.includes("CORS") ||
    error.code === "ERR_NETWORK" ||
    error.message?.includes("Access-Control-Allow-Origin")
  ) {
    return {
      message:
        "서버 연결 설정에 문제가 있습니다. 페이지를 새로고침하고 다시 시도해주세요.",
      statusCode: 0,
      errorType: "CORS_ERROR",
    };
  }

  // 타임아웃 오류 특별 처리
  if (error.code === "ECONNABORTED") {
    return {
      message:
        "요청 처리 시간이 초과되었습니다. 입력을 줄이거나 잠시 후 다시 시도해주세요.",
      statusCode: 0,
      errorType: "TIMEOUT_ERROR",
    };
  }

  if (error.response) {
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
    return {
      message: "서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요",
      statusCode: 0,
      errorType: "NETWORK_ERROR",
    };
  } else {
    return {
      message: `요청 오류: ${error.message}`,
      statusCode: -1,
      errorType: "REQUEST_ERROR",
    };
  }
};

// =============================================================================
// 기타 유틸리티 함수들 (기존 유지)
// =============================================================================

export const DYNAMIC_PROMPT_SYSTEM = {
  message:
    "원하는 만큼 프롬프트 카드를 생성하여 나만의 AI 어시스턴트를 만들어보세요!",
  maxPromptCards: 50,
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

  if (filters.searchQuery) {
    const query = filters.searchQuery.toLowerCase();
    filtered = filtered.filter(
      (project) =>
        project.name?.toLowerCase().includes(query) ||
        project.description?.toLowerCase().includes(query) ||
        project.tags?.some((tag) => tag.toLowerCase().includes(query))
    );
  }

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
