import React from 'react';
import { SunIcon, MoonIcon } from '@heroicons/react/24/outline';
import { useTheme } from '../contexts/ThemeContext';

const DarkModeToggle = ({ className = '', size = 'md' }) => {
  const { isDarkMode, toggleDarkMode } = useTheme();

  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10', 
    lg: 'w-12 h-12'
  };

  const iconSizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-6 w-6'
  };

  return (
    <button
      onClick={toggleDarkMode}
      className={`relative inline-flex items-center justify-center rounded-lg transition-all duration-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 ${sizeClasses[size]} ${
        isDarkMode 
          ? 'bg-gray-800 text-yellow-400 hover:bg-gray-700' 
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
      } ${className}`}
      title={isDarkMode ? '라이트 모드로 전환' : '다크 모드로 전환'}
    >
      <div className={`transition-all duration-300 ${isDarkMode ? 'rotate-0 scale-100' : 'rotate-180 scale-0'} absolute`}>
        <MoonIcon className={iconSizeClasses[size]} />
      </div>
      <div className={`transition-all duration-300 ${isDarkMode ? 'rotate-180 scale-0' : 'rotate-0 scale-100'} absolute`}>
        <SunIcon className={iconSizeClasses[size]} />
      </div>
    </button>
  );
};

export default DarkModeToggle;