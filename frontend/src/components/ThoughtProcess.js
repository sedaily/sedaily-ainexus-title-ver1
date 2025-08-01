import React from 'react';

/**
 * AI 사고과정 표시 컴포넌트
 * WebSocket을 통해 실시간으로 전달되는 AI의 사고과정을 시각화
 */
const ThoughtProcess = ({ thoughts = [] }) => {
  return (
    <div className="thought-process-container bg-gray-50 rounded-lg p-4 mb-4">
      <h3 className="text-lg font-semibold mb-3 flex items-center">
        <span className="mr-2">🧠</span>
        AI 사고과정
      </h3>
      
      {thoughts.length === 0 ? (
        <p className="text-gray-500 italic">사고과정이 표시됩니다...</p>
      ) : (
        <div className="space-y-3">
          {thoughts.map((thought, index) => (
            <ThoughtItem key={index} thought={thought} index={index} />
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * 개별 사고과정 아이템
 */
const ThoughtItem = ({ thought, index }) => {
  const getDecisionColor = (decision) => {
    switch (decision) {
      case 'PROCEED':
      case 'CONTINUE':
        return 'text-green-600';
      case 'STOP':
        return 'text-red-600';
      case 'RETRY':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  const getConfidenceBar = (confidence) => {
    const percentage = Math.round(confidence * 100);
    const barColor = confidence >= 0.7 ? 'bg-green-500' : confidence >= 0.4 ? 'bg-yellow-500' : 'bg-red-500';
    
    return (
      <div className="w-full bg-gray-200 rounded-full h-2.5 mt-1">
        <div 
          className={`${barColor} h-2.5 rounded-full transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    );
  };

  return (
    <div className="thought-item bg-white rounded border border-gray-200 p-3">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-600 text-sm font-medium mr-2">
            {index + 1}
          </span>
          <h4 className="font-medium text-gray-900">{thought.step || `단계 ${index + 1}`}</h4>
        </div>
        <span className={`text-sm font-medium ${getDecisionColor(thought.decision)}`}>
          {thought.decision}
        </span>
      </div>
      
      <div className="space-y-2 text-sm">
        <div>
          <span className="font-medium text-gray-700">생각:</span>
          <p className="text-gray-600 mt-1">{thought.thought}</p>
        </div>
        
        {thought.reasoning && (
          <div>
            <span className="font-medium text-gray-700">근거:</span>
            <p className="text-gray-600 mt-1">{thought.reasoning}</p>
          </div>
        )}
        
        <div>
          <span className="font-medium text-gray-700">신뢰도: {Math.round(thought.confidence * 100)}%</span>
          {getConfidenceBar(thought.confidence)}
        </div>
      </div>
    </div>
  );
};

export default ThoughtProcess;