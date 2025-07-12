import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import Login from "./Login";
import Signup from "./Signup";
import EmailVerification from "./EmailVerification";
import { useAuth } from "../contexts/AuthContext";

const AuthContainer = ({ onAuthSuccess }) => {
  const [currentView, setCurrentView] = useState("login"); // 'login', 'signup', 'verify'
  const [signupEmail, setSignupEmail] = useState("");
  const navigate = useNavigate();
  const { login, signup, verifyEmail } = useAuth();

  const handleLoginSuccess = async (response) => {
    // AuthContext의 상태가 업데이트되면 자동으로 App.js에서 인증된 화면으로 전환됨
    console.log("로그인 성공:", response);
    // 명시적으로 홈페이지로 리다이렉트
    navigate("/", { replace: true });
  };

  const handleSignupSuccess = (response, email) => {
    setSignupEmail(email || response.email || signupEmail);
    setCurrentView("verify");
  };

  const handleVerificationSuccess = () => {
    setCurrentView("login");
    alert("이메일 인증이 완료되었습니다. 로그인해주세요.");
  };

  const handleSwitchToSignup = () => {
    setCurrentView("signup");
  };

  const handleSwitchToLogin = () => {
    setCurrentView("login");
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case "signup":
        return (
          <Signup
            onSignupSuccess={handleSignupSuccess}
            onSwitchToLogin={handleSwitchToLogin}
          />
        );
      case "verify":
        return (
          <EmailVerification
            email={signupEmail}
            onVerificationSuccess={handleVerificationSuccess}
            onBackToLogin={handleSwitchToLogin}
          />
        );
      case "login":
      default:
        return (
          <Login
            onLoginSuccess={handleLoginSuccess}
            onSwitchToSignup={handleSwitchToSignup}
          />
        );
    }
  };

  return renderCurrentView();
};

export default AuthContainer;