import React from 'react';

// 기본 스켈레톤 컴포넌트
export const Skeleton = ({ 
  width = "100%", 
  height = "1rem", 
  className = "", 
  rounded = true 
}) => (
  <div 
    className={`bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 animate-pulse ${
      rounded ? "rounded" : ""
    } ${className}`}
    style={{ width, height }}
  />
);

// 프로젝트 카드 스켈레톤
export const ProjectCardSkeleton = () => (
  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 animate-pulse">
    <div className="flex items-start justify-between mb-4">
      <Skeleton width="60%" height="1.25rem" />
      <Skeleton width="2rem" height="2rem" className="rounded-full" />
    </div>
    <Skeleton width="40%" height="0.875rem" className="mb-3" />
    <Skeleton width="100%" height="3rem" className="mb-4" />
    <div className="flex items-center justify-between">
      <div className="flex space-x-2">
        <Skeleton width="4rem" height="1.5rem" className="rounded-full" />
        <Skeleton width="3rem" height="1.5rem" className="rounded-full" />
      </div>
      <Skeleton width="5rem" height="0.75rem" />
    </div>
  </div>
);

// 프롬프트 카드 스켈레톤
export const PromptCardSkeleton = () => (
  <div className="p-4 rounded-xl border border-gray-200 bg-white animate-pulse">
    <div className="flex items-start justify-between">
      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2 mb-2">
          <Skeleton width="4rem" height="1.25rem" className="rounded-md" />
          <Skeleton width="6rem" height="0.875rem" />
        </div>
        <div className="space-y-1">
          <Skeleton width="5rem" height="0.75rem" />
          <Skeleton width="7rem" height="0.75rem" />
        </div>
      </div>
      <div className="flex items-center space-x-2 ml-4">
        <Skeleton width="1rem" height="1rem" className="rounded" />
        <Skeleton width="1rem" height="1rem" className="rounded" />
        <Skeleton width="2.5rem" height="1.25rem" className="rounded-full" />
      </div>
    </div>
  </div>
);

// 채팅 메시지 스켈레톤
export const ChatMessageSkeleton = ({ isUser = false }) => (
  <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
    <div className={`flex max-w-[80%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div className={`flex-shrink-0 ${isUser ? "ml-3" : "mr-3"}`}>
        <Skeleton 
          width="2rem" 
          height="2rem" 
          className="rounded-full" 
        />
      </div>
      <div className={`rounded-lg px-4 py-3 ${
        isUser ? "bg-blue-100" : "bg-gray-100"
      }`}>
        <div className="space-y-2">
          <Skeleton width="12rem" height="0.875rem" />
          <Skeleton width="8rem" height="0.875rem" />
          {!isUser && <Skeleton width="10rem" height="0.875rem" />}
        </div>
      </div>
    </div>
  </div>
);

// 사이드바 스켈레톤
export const SidebarSkeleton = () => (
  <div className="w-96 bg-white border border-gray-200 rounded-lg shadow-sm p-4 animate-pulse">
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center space-x-2">
        <Skeleton width="1.25rem" height="1.25rem" />
        <Skeleton width="6rem" height="0.875rem" />
      </div>
      <Skeleton width="3rem" height="0.75rem" />
    </div>
    
    <div className="space-y-6">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div key={i}>
          <div className="flex items-center justify-between mb-2">
            <Skeleton width="4rem" height="0.75rem" />
            <Skeleton width="8rem" height="0.75rem" />
          </div>
          <PromptCardSkeleton />
        </div>
      ))}
    </div>
  </div>
);

// 전체 프로젝트 목록 스켈레톤
export const ProjectListSkeleton = () => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
    {[1, 2, 3, 4, 5, 6].map((i) => (
      <ProjectCardSkeleton key={i} />
    ))}
  </div>
);

// 최적화된 스켈레톤 (Intersection Observer 사용)
export const LazySkeletonLoader = ({ 
  children, 
  fallback, 
  threshold = 0.1 
}) => {
  const [isVisible, setIsVisible] = React.useState(false);
  const ref = React.useRef();

  React.useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, [threshold]);

  return (
    <div ref={ref}>
      {isVisible ? children : fallback}
    </div>
  );
};

export default {
  Skeleton,
  ProjectCardSkeleton,
  PromptCardSkeleton,
  ChatMessageSkeleton,
  SidebarSkeleton,
  ProjectListSkeleton,
  LazySkeletonLoader
};