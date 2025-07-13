import axios from "axios";
import React from "react"; // Added for useDebounce

// API 기본 URL (환경 변수 또는 기본값)
const API_BASE_URL =
  process.env.REACT_APP_API_URL ||
  "https://vph0fu827a.execute-api.us-east-1.amazonaws.com/prod";

// 개발 환경에서 CORS 우회용 모키 모드
const IS_MOCK_MODE = process.env.NODE_ENV === 'development' && process.env.REACT_APP_USE_MOCK !== 'false';

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

    // 인증 토큰 추가 (API Gateway Cognito Authorizer는 ID Token을 요구)
    const token =
      localStorage.getItem("idToken") || localStorage.getItem("accessToken");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

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

    // 401 오류 시 토큰 갱신 시도 또는 로그인 페이지로 리다이렉트
    if (error.response?.status === 401) {
      // 토큰 만료 처리
      localStorage.removeItem("accessToken");
      localStorage.removeItem("idToken");
      localStorage.removeItem("refreshToken");

      // 로그인 페이지로 리다이렉트 (실제 구현 시 React Router 사용)
      window.location.href = "/login";
    }

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
    const response = await api.get(`/projects/${projectId}/upload-url`, {
      params: { category, filename },
    });
    return response.data;
  },
};

// 제목 생성 API (Step Functions 기반)
export const generateAPI = {
  // 제목 생성 시작 (Step Functions 실행)
  startTitleGeneration: async (projectId, article, aiSettings) => {
    const payload = {
      article,
    };

    // AI 설정이 있으면 추가
    if (aiSettings) {
      payload.aiSettings = aiSettings;
    }

    const response = await api.post(`/projects/${projectId}/generate`, payload);
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
    if (!executionArn || executionArn === "undefined") {
      return {
        success: false,
        error: "실행 ARN이 없습니다. 직접 모드에서는 폴링이 필요하지 않습니다.",
      };
    }

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

  // 제목 생성 (직접 모드 + Step Functions 모드 지원)
  generateTitle: async (projectId, article, onProgress, aiSettings) => {
    try {
      // 제목 생성 시작
      const startResponse = await generateAPI.startTitleGeneration(
        projectId,
        article,
        aiSettings
      );

      // 직접 모드인 경우 (mode가 'direct'이거나 result가 바로 있는 경우)
      if (startResponse.mode === "direct" || startResponse.result) {
        if (onProgress) {
          onProgress({
            status: "completed",
            message: "제목 생성이 완료되었습니다!",
            result: startResponse.result,
          });
        }

        return {
          conversationId: startResponse.executionId || "direct-" + Date.now(),
          projectId: projectId,
          result: startResponse.result,
          usage: startResponse.usage || {},
          timestamp: startResponse.timestamp || new Date().toISOString(),
          mode: "direct",
          debug: startResponse.debug || {}
        };
      }

      // Step Functions 모드인 경우
      if (startResponse.executionArn) {
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
            timestamp:
              pollResponse.data.completedAt || new Date().toISOString(),
            executionArn: startResponse.executionArn,
            mode: "stepfunctions",
          };
        } else {
          throw new Error(pollResponse.error);
        }
      }

      throw new Error("알 수 없는 응답 형식입니다");
    } catch (error) {
      console.error("제목 생성 실패:", error);
      throw error;
    }
  },
};

// 🆕 프롬프트 카드 관리 API
export const promptCardAPI = {
  // 프롬프트 카드 목록 조회 (step_order 순으로 정렬)
  getPromptCards: async (
    projectId,
    includeContent = false,
    includeDisabled = false
  ) => {
    const params = {};
    if (includeContent) params.include_content = "true";
    if (includeDisabled) params.include_disabled = "true";

    const response = await api.get(`/prompts/${projectId}`, { params });
    return response.data;
  },

  // 새 프롬프트 카드 생성
  createPromptCard: async (projectId, promptData) => {
    const response = await api.post(`/prompts/${projectId}`, promptData);
    return response.data;
  },

  // 프롬프트 카드 수정
  updatePromptCard: async (projectId, promptId, promptData) => {
    const response = await api.put(
      `/prompts/${projectId}/${promptId}`,
      promptData
    );
    return response.data;
  },

  // 프롬프트 카드 삭제
  deletePromptCard: async (projectId, promptId) => {
    const response = await api.delete(`/prompts/${projectId}/${promptId}`);
    return response.data;
  },

  // 프롬프트 카드 순서 변경
  reorderPromptCard: async (projectId, promptId, newStepOrder) => {
    const response = await api.put(`/prompts/${projectId}/${promptId}`, {
      step_order: newStepOrder,
    });
    return response.data;
  },

  // 프롬프트 카드 활성/비활성 토글
  togglePromptCard: async (projectId, promptId, enabled) => {
    const response = await api.put(`/prompts/${projectId}/${promptId}`, {
      enabled: enabled,
    });
    return response.data;
  },
};

// 🆕 인증 API
export const authAPI = {
  // 회원가입
  signup: async (userData) => {
    const response = await api.post("/auth/signup", userData);
    return response.data;
  },

  // 로그인
  signin: async (credentials) => {
    const response = await api.post("/auth/signin", credentials);
    const { accessToken, idToken, refreshToken } = response.data;

    // 토큰 저장
    localStorage.setItem("accessToken", accessToken);
    localStorage.setItem("idToken", idToken);
    localStorage.setItem("refreshToken", refreshToken);

    return response.data;
  },

  // 로그아웃
  signout: async () => {
    try {
      await api.post("/auth/signout");
    } finally {
      // 로컬 토큰 삭제
      localStorage.removeItem("accessToken");
      localStorage.removeItem("idToken");
      localStorage.removeItem("refreshToken");
    }
  },

  // 토큰 갱신
  refreshToken: async () => {
    const refreshToken = localStorage.getItem("refreshToken");
    if (!refreshToken) {
      throw new Error("리프레시 토큰이 없습니다");
    }

    const response = await api.post("/auth/refresh", { refreshToken });
    const { accessToken, idToken } = response.data;

    // 새 토큰 저장
    localStorage.setItem("accessToken", accessToken);
    localStorage.setItem("idToken", idToken);

    return response.data;
  },

  // 이메일 인증
  verifyEmail: async (verificationData) => {
    const response = await api.post("/auth/verify", verificationData);
    return response.data;
  },

  // 비밀번호 찾기
  forgotPassword: async (email) => {
    const response = await api.post("/auth/forgot-password", { email });
    return response.data;
  },

  // 비밀번호 재설정
  confirmPassword: async (resetData) => {
    const response = await api.post("/auth/confirm-password", resetData);
    return response.data;
  },

  // 현재 사용자 정보 (토큰에서 추출)
  getCurrentUser: () => {
    const token = localStorage.getItem("idToken");
    if (!token) return null;

    try {
      // JWT 토큰 디코딩 (간단한 방법 - 실제로는 jwt-decode 라이브러리 사용 권장)
      const payload = JSON.parse(atob(token.split(".")[1]));
      return {
        email: payload.email,
        name: payload.name,
        sub: payload.sub,
      };
    } catch (error) {
      console.error("토큰 디코딩 오류:", error);
      return null;
    }
  },

  // 로그인 상태 확인
  isAuthenticated: () => {
    const token = localStorage.getItem("accessToken");
    if (!token) return false;

    try {
      // 토큰 만료 시간 확인
      const payload = JSON.parse(atob(token.split(".")[1]));
      const currentTime = Date.now() / 1000;
      return payload.exp > currentTime;
    } catch (error) {
      return false;
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

// 🆕 프롬프트 카테고리 정의 (레거시 - 기존 파일 업로드용)
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

// 🆕 프롬프트 카드 카테고리 정의 (새로운 카드 시스템용)
// 프롬프트 오케스트레이션 카테고리 체계
export const PROMPT_CARD_CATEGORIES = [
  {
    id: "role",
    name: "역할 (Role)",
    description: "모델이 맡게 될 페르소나 및 역할 정의",
    color: "purple",
    icon: "🎭",
    order: 1,
    orchestration_step: "persona_definition"
  },
  {
    id: "guideline",
    name: "가이드라인 (Guideline)",
    description: "명확한 제한사항, 룰, 조건",
    color: "blue",
    icon: "📦",
    order: 2,
    orchestration_step: "constraint_definition"
  },
  {
    id: "workflow",
    name: "워크플로우 (Workflow)",
    description: "작업을 수행할 단계, 순서",
    color: "green",
    icon: "🧩",
    order: 3,
    orchestration_step: "process_execution"
  },
  {
    id: "output_format",
    name: "출력결과 (Output Format)",
    description: "최종 결과물 포맷 정의",
    color: "orange",
    icon: "🎯",
    order: 4,
    orchestration_step: "format_validation"
  },
  {
    id: "few_shot",
    name: "예시 (Few-shot)",
    description: "few-shot learning 예제",
    color: "yellow",
    icon: "💡",
    order: 5,
    orchestration_step: "example_learning"
  },
  {
    id: "scoring",
    name: "검수 (Scoring)",
    description: "검수 규칙 및 평가 기준",
    color: "red",
    icon: "🔍",
    order: 6,
    orchestration_step: "quality_assessment"
  },
];

// 사용 가능한 AI 모델 목록
export const AVAILABLE_MODELS = [
  {
    id: "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    name: "Claude 3.5 Sonnet (최신)",
    description: "가장 최신이고 성능이 뛰어난 모델",
    maxTokens: 200000,
  },
  {
    id: "us.anthropic.claude-3-sonnet-20240229-v1:0",
    name: "Claude 3 Sonnet",
    description: "균형잡힌 성능과 속도",
    maxTokens: 200000,
  },
  {
    id: "us.anthropic.claude-3-haiku-20240307-v1:0",
    name: "Claude 3 Haiku",
    description: "빠른 속도, 효율적인 처리",
    maxTokens: 200000,
  },
  {
    id: "anthropic.claude-instant-v1",
    name: "Claude Instant",
    description: "즉시 응답, 간단한 작업용",
    maxTokens: 100000,
  },
  {
    id: "amazon.titan-text-lite-v1",
    name: "Titan Text Lite",
    description: "가벼운 텍스트 처리",
    maxTokens: 4000,
  },
  {
    id: "amazon.titan-text-express-v1",
    name: "Titan Text Express",
    description: "빠른 텍스트 생성",
    maxTokens: 8000,
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

// 기본 프로젝트 카테고리 정의 (이모지 제거, 전문적 디자인)
export const DEFAULT_PROJECT_CATEGORIES = [
  {
    id: "news",
    name: "뉴스/언론",
    color: "blue",
    description: "뉴스 기사, 언론 보도 제목 생성",
    isDefault: true,
  },
  {
    id: "business",
    name: "비즈니스",
    color: "green",
    description: "비즈니스 문서, 기업 커뮤니케이션",
    isDefault: true,
  },
  {
    id: "corporate",
    name: "기업 홍보",
    color: "purple",
    description: "기업 홍보, 마케팅 콘텐츠",
    isDefault: true,
  },
  {
    id: "education",
    name: "교육/연구",
    color: "orange",
    description: "교육 자료, 연구 논문, 학술 자료",
    isDefault: true,
  },
  {
    id: "marketing",
    name: "마케팅/광고",
    color: "yellow",
    description: "광고 카피, 마케팅 캠페인",
    isDefault: true,
  },
  {
    id: "social",
    name: "소셜미디어",
    color: "indigo",
    description: "SNS 포스팅, 소셜 콘텐츠",
    isDefault: true,
  },
  {
    id: "tech",
    name: "기술/IT",
    color: "cyan",
    description: "기술 문서, IT 뉴스, 개발 관련",
    isDefault: true,
  },
];

// 사용자 정의 카테고리 API
export const categoryAPI = {
  // 사용자 카테고리 목록 조회
  getUserCategories: async () => {
    try {
      const response = await api.get("/categories");
      return response.data;
    } catch (error) {
      // 백엔드 API가 없는 경우 로컬 스토리지 사용
      const savedCategories = localStorage.getItem("userCategories");
      if (savedCategories) {
        return JSON.parse(savedCategories);
      }
      return { categories: DEFAULT_PROJECT_CATEGORIES };
    }
  },

  // 사용자 카테고리 생성
  createCategory: async (categoryData) => {
    try {
      const response = await api.post("/categories", categoryData);
      return response.data;
    } catch (error) {
      // 로컬 스토리지 사용
      const savedCategories = localStorage.getItem("userCategories");
      const categories = savedCategories
        ? JSON.parse(savedCategories)
        : { categories: [...DEFAULT_PROJECT_CATEGORIES] };

      const newCategory = {
        ...categoryData,
        id: `custom_${Date.now()}`,
        isDefault: false,
        createdAt: new Date().toISOString(),
      };

      categories.categories.push(newCategory);
      localStorage.setItem("userCategories", JSON.stringify(categories));
      return newCategory;
    }
  },

  // 사용자 카테고리 수정
  updateCategory: async (categoryId, categoryData) => {
    try {
      const response = await api.put(`/categories/${categoryId}`, categoryData);
      return response.data;
    } catch (error) {
      // 로컬 스토리지 사용
      const savedCategories = localStorage.getItem("userCategories");
      const categories = savedCategories
        ? JSON.parse(savedCategories)
        : { categories: [...DEFAULT_PROJECT_CATEGORIES] };

      const categoryIndex = categories.categories.findIndex(
        (cat) => cat.id === categoryId
      );
      if (categoryIndex !== -1) {
        categories.categories[categoryIndex] = {
          ...categories.categories[categoryIndex],
          ...categoryData,
          updatedAt: new Date().toISOString(),
        };
        localStorage.setItem("userCategories", JSON.stringify(categories));
        return categories.categories[categoryIndex];
      }
      throw new Error("카테고리를 찾을 수 없습니다");
    }
  },

  // 사용자 카테고리 삭제
  deleteCategory: async (categoryId) => {
    try {
      const response = await api.delete(`/categories/${categoryId}`);
      return response.data;
    } catch (error) {
      // 로컬 스토리지 사용
      const savedCategories = localStorage.getItem("userCategories");
      const categories = savedCategories
        ? JSON.parse(savedCategories)
        : { categories: [...DEFAULT_PROJECT_CATEGORIES] };

      const categoryIndex = categories.categories.findIndex(
        (cat) => cat.id === categoryId
      );
      if (categoryIndex !== -1) {
        categories.categories.splice(categoryIndex, 1);
        localStorage.setItem("userCategories", JSON.stringify(categories));
        return { success: true };
      }
      throw new Error("카테고리를 찾을 수 없습니다");
    }
  },
};

// 프로젝트 카테고리 변경 API
export const projectCategoryAPI = {
  // 프로젝트 카테고리 변경
  updateProjectCategory: async (projectId, categoryId) => {
    try {
      const response = await api.put(`/projects/${projectId}/category`, {
        category: categoryId,
      });
      return response.data;
    } catch (error) {
      // 임시로 클라이언트에서 처리 (실제로는 백엔드에서 처리해야 함)
      console.log(`프로젝트 ${projectId}의 카테고리를 ${categoryId}로 변경`);
      return { success: true, projectId, category: categoryId };
    }
  },
};

//프로젝트 통계 정보 API
export const projectStatsAPI = {
  // 프로젝트 상세 통계 조회
  getProjectStats: async (projectId) => {
    const response = await api.get(`/projects/${projectId}/stats`);
    return response.data;
  },

  // 모든 프로젝트 통계 요약
  getAllProjectsStats: async () => {
    const response = await api.get("/projects/stats");
    return response.data;
  },
};

// 프롬프트 통계 정보 계산 유틸리티
export const calculatePromptStats = (promptCards) => {
  const stats = {
    totalCards: promptCards.length,
    activeCards: promptCards.filter((card) => card.enabled !== false).length,
    totalTokens: 0,
    totalSize: 0,
    avgTokensPerCard: 0,
    categories: new Set(),
    models: new Set(),
    temperatureRange: { min: 1, max: 0 },
  };

  promptCards.forEach((card) => {
    // 카테고리 수집
    stats.categories.add(card.category);

    // 모델 수집
    stats.models.add(card.model);

    // 프롬프트 텍스트 통계
    if (card.prompt_text) {
      const textLength = card.prompt_text.length;
      stats.totalSize += textLength;

      // 대략적인 토큰 수 계산 (영어: 4자/토큰, 한국어: 2자/토큰)
      const estimatedTokens = Math.ceil(textLength / 2.5);
      stats.totalTokens += estimatedTokens;
    }

    // 온도 범위 계산
    const temp = parseFloat(card.temperature);
    if (temp < stats.temperatureRange.min) stats.temperatureRange.min = temp;
    if (temp > stats.temperatureRange.max) stats.temperatureRange.max = temp;
  });

  // 평균 토큰 계산
  stats.avgTokensPerCard =
    stats.totalCards > 0 ? Math.round(stats.totalTokens / stats.totalCards) : 0;

  // Set을 배열로 변환
  stats.categories = Array.from(stats.categories);
  stats.models = Array.from(stats.models);

  return stats;
};

// 프롬프트 오케스트레이션 API
export const orchestrationAPI = {
  // 오케스트레이션 실행
  executeOrchestration: async (projectId, articleContent, orchestrationConfig = {}) => {
    // 개발 환경에서 CORS 문제 우회용 모키 응답
    if (IS_MOCK_MODE) {
      console.log("🚀 모키 모드: AI 제목 생성 시뮬레이션");
      
      // 실제와 유사한 응답 시뮬레이션
      await new Promise(resolve => setTimeout(resolve, 2000)); // 2초 지연
      
      // 실제 API와 동일한 응답 구조 사용
      return {
        message: '제목 생성이 완료되었습니다',
        executionId: `mock-${Date.now()}`,
        projectId: 'mock-project',
        result: `1. AI가 제안하는 혁신적인 제목 1번
2. 데이터 기반으로 생성된 매력적인 제목 2번
3. 독자의 관심을 끄는 최적화된 제목 3번
4. SEO와 가독성을 고려한 제목 4번
5. 감정적 어필이 강한 제목 5번`,
        mode: 'mock',
        timestamp: new Date().toISOString(),
        debug: {
          promptCount: orchestrationConfig.enabledSteps?.length || 5,
          usedDefaultGuidelines: false,
          combinedPromptsLength: 1500,
          promptTitles: orchestrationConfig.enabledSteps || ["instruction", "knowledge", "secondary", "style_guide", "validation"],
          firstPromptPreview: "모키 모드에서 실행된 프롬프트입니다..."
        }
      };
    }

    // 실제 API 호출 - /generate 엔드포인트 사용
    const response = await api.post(`/projects/${projectId}/generate`, {
      article: articleContent,
      useStepFunction: false, // 직접 모드 사용
      enabledSteps: orchestrationConfig.enabledSteps || [],
      temperature: orchestrationConfig.temperature || 0.7
    });
    return response.data;
  },

  // 오케스트레이션 상태 조회
  getOrchestrationStatus: async (projectId, executionId) => {
    const response = await api.get(`/projects/${projectId}/orchestrate/${executionId}/status`);
    return response.data;
  },

  // 오케스트레이션 결과 조회
  getOrchestrationResult: async (projectId, executionId) => {
    const response = await api.get(`/projects/${projectId}/orchestrate/${executionId}/result`);
    return response.data;
  },

  // 오케스트레이션 로그 조회
  getOrchestrationLogs: async (projectId, executionId) => {
    const response = await api.get(`/projects/${projectId}/orchestrate/${executionId}/logs`);
    return response.data;
  },

  // 오케스트레이션 전략 테스트
  testOrchestrationStep: async (projectId, stepType, promptContent, articleContent) => {
    const response = await api.post(`/projects/${projectId}/orchestrate/test`, {
      stepType,
      promptContent,
      articleContent
    });
    return response.data;
  },

  // 오케스트레이션 고도화 설정
  updateOrchestrationConfig: async (projectId, config) => {
    const response = await api.put(`/projects/${projectId}/orchestration-config`, config);
    return response.data;
  },

  // 오케스트레이션 메트릭 조회
  getOrchestrationMetrics: async (projectId, timeRange = '24h') => {
    const response = await api.get(`/projects/${projectId}/orchestration-metrics`, {
      params: { timeRange }
    });
    return response.data;
  }
};

// 오케스트레이션 단계 정의
export const ORCHESTRATION_STEPS = {
  PERSONA_DEFINITION: {
    id: 'persona_definition',
    name: '역할 정의',
    description: 'AI 모델에게 역할과 페르소나를 부여',
    order: 1,
    required: true
  },
  CONSTRAINT_DEFINITION: {
    id: 'constraint_definition', 
    name: '제약 조건 설정',
    description: '명확한 룰과 제한사항 적용',
    order: 2,
    required: true
  },
  PROCESS_EXECUTION: {
    id: 'process_execution',
    name: '워크플로우 실행',
    description: '단계별 작업 프로세스 수행',
    order: 3,
    required: true
  },
  FORMAT_VALIDATION: {
    id: 'format_validation',
    name: '포맷 검증',
    description: '출력 결과물 포맷 검증 및 조정',
    order: 4,
    required: false
  },
  EXAMPLE_LEARNING: {
    id: 'example_learning',
    name: '예시 학습',
    description: 'Few-shot 예제를 통한 학습 및 측고',
    order: 5,
    required: false
  },
  QUALITY_ASSESSMENT: {
    id: 'quality_assessment',
    name: '품질 평가',
    description: '결과물 품질 평가 및 점수 매기기',
    order: 6,
    required: false
  }
};

// 🆕 파일 크기 포맷팅 유틸리티
export const formatFileSize = (bytes) => {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
};

// 🆕 토큰 수 포맷팅 유틸리티
export const formatTokenCount = (tokens) => {
  if (tokens < 1000) return tokens.toString();
  if (tokens < 1000000) return (tokens / 1000).toFixed(1) + "K";
  return (tokens / 1000000).toFixed(1) + "M";
};

// 🆕 카테고리 관련 유틸리티 (수정됨)
export const getCategoryInfo = (categoryId, userCategories = []) => {
  const allCategories = [...DEFAULT_PROJECT_CATEGORIES, ...userCategories];
  return (
    allCategories.find((cat) => cat.id === categoryId) ||
    DEFAULT_PROJECT_CATEGORIES.find((cat) => cat.id === "news")
  );
};

// 🆕 카테고리별 색상 클래스 반환 (수정됨)
export const getCategoryColorClasses = (color) => {
  const colors = {
    blue: "bg-blue-100 text-blue-800 border-blue-200",
    green: "bg-green-100 text-green-800 border-green-200",
    purple: "bg-purple-100 text-purple-800 border-purple-200",
    orange: "bg-orange-100 text-orange-800 border-orange-200",
    yellow: "bg-yellow-100 text-yellow-800 border-yellow-200",
    indigo: "bg-indigo-100 text-indigo-800 border-indigo-200",
    cyan: "bg-cyan-100 text-cyan-800 border-cyan-200",
    red: "bg-red-100 text-red-800 border-red-200",
    pink: "bg-pink-100 text-pink-800 border-pink-200",
    gray: "bg-gray-100 text-gray-800 border-gray-200",
  };
  return colors[color] || colors.gray;
};

// 🆕 색상 옵션 (카테고리 생성 시 사용)
export const COLOR_OPTIONS = [
  { id: "blue", name: "파란색", class: "bg-blue-500" },
  { id: "green", name: "초록색", class: "bg-green-500" },
  { id: "purple", name: "보라색", class: "bg-purple-500" },
  { id: "orange", name: "주황색", class: "bg-orange-500" },
  { id: "yellow", name: "노란색", class: "bg-yellow-500" },
  { id: "indigo", name: "남색", class: "bg-indigo-500" },
  { id: "cyan", name: "청록색", class: "bg-cyan-500" },
  { id: "red", name: "빨간색", class: "bg-red-500" },
  { id: "pink", name: "분홍색", class: "bg-pink-500" },
  { id: "gray", name: "회색", class: "bg-gray-500" },
];

// 🆕 프로젝트 검색 및 필터링 유틸리티
export const filterProjects = (projects, { category, searchQuery, sortBy }) => {
  let filtered = [...projects];

  // 카테고리 필터링
  if (category && category !== "all") {
    filtered = filtered.filter((project) => project.category === category);
  }

  // 검색 필터링
  if (searchQuery && searchQuery.trim()) {
    const query = searchQuery.toLowerCase().trim();
    filtered = filtered.filter(
      (project) =>
        project.name.toLowerCase().includes(query) ||
        (project.description &&
          project.description.toLowerCase().includes(query)) ||
        (project.tags &&
          project.tags.some((tag) => tag.toLowerCase().includes(query)))
    );
  }

  // 정렬
  switch (sortBy) {
    case "name":
      filtered.sort((a, b) => a.name.localeCompare(b.name));
      break;
    case "updated":
      filtered.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
      break;
    case "created":
    default:
      filtered.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
      break;
  }

  return filtered;
};

// 🆕 디바운스 훅 (검색 최적화용)
export const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = React.useState(value);

  React.useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

export default api;
