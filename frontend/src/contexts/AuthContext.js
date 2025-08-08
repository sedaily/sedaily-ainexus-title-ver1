import React, { createContext, useContext, useState, useEffect } from "react";
import { Amplify } from "aws-amplify";
import {
  signUp,
  signIn,
  signOut,
  getCurrentUser,
  fetchAuthSession,
  confirmSignUp,
  resendSignUpCode,
  resetPassword,
  confirmResetPassword,
} from "aws-amplify/auth";
import awsConfig from "../aws-config";

// Amplify 설정
console.log("AWS Config loaded:", awsConfig);
Amplify.configure(awsConfig);

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      setLoading(true);
      
      // 실제 AWS Cognito 인증 체크
      const currentUser = await getCurrentUser();
      const session = await fetchAuthSession();

      // 사용자 그룹 정보 가져오기
      const groups = session?.tokens?.idToken?.payload["cognito:groups"] || [];
      const userRole = groups.includes("admin") ? "admin" : "user";

      // ID 토큰에서 이메일 정보 추출
      const email = session?.tokens?.idToken?.payload?.email || currentUser.username;
      const userName = email.includes("@") ? email.split("@")[0] : email;

      console.log("사용자 인증 정보:", {
        userId: currentUser.userId,
        username: currentUser.username,
        email: email,
        groups: groups,
        userRole: userRole,
        fullPayload: session?.tokens?.idToken?.payload
      });

      setIsAuthenticated(true);
      setUser({
        id: currentUser.userId,
        email: email,
        name: userName,
        role: userRole,
        groups: groups,
      });
    } catch (error) {
      console.error("Authentication check failed:", error);
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (credentials) => {
    try {
      const { email, password } = credentials;
      
      console.log("로그인 시도:", { email });

      // 실제 AWS Cognito 인증
      const user = await signIn({ username: email, password });
      
      console.log("signIn 결과:", user);

      if (user.isSignedIn === false) {
        if (user.nextStep?.signInStep === "CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED") {
          console.log("새 비밀번호 필요");
          throw new Error("새 비밀번호가 필요합니다");
        } else if (user.nextStep?.signInStep === "CONFIRM_SIGN_UP") {
          console.log("이메일 인증 필요");
          throw new Error("이메일 인증이 필요합니다");
        } else {
          console.log("로그인 실패 - 알 수 없는 상태:", user.nextStep);
          throw new Error("로그인에 실패했습니다");
        }
      }

      console.log("인증 상태 확인 중...");
      await checkAuthStatus();

      console.log("로그인 성공");
      return { success: true, user };
    } catch (error) {
      console.error("로그인 오류:", error);

      let errorMessage = "로그인에 실패했습니다.";

      if (error.name === "NotAuthorizedException") {
        errorMessage = "이메일 또는 비밀번호가 올바르지 않습니다.";
      } else if (error.name === "UserNotConfirmedException") {
        errorMessage = "이메일 인증이 필요합니다.";
      } else if (error.name === "UserNotFoundException") {
        errorMessage = "존재하지 않는 사용자입니다.";
      } else if (error.message) {
        errorMessage = error.message;
      }

      throw new Error(errorMessage);
    }
  };

  const signup = async (userData) => {
    try {
      const { email, password, fullname } = userData;

      const result = await signUp({
        username: email,
        password: password,
        options: {
          userAttributes: {
            email: email,
            name: fullname || email.split("@")[0],
          },
        },
      });

      return {
        success: true,
        message:
          "회원가입이 완료되었습니다. 이메일로 전송된 인증 코드를 확인해주세요.",
        userSub: result.userId,
      };
    } catch (error) {
      console.error("회원가입 오류:", error);

      let errorMessage = "회원가입에 실패했습니다.";

      if (error.name === "UsernameExistsException") {
        errorMessage = "이미 존재하는 이메일입니다.";
      } else if (error.name === "InvalidPasswordException") {
        errorMessage =
          "비밀번호가 정책에 맞지 않습니다. (최소 8자, 숫자 및 특수문자 포함)";
      } else if (error.message) {
        errorMessage = error.message;
      }

      throw new Error(errorMessage);
    }
  };

  const logout = async () => {
    try {
      await signOut();
      setIsAuthenticated(false);
      setUser(null);
    } catch (error) {
      console.error("로그아웃 오류:", error);
      // 로그아웃은 항상 성공으로 처리
      setIsAuthenticated(false);
      setUser(null);
    }
  };

  const verifyEmail = async (verificationData) => {
    try {
      const { email, code } = verificationData;

      await confirmSignUp({ username: email, confirmationCode: code });

      return {
        success: true,
        message: "이메일 인증이 완료되었습니다. 로그인하세요.",
      };
    } catch (error) {
      console.error("이메일 인증 오류:", error);

      let errorMessage = "이메일 인증에 실패했습니다.";

      if (error.name === "CodeMismatchException") {
        errorMessage = "인증 코드가 올바르지 않습니다.";
      } else if (error.name === "ExpiredCodeException") {
        errorMessage = "인증 코드가 만료되었습니다.";
      } else if (error.message) {
        errorMessage = error.message;
      }

      throw new Error(errorMessage);
    }
  };

  const resendVerificationCode = async (email) => {
    try {
      await resendSignUpCode({ username: email });
      return {
        success: true,
        message: "인증 코드가 다시 전송되었습니다.",
      };
    } catch (error) {
      console.error("인증 코드 재전송 오류:", error);
      throw new Error("인증 코드 재전송에 실패했습니다.");
    }
  };

  const forgotPassword = async (email) => {
    try {
      await resetPassword({ username: email });
      return {
        success: true,
        message: "비밀번호 재설정 코드가 이메일로 전송되었습니다.",
      };
    } catch (error) {
      console.error("비밀번호 찾기 오류:", error);
      throw new Error("비밀번호 찾기에 실패했습니다.");
    }
  };

  const confirmPassword = async (resetData) => {
    try {
      const { email, code, newPassword } = resetData;

      await confirmResetPassword({ 
        username: email, 
        confirmationCode: code, 
        newPassword: newPassword 
      });

      return {
        success: true,
        message: "비밀번호가 성공적으로 변경되었습니다.",
      };
    } catch (error) {
      console.error("비밀번호 재설정 오류:", error);

      let errorMessage = "비밀번호 재설정에 실패했습니다.";

      if (error.name === "CodeMismatchException") {
        errorMessage = "인증 코드가 올바르지 않습니다.";
      } else if (error.name === "ExpiredCodeException") {
        errorMessage = "인증 코드가 만료되었습니다.";
      } else if (error.message) {
        errorMessage = error.message;
      }

      throw new Error(errorMessage);
    }
  };

  // 토큰 갱신
  const refreshToken = async () => {
    try {
      const session = await fetchAuthSession();
      return session;
    } catch (error) {
      console.error("토큰 갱신 오류:", error);
      setIsAuthenticated(false);
      setUser(null);
      throw error;
    }
  };

  // API 요청용 인증 토큰 가져오기
  const getAuthToken = async () => {
    try {
      const session = await fetchAuthSession();
      return session?.tokens?.idToken?.toString();
    } catch (error) {
      console.error("토큰 가져오기 오류:", error);
      return null;
    }
  };

  const value = {
    isAuthenticated,
    user,
    loading,
    login,
    signup,
    logout,
    verifyEmail,
    resendVerificationCode,
    forgotPassword,
    confirmResetPassword: confirmPassword,
    checkAuthStatus,
    refreshToken,
    getAuthToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
