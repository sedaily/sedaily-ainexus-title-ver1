import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import {
  XMarkIcon,
  Bars3Icon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline';
import ChatPanel from './ChatPanel';
import ResizeHandle from '../common/ResizeHandle';
import { promptCardAPI } from '../../services/api';

const CardPanel = ({ 
  projectId, 
  promptCards = [], 
  onCardsChanged,
  className = "" 
}) => {
  const [loading, setLoading] = useState(false);

  const handleCardToggle = async (cardId, enabled) => {
    try {
      setLoading(true);
      await promptCardAPI.updatePromptCard(cardId, { enabled });
      onCardsChanged?.();
      toast.success(enabled ? '카드가 활성화되었습니다' : '카드가 비활성화되었습니다');
    } catch (error) {
      console.error('카드 상태 변경 실패:', error);
      toast.error('카드 상태 변경에 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  const categorizedCards = promptCards.reduce((acc, card) => {
    const category = card.category || 'other';
    if (!acc[category]) acc[category] = [];
    acc[category].push(card);
    return acc;
  }, {});

  const categoryNames = {
    role: '역할 (Role)',
    guideline: '가이드라인 (Guideline)', 
    workflow: '워크플로우 (Workflow)',
    output_format: '출력 형식 (Output Format)',
    few_shot: '예시 (Few-shot)',
    scoring: '평가 (Scoring)',
    other: '기타'
  };

  return (
    <div className={`bg-white border-r border-gray-200 h-full overflow-y-auto ${className}`}>
      {/* 카드 패널 헤더 */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AdjustmentsHorizontalIcon className="h-5 w-5 text-gray-600" />
            <h3 className="font-semibold text-gray-900">프롬프트 카드</h3>
          </div>
          <div className="text-sm text-gray-500">
            {promptCards.filter(c => c.enabled).length}/{promptCards.length} 활성
          </div>
        </div>
      </div>

      {/* 카드 목록 */}
      <div className="p-4 space-y-6">
        {Object.entries(categorizedCards).map(([category, cards]) => (
          <div key={category} className="space-y-3">
            <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              {categoryNames[category] || category}
            </h4>
            <div className="space-y-2">
              {cards.map((card) => (
                <div
                  key={card.id}
                  className={`p-3 rounded-lg border transition-all duration-200 ${
                    card.enabled
                      ? 'border-blue-200 bg-blue-50 shadow-sm'
                      : 'border-gray-200 bg-gray-50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <h5 className="text-sm font-medium text-gray-900 truncate">
                          {card.title}
                        </h5>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          card.enabled
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {card.enabled ? '활성' : '비활성'}
                        </span>
                      </div>
                      {card.description && (
                        <p className="mt-1 text-xs text-gray-600 line-clamp-2">
                          {card.description}
                        </p>
                      )}
                      <div className="mt-2 flex items-center space-x-2 text-xs text-gray-500">
                        <span>{card.model_name || 'Claude'}</span>
                        <span>•</span>
                        <span>카테고리: {categoryNames[card.category] || card.category}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleCardToggle(card.id, !card.enabled)}
                      disabled={loading}
                      className={`ml-3 w-9 h-5 rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                        card.enabled
                          ? 'bg-blue-600'
                          : 'bg-gray-300'
                      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <div className={`w-4 h-4 bg-white rounded-full shadow transform transition-transform duration-200 ${
                        card.enabled ? 'translate-x-4' : 'translate-x-0'
                      }`} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
        
        {promptCards.length === 0 && (
          <div className="text-center py-8">
            <AdjustmentsHorizontalIcon className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">프롬프트 카드가 없습니다</p>
          </div>
        )}
      </div>
    </div>
  );
};

const MobileDrawer = ({ 
  isOpen, 
  onClose, 
  projectId, 
  promptCards, 
  onCardsChanged 
}) => {
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      {/* 오버레이 */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
        onClick={onClose}
      />
      
      {/* 드로어 */}
      <div className="fixed inset-y-0 right-0 w-80 bg-white shadow-xl z-50 md:hidden transform transition-transform duration-300">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">프롬프트 카드</h3>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>
        <CardPanel
          projectId={projectId}
          promptCards={promptCards}
          onCardsChanged={onCardsChanged}
          className="border-r-0"
        />
      </div>
    </>
  );
};

const WorkspaceLayout = ({ 
  projectId, 
  projectName,
  onCardsChanged 
}) => {
  const [promptCards, setPromptCards] = useState([]);
  const [cardPanelVisible, setCardPanelVisible] = useState(true);
  const [cardPanelWidth, setCardPanelWidth] = useState(380);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [isDesktop, setIsDesktop] = useState(window.innerWidth >= 960);

  // 화면 크기 변화 감지
  useEffect(() => {
    const handleResize = () => {
      setIsDesktop(window.innerWidth >= 960);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 프롬프트 카드 로드
  const loadPromptCards = useCallback(async () => {
    try {
      const response = await promptCardAPI.getPromptCards(projectId, true, true);
      setPromptCards(response.promptCards || []);
      onCardsChanged?.(response.promptCards || []);
    } catch (error) {
      console.error('프롬프트 카드 로드 실패:', error);
      setPromptCards([]);
    }
  }, [projectId, onCardsChanged]);

  useEffect(() => {
    loadPromptCards();
  }, [loadPromptCards]);

  // 카드 패널 토글
  const handleToggleCardPanel = useCallback(() => {
    if (isDesktop) {
      setCardPanelVisible(prev => !prev);
    } else {
      setMobileDrawerOpen(prev => !prev);
    }
  }, [isDesktop]);

  // 리사이즈 핸들러
  const handleResize = useCallback((newWidth) => {
    setCardPanelWidth(newWidth);
  }, []);

  // 카드 변경 핸들러
  const handleCardsChanged = useCallback(() => {
    loadPromptCards();
  }, [loadPromptCards]);

  // 데스크톱 레이아웃
  if (isDesktop) {
    return (
      <div className="h-full flex">
        {/* 카드 패널 */}
        {cardPanelVisible && (
          <>
            <div style={{ width: cardPanelWidth }}>
              <CardPanel
                projectId={projectId}
                promptCards={promptCards}
                onCardsChanged={handleCardsChanged}
              />
            </div>
            <ResizeHandle
              onResize={handleResize}
              initialWidth={cardPanelWidth}
              minWidth={300}
              maxWidth={500}
            />
          </>
        )}
        
        {/* 채팅 패널 */}
        <div className="flex-1 min-w-0">
          <ChatPanel
            projectId={projectId}
            projectName={projectName}
            promptCards={promptCards}
            onToggleCardPanel={handleToggleCardPanel}
            cardPanelVisible={cardPanelVisible}
          />
        </div>
      </div>
    );
  }

  // 모바일 레이아웃
  return (
    <div className="h-full relative">
      {/* 메인 채팅 인터페이스 */}
      <ChatPanel
        projectId={projectId}
        projectName={projectName}
        promptCards={promptCards}
        onToggleCardPanel={handleToggleCardPanel}
        cardPanelVisible={false}
      />
      
      {/* 모바일 드로어 */}
      <MobileDrawer
        isOpen={mobileDrawerOpen}
        onClose={() => setMobileDrawerOpen(false)}
        projectId={projectId}
        promptCards={promptCards}
        onCardsChanged={handleCardsChanged}
      />
      
      {/* 플로팅 버튼 (모바일) */}
      {!mobileDrawerOpen && (
        <button
          onClick={() => setMobileDrawerOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-colors z-30 flex items-center justify-center"
        >
          <Bars3Icon className="h-6 w-6" />
        </button>
      )}
    </div>
  );
};

export default WorkspaceLayout;