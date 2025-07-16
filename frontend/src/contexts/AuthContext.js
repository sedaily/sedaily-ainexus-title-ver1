import React, { createContext, useContext, useState, useEffect } from "react";
import { authAPI } from "../services/api";

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

  const checkAuthStatus = () => {
    try {
      const isAuth = authAPI.isAuthenticated();
      const currentUser = authAPI.getCurrentUser();

      setIsAuthenticated(isAuth);
      setUser(currentUser);
    } catch (error) {
      console.error("Auth status check failed:", error);
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (credentials) => {
    try {
      const result = await authAPI.signin(credentials);
      const user = authAPI.getCurrentUser();

      setIsAuthenticated(true);
      setUser(user);

      return result;
    } catch (error) {
      throw error;
    }
  };

  const signup = async (userData) => {
    try {
      const result = await authAPI.signup(userData);
      return result;
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      await authAPI.signout();
    } finally {
      setIsAuthenticated(false);
      setUser(null);
    }
  };

  const verifyEmail = async (verificationData) => {
    try {
      const result = await authAPI.verifyEmail(verificationData);
      return result;
    } catch (error) {
      throw error;
    }
  };

  const forgotPassword = async (email) => {
    try {
      const result = await authAPI.forgotPassword(email);
      return result;
    } catch (error) {
      throw error;
    }
  };

  const confirmPassword = async (resetData) => {
    try {
      const result = await authAPI.confirmPassword(resetData);
      return result;
    } catch (error) {
      throw error;
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
    forgotPassword,
    confirmPassword,
    checkAuthStatus,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
