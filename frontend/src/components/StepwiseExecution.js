import React, { useState } from 'react';
import ThoughtProcess from './ThoughtProcess';

/**
 * 단계별 실행 결과 표시 컴포넌트
 * 각 단계의 응답과 임계값 평가를 시각화
 */
const StepwiseExecution = ({ steps = [], isExecuting = false }) => {
  const [expandedSteps, setExpandedSteps] = useState({});

  const toggleStep = (stepIndex) => {
    setExpandedSteps(prev => ({
      ...prev,
      [stepIndex]: !prev[stepIndex]
    }));
  };

  return (
    <div className="stepwise-execution-container">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <span className="mr-2">📋</span>
        단계별 실행 결과
      </h3>

      {steps.length === 0 && !isExecuting ? (
        <p className="text-gray-500 italic">단계별 실행 결과가 표시됩니다...</p>
      ) : (
        <div className="space-y-3">
          {steps.map((step, index) => (
            <StepResult 
              key={index} 
              step={step} 
              index={index}
              isExpanded={expandedSteps[index]}
              onToggle={() => toggleStep(index)}
            />
          ))}
          
          {isExecuting && (
            <div className="flex items-center justify-center p-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-3 text-gray-600">실행 중...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * 개별 단계 결과
 */
const StepResult = ({ step, index, isExpanded, onToggle }) => {
  const getStatusIcon = () => {
    if (!step.completed) return '⏳';
    return step.confidence >= step.threshold ? '✅' : '❌';
  };

  const getStatusColor = () => {
    if (!step.completed) return 'border-gray-300';
    return step.confidence >= step.threshold ? 'border-green-500' : 'border-red-500';
  };

  return (
    <div className={`step-result bg-white rounded-lg border-2 ${getStatusColor()} overflow-hidden`}>
      <div 
        className="p-4 cursor-pointer hover:bg-gray-50"
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <span className="text-2xl mr-3">{getStatusIcon()}</span>
            <div>
              <h4 className="font-medium text-gray-900">
                {step.step || `단계 ${index + 1}`}
              </h4>
              <div className="flex items-center mt-1 text-sm text-gray-600">
                <span>신뢰도: {step.confidence ? `${Math.round(step.confidence * 100)}%` : '-'}</span>
                <span className="mx-2">|</span>
                <span>임계값: {Math.round(step.threshold * 100)}%</span>
              </div>
            </div>
          </div>
          <button className="text-gray-400 hover:text-gray-600">
            {isExpanded ? '▼' : '▶'}
          </button>
        </div>
      </div>

      {isExpanded && step.response && (
        <div className="border-t px-4 py-3 bg-gray-50">
          <div className="prose prose-sm max-w-none">
            <h5 className="font-medium text-gray-700 mb-2">응답:</h5>
            <div className="bg-white p-3 rounded border border-gray-200">
              <p className="whitespace-pre-wrap text-gray-800">{step.response}</p>
            </div>
          </div>
          
          {step.confidence !== undefined && (
            <div className="mt-3">
              <ConfidenceBar 
                confidence={step.confidence} 
                threshold={step.threshold}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * 신뢰도 바 컴포넌트
 */
const ConfidenceBar = ({ confidence, threshold }) => {
  const confidencePercent = Math.round(confidence * 100);
  const thresholdPercent = Math.round(threshold * 100);
  
  return (
    <div className="relative">
      <div className="flex justify-between text-xs text-gray-600 mb-1">
        <span>신뢰도: {confidencePercent}%</span>
        <span>임계값: {thresholdPercent}%</span>
      </div>
      <div className="relative w-full bg-gray-200 rounded-full h-3">
        <div 
          className={`absolute top-0 left-0 h-full rounded-full transition-all duration-300 ${
            confidence >= threshold ? 'bg-green-500' : 'bg-red-500'
          }`}
          style={{ width: `${confidencePercent}%` }}
        />
        <div 
          className="absolute top-0 h-full w-0.5 bg-gray-700"
          style={{ left: `${thresholdPercent}%` }}
        >
          <span className="absolute -top-5 -left-3 text-xs text-gray-700">
            ▼
          </span>
        </div>
      </div>
    </div>
  );
};

export default StepwiseExecution;