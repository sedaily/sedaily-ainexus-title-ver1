import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const TestMarkdown = () => {
  const testContent = `
# # 주요 해전 승리
# # # 임진왜란 시기 (1592-1598)

## 정상적인 H2 제목
### 정상적인 H3 제목

이것은 일반 텍스트입니다.

• 불릿 포인트 1
• 불릿 포인트 2

| 항목 | 설명 |
|------|------|
| 테스트 | 값 |
`;

  const processedContent = testContent
    .replace(/^#\s+#\s+#/gm, '### ')
    .replace(/^#\s+#/gm, '## ')
    .replace(/\n#\s+#\s+#/g, '\n### ')
    .replace(/\n#\s+#/g, '\n## ');

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">마크다운 테스트</h1>
      
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-2">원본 텍스트:</h2>
        <pre className="bg-gray-100 p-4 rounded overflow-x-auto">
          {testContent}
        </pre>
      </div>

      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-2">처리된 텍스트:</h2>
        <pre className="bg-gray-100 p-4 rounded overflow-x-auto">
          {processedContent}
        </pre>
      </div>

      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-2">렌더링 결과:</h2>
        <div className="prose prose-lg max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {processedContent}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
};

export default TestMarkdown;