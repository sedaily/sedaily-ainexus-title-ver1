import React, { useState, useCallback, useEffect } from 'react';

const ResizeHandle = ({ 
  onResize, 
  minWidth = 300, 
  maxWidth = 500, 
  initialWidth = 380,
  className = "" 
}) => {
  const [isResizing, setIsResizing] = useState(false);
  const [startX, setStartX] = useState(0);
  const [startWidth, setStartWidth] = useState(initialWidth);

  const handleMouseDown = useCallback((e) => {
    setIsResizing(true);
    setStartX(e.clientX);
    setStartWidth(initialWidth);
    e.preventDefault();
  }, [initialWidth]);

  const handleTouchStart = useCallback((e) => {
    setIsResizing(true);
    setStartX(e.touches[0].clientX);
    setStartWidth(initialWidth);
    e.preventDefault();
  }, [initialWidth]);

  const handleMouseMove = useCallback((e) => {
    if (!isResizing) return;
    
    const deltaX = startX - e.clientX; // 왼쪽으로 드래그하면 패널이 좁아짐
    const newWidth = Math.min(maxWidth, Math.max(minWidth, startWidth + deltaX));
    
    onResize(newWidth);
  }, [isResizing, startX, startWidth, minWidth, maxWidth, onResize]);

  const handleTouchMove = useCallback((e) => {
    if (!isResizing) return;
    
    const deltaX = startX - e.touches[0].clientX;
    const newWidth = Math.min(maxWidth, Math.max(minWidth, startWidth + deltaX));
    
    onResize(newWidth);
  }, [isResizing, startX, startWidth, minWidth, maxWidth, onResize]);

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
  }, []);

  const handleTouchEnd = useCallback(() => {
    setIsResizing(false);
  }, []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.addEventListener('touchmove', handleTouchMove);
      document.addEventListener('touchend', handleTouchEnd);
      
      // 리사이징 중 텍스트 선택 방지
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'col-resize';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
      
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isResizing, handleMouseMove, handleMouseUp, handleTouchMove, handleTouchEnd]);

  return (
    <div
      className={`
        w-1 bg-gray-200 hover:bg-blue-400 cursor-col-resize transition-colors duration-200
        ${isResizing ? 'bg-blue-500' : ''}
        ${className}
      `}
      onMouseDown={handleMouseDown}
      onTouchStart={handleTouchStart}
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize panel"
      tabIndex={0}
      onKeyDown={(e) => {
        // 키보드로도 리사이즈 가능
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
          const delta = e.key === 'ArrowLeft' ? 10 : -10;
          const newWidth = Math.min(maxWidth, Math.max(minWidth, initialWidth + delta));
          onResize(newWidth);
        }
      }}
    >
      {/* 시각적 리사이즈 인디케이터 */}
      <div className="h-full w-full relative">
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
          <div className="flex flex-col space-y-1">
            <div className="w-0.5 h-4 bg-gray-400"></div>
            <div className="w-0.5 h-4 bg-gray-400"></div>
            <div className="w-0.5 h-4 bg-gray-400"></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResizeHandle;