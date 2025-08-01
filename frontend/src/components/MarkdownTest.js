import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const MarkdownTest = () => {
  const testCases = [
    { input: "### 제목", expected: "H3 헤딩" },
    { input: "## 제목", expected: "H2 헤딩" },
    { input: "# 제목", expected: "H1 헤딩" },
    { input: "일반 텍스트", expected: "일반 문단" },
  ];

  return (
    <div className="p-8 space-y-4">
      <h1 className="text-2xl font-bold mb-4">마크다운 렌더링 테스트</h1>
      
      {testCases.map((test, idx) => (
        <div key={idx} className="border p-4 rounded">
          <div className="mb-2">
            <strong>입력:</strong> <code>{test.input}</code>
          </div>
          <div className="mb-2">
            <strong>예상:</strong> {test.expected}
          </div>
          <div className="border-t pt-2">
            <strong>결과:</strong>
            <div className="prose">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {test.input}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default MarkdownTest;