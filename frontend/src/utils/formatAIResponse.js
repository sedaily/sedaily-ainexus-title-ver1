/**
 * AI 응답 텍스트를 일관된 형식으로 정리하는 유틸리티 함수
 */

export const formatAIResponse = (text) => {
  if (!text || typeof text !== 'string') return text;

  let formatted = text;

  // 1. 연속된 공백과 탭을 정리
  formatted = formatted.replace(/[ \t]+/g, ' ');

  // 2. 기본적으로 모든 문장 끝에 빈 줄 추가
  formatted = formatted.replace(/([.!?])\s*\n(?!\n)/g, '$1\n\n');
  
  // 3. 콜론(:) 다음에도 줄바꿈
  formatted = formatted.replace(/(:)\s*\n(?!\n)/g, '$1\n\n');

  // 4. 목록 항목 앞에 적절한 간격 추가
  formatted = formatted.replace(/\n([0-9]+\.)\s/g, '\n\n$1 '); // 번호 목록
  formatted = formatted.replace(/\n([•\-\*])\s/g, '\n\n$1 '); // 불릿 목록
  
  // 5. 이모지나 특수문자로 시작하는 라인 앞에도 빈 줄 추가
  formatted = formatted.replace(/\n([📊🎯💡🔍⚠️🚀✅❌🌐🔧⚡])/g, '\n\n$1');
  
  // 6. 연속된 줄바꿈 정리 (3개 이상 → 2개로)
  formatted = formatted.replace(/\n{3,}/g, '\n\n');


  // 7. 시작과 끝의 불필요한 공백 제거
  formatted = formatted.trim();

  // 8. 연속된 공백 줄을 최대 1개로 제한
  formatted = formatted.replace(/\n\n+/g, '\n\n');

  return formatted;
};